# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
from __future__ import annotations

import logging
from typing import Any

from superset.anomalies.detector import anomaly_detector
from superset.anomalies.models import AnomalyRule, AnomalyRuleStatus
from superset.daos.anomaly import AnomalyRuleDAO, AnomalyDetectionLogDAO
from superset.models.slice import Slice

logger = logging.getLogger(__name__)


class AnomalyInjectionEngine:
    """
    Engine for injecting anomaly detection results into chart data responses.
    """

    def __init__(self) -> None:
        self.detector = anomaly_detector

    def inject_anomaly_results(
        self,
        chart: Slice | None,
        queries_result: list[dict[str, Any]],
        chart_id: int | None = None,
    ) -> dict[str, Any]:
        """
        Inject anomaly detection results into the query response.

        Args:
            chart: The chart object (if available)
            queries_result: The query results from ChartDataCommand
            chart_id: Optional chart ID (used when chart object is not available)

        Returns:
            A dictionary containing anomaly results, or empty dict if no anomalies
        """
        if not chart and not chart_id:
            return {"has_anomaly_rules": False, "anomaly_results": []}

        actual_chart_id = chart.id if chart else chart_id
        if not actual_chart_id:
            return {"has_anomaly_rules": False, "anomaly_results": []}

        rules = AnomalyRuleDAO.find_by_chart_id(actual_chart_id)
        if not rules:
            return {"has_anomaly_rules": False, "anomaly_results": []}

        active_rules = [r for r in rules if r.status == AnomalyRuleStatus.ACTIVE]
        if not active_rules:
            return {"has_anomaly_rules": True, "anomaly_results": []}

        all_anomaly_results: list[dict[str, Any]] = []
        has_anomalies = False

        for rule in active_rules:
            for query in queries_result:
                data = query.get("data", [])
                if not data:
                    continue

                metric_column = self._find_metric_column(data, rule.metric)
                timestamp_column = self._find_timestamp_column(data)

                detection_result = self.detector.detect(
                    rule=rule,
                    data=data,
                    metric_column=metric_column,
                    timestamp_column=timestamp_column,
                )

                if detection_result.get("is_anomaly", False):
                    has_anomalies = True
                    self._update_rule_last_anomaly(rule, detection_result)

                result_dict = {
                    "rule_id": detection_result["rule_id"],
                    "rule_name": rule.name,
                    "metric": detection_result["metric"],
                    "rule_type": rule.rule_type,
                    "is_anomaly": detection_result["is_anomaly"],
                    "results": detection_result["results"],
                    "summary": detection_result["summary"],
                }
                all_anomaly_results.append(result_dict)

        return {
            "has_anomaly_rules": True,
            "has_anomalies": has_anomalies,
            "anomaly_results": all_anomaly_results,
        }

    def _find_metric_column(self, data: list[dict[str, Any]], metric: str) -> str | None:
        """
        Find the appropriate column name for the metric.
        Handles both exact matches and common transformations.
        """
        if not data:
            return metric

        sample_row = data[0]
        columns = sample_row.keys()

        if metric in columns:
            return metric

        for col in columns:
            if col.lower() == metric.lower():
                return col

        for col in columns:
            if metric in col or col in metric:
                return col

        return metric

    def _find_timestamp_column(self, data: list[dict[str, Any]]) -> str | None:
        """
        Find the timestamp column in the data.
        Looks for common timestamp column names.
        """
        if not data:
            return None

        sample_row = data[0]
        timestamp_columns = ["__timestamp", "time", "timestamp", "date", "datetime", "ds"]

        for col in timestamp_columns:
            if col in sample_row:
                return col

        return None

    def _update_rule_last_anomaly(
        self, rule: AnomalyRule, detection_result: dict[str, Any]
    ) -> None:
        """
        Update the rule's last anomaly information and create detection log.
        """
        from superset.extensions import db

        summary = detection_result.get("summary") or {}
        results = detection_result.get("results") or []

        anomaly_results = [r for r in results if r.get("is_anomaly", False)]
        if not anomaly_results:
            return

        last_anomaly = anomaly_results[-1]
        current_value = last_anomaly.get("current_value")
        message = last_anomaly.get("message", "")

        rule.update_last_anomaly(value=current_value or 0, message=message or "")

        for anomaly in anomaly_results:
            AnomalyDetectionLogDAO.create_log(
                rule=rule,
                is_anomaly=True,
                anomaly_type=anomaly.get("anomaly_type"),
                direction=anomaly.get("direction"),
                current_value=anomaly.get("current_value"),
                reference_value=anomaly.get("reference_value") or anomaly.get("previous_value"),
                change_percent=anomaly.get("change_percent"),
                change_absolute=anomaly.get("change_absolute"),
                threshold=anomaly.get("threshold"),
                threshold_min=anomaly.get("threshold_min"),
                threshold_max=anomaly.get("threshold_max"),
                row_index=anomaly.get("row_index"),
                message=anomaly.get("message"),
            )

        db.session.commit()


anomaly_injection_engine = AnomalyInjectionEngine()
