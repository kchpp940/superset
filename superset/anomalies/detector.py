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
from typing import Any, Optional

from superset.anomalies.models import (
    AnomalyDirection,
    AnomalyRule,
    AnomalyRuleType,
)
from superset.anomalies.types import (
    AnomalyDetectionResult,
    AnomalyResult,
    AnomalySummary,
)

logger = logging.getLogger(__name__)


class AnomalyDetector:
    """
    Core anomaly detection engine that implements various anomaly detection algorithms.
    """

    def __init__(self) -> None:
        self._detectors = {
            AnomalyRuleType.THRESHOLD: self._detect_threshold,
            AnomalyRuleType.MOM: self._detect_mom,
            AnomalyRuleType.YOY: self._detect_yoy,
            AnomalyRuleType.PERIOD_OVER_PERIOD: self._detect_period_over_period,
            AnomalyRuleType.CONSECUTIVE: self._detect_consecutive,
        }

    def detect(
        self,
        rule: AnomalyRule,
        data: list[dict[str, Any]],
        metric_column: str | None = None,
        timestamp_column: str | None = None,
    ) -> AnomalyDetectionResult:
        """
        Detect anomalies in the data using the specified rule.

        Args:
            rule: The anomaly detection rule to apply
            data: List of data rows to analyze
            metric_column: Column name containing the metric values
            timestamp_column: Column name containing timestamps (for time-based detection)

        Returns:
            AnomalyDetectionResult containing all detected anomalies
        """
        metric = metric_column or rule.metric
        results: list[AnomalyResult] = []
        rule_type = rule.rule_type

        detector = self._detectors.get(rule_type)
        if detector:
            results = detector(
                rule=rule,
                data=data,
                metric=metric,
                timestamp_column=timestamp_column,
            )

        summary = self._compute_summary(results, data)

        return AnomalyDetectionResult(
            rule_id=rule.id,
            chart_id=rule.chart_id,
            metric=metric,
            is_anomaly=any(r.get("is_anomaly", False) for r in results),
            results=results,
            summary=summary,
        )

    def _detect_threshold(
        self,
        rule: AnomalyRule,
        data: list[dict[str, Any]],
        metric: str,
        timestamp_column: str | None = None,
    ) -> list[AnomalyResult]:
        """
        Detect anomalies based on threshold values.
        """
        results: list[AnomalyResult] = []
        threshold_min = rule.threshold_min
        threshold_max = rule.threshold_max
        direction = rule.direction

        for idx, row in enumerate(data):
            value = self._get_numeric_value(row, metric)
            if value is None:
                continue

            is_anomaly = False
            anomaly_direction: str | None = None
            message: str | None = None

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.INCREASE):
                if threshold_max is not None and value > threshold_max:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.INCREASE
                    message = f"Value {value} exceeds maximum threshold {threshold_max}"

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.DECREASE):
                if threshold_min is not None and value < threshold_min:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.DECREASE
                    message = f"Value {value} is below minimum threshold {threshold_min}"

            timestamp = self._get_timestamp(row, timestamp_column, idx)

            results.append(
                AnomalyResult(
                    rule_id=rule.id,
                    chart_id=rule.chart_id,
                    metric=metric,
                    anomaly_type=AnomalyRuleType.THRESHOLD,
                    direction=anomaly_direction or direction,
                    current_value=value,
                    threshold_min=threshold_min,
                    threshold_max=threshold_max,
                    is_anomaly=is_anomaly,
                    message=message,
                    row_index=idx,
                    timestamp=timestamp,
                )
            )

        return results

    def _detect_mom(
        self,
        rule: AnomalyRule,
        data: list[dict[str, Any]],
        metric: str,
        timestamp_column: str | None = None,
    ) -> list[AnomalyResult]:
        """
        Detect Month-over-Month anomalies.
        Compare each value with the value from the previous period.
        """
        results: list[AnomalyResult] = []
        threshold = rule.mom_threshold or 0.1
        direction = rule.direction

        if len(data) < 2:
            return results

        for idx in range(1, len(data)):
            current_value = self._get_numeric_value(data[idx], metric)
            previous_value = self._get_numeric_value(data[idx - 1], metric)

            if current_value is None or previous_value is None:
                continue

            if previous_value == 0:
                if current_value != 0:
                    change_percent = float("inf") if current_value > 0 else float("-inf")
                else:
                    change_percent = 0.0
            else:
                change_percent = (current_value - previous_value) / abs(previous_value)

            change_absolute = current_value - previous_value
            is_anomaly = False
            anomaly_direction: str | None = None
            message: str | None = None

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.INCREASE):
                if change_percent >= threshold:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.INCREASE
                    message = (
                        f"Value increased by {change_percent:.1%} "
                        f"(from {previous_value} to {current_value}), "
                        f"exceeding threshold {threshold:.1%}"
                    )

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.DECREASE):
                if change_percent <= -threshold:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.DECREASE
                    message = (
                        f"Value decreased by {abs(change_percent):.1%} "
                        f"(from {previous_value} to {current_value}), "
                        f"exceeding threshold {threshold:.1%}"
                    )

            timestamp = self._get_timestamp(data[idx], timestamp_column, idx)

            results.append(
                AnomalyResult(
                    rule_id=rule.id,
                    chart_id=rule.chart_id,
                    metric=metric,
                    anomaly_type=AnomalyRuleType.MOM,
                    direction=anomaly_direction or direction,
                    current_value=current_value,
                    previous_value=previous_value,
                    change_percent=change_percent,
                    change_absolute=change_absolute,
                    threshold=threshold,
                    is_anomaly=is_anomaly,
                    message=message,
                    row_index=idx,
                    timestamp=timestamp,
                )
            )

        return results

    def _detect_yoy(
        self,
        rule: AnomalyRule,
        data: list[dict[str, Any]],
        metric: str,
        timestamp_column: str | None = None,
    ) -> list[AnomalyResult]:
        """
        Detect Year-over-Year anomalies.
        Similar to MOM but typically used for yearly comparisons.
        Uses period_offset_count if specified (default 12 for monthly data).
        """
        results: list[AnomalyResult] = []
        threshold = rule.yoy_threshold or 0.1
        period_offset = rule.period_offset_count or 12
        direction = rule.direction

        if len(data) <= period_offset:
            return results

        for idx in range(period_offset, len(data)):
            current_value = self._get_numeric_value(data[idx], metric)
            reference_value = self._get_numeric_value(data[idx - period_offset], metric)

            if current_value is None or reference_value is None:
                continue

            if reference_value == 0:
                if current_value != 0:
                    change_percent = float("inf") if current_value > 0 else float("-inf")
                else:
                    change_percent = 0.0
            else:
                change_percent = (current_value - reference_value) / abs(reference_value)

            change_absolute = current_value - reference_value
            is_anomaly = False
            anomaly_direction: str | None = None
            message: str | None = None

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.INCREASE):
                if change_percent >= threshold:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.INCREASE
                    message = (
                        f"YoY increase of {change_percent:.1%} "
                        f"(from {reference_value} to {current_value}), "
                        f"exceeding threshold {threshold:.1%}"
                    )

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.DECREASE):
                if change_percent <= -threshold:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.DECREASE
                    message = (
                        f"YoY decrease of {abs(change_percent):.1%} "
                        f"(from {reference_value} to {current_value}), "
                        f"exceeding threshold {threshold:.1%}"
                    )

            timestamp = self._get_timestamp(data[idx], timestamp_column, idx)

            results.append(
                AnomalyResult(
                    rule_id=rule.id,
                    chart_id=rule.chart_id,
                    metric=metric,
                    anomaly_type=AnomalyRuleType.YOY,
                    direction=anomaly_direction or direction,
                    current_value=current_value,
                    reference_value=reference_value,
                    change_percent=change_percent,
                    change_absolute=change_absolute,
                    threshold=threshold,
                    is_anomaly=is_anomaly,
                    message=message,
                    row_index=idx,
                    timestamp=timestamp,
                )
            )

        return results

    def _detect_period_over_period(
        self,
        rule: AnomalyRule,
        data: list[dict[str, Any]],
        metric: str,
        timestamp_column: str | None = None,
    ) -> list[AnomalyResult]:
        """
        Detect anomalies based on custom period-over-period comparison.
        """
        results: list[AnomalyResult] = []
        period_offset_count = rule.period_offset_count or 1
        direction = rule.direction

        if len(data) <= period_offset_count:
            return results

        threshold = rule.mom_threshold or rule.yoy_threshold or 0.1

        for idx in range(period_offset_count, len(data)):
            current_value = self._get_numeric_value(data[idx], metric)
            reference_value = self._get_numeric_value(data[idx - period_offset_count], metric)

            if current_value is None or reference_value is None:
                continue

            if reference_value == 0:
                if current_value != 0:
                    change_percent = float("inf") if current_value > 0 else float("-inf")
                else:
                    change_percent = 0.0
            else:
                change_percent = (current_value - reference_value) / abs(reference_value)

            change_absolute = current_value - reference_value
            is_anomaly = False
            anomaly_direction: str | None = None
            message: str | None = None

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.INCREASE):
                if change_percent >= threshold:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.INCREASE
                    message = (
                        f"PoP increase of {change_percent:.1%} "
                        f"(period offset: {period_offset_count}), "
                        f"exceeding threshold {threshold:.1%}"
                    )

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.DECREASE):
                if change_percent <= -threshold:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.DECREASE
                    message = (
                        f"PoP decrease of {abs(change_percent):.1%} "
                        f"(period offset: {period_offset_count}), "
                        f"exceeding threshold {threshold:.1%}"
                    )

            timestamp = self._get_timestamp(data[idx], timestamp_column, idx)

            results.append(
                AnomalyResult(
                    rule_id=rule.id,
                    chart_id=rule.chart_id,
                    metric=metric,
                    anomaly_type=AnomalyRuleType.PERIOD_OVER_PERIOD,
                    direction=anomaly_direction or direction,
                    current_value=current_value,
                    reference_value=reference_value,
                    change_percent=change_percent,
                    change_absolute=change_absolute,
                    threshold=threshold,
                    is_anomaly=is_anomaly,
                    message=message,
                    row_index=idx,
                    timestamp=timestamp,
                )
            )

        return results

    def _detect_consecutive(
        self,
        rule: AnomalyRule,
        data: list[dict[str, Any]],
        metric: str,
        timestamp_column: str | None = None,
    ) -> list[AnomalyResult]:
        """
        Detect consecutive anomalies.
        Triggers when N consecutive data points show abnormal behavior.
        """
        results: list[AnomalyResult] = []
        consecutive_count = rule.consecutive_count or 3
        direction = rule.consecutive_direction or AnomalyDirection.BOTH

        if len(data) < consecutive_count:
            return results

        numeric_values: list[float] = []
        for row in data:
            val = self._get_numeric_value(row, metric)
            numeric_values.append(val if val is not None else float("nan"))

        for idx in range(consecutive_count - 1, len(data)):
            current_values = numeric_values[idx - consecutive_count + 1 : idx + 1]

            valid_values = [v for v in current_values if not (v != v)]
            if len(valid_values) < consecutive_count:
                continue

            all_increasing = all(
                valid_values[i] <= valid_values[i + 1] for i in range(len(valid_values) - 1)
            )
            all_decreasing = all(
                valid_values[i] >= valid_values[i + 1] for i in range(len(valid_values) - 1)
            )

            is_anomaly = False
            anomaly_direction: str | None = None
            message: str | None = None

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.INCREASE):
                if all_increasing:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.INCREASE
                    message = (
                        f"Consecutive increase detected: {consecutive_count} "
                        f"consecutive increasing values ending at {valid_values[-1]}"
                    )

            if direction in (AnomalyDirection.BOTH, AnomalyDirection.DECREASE):
                if all_decreasing and not all_increasing:
                    is_anomaly = True
                    anomaly_direction = AnomalyDirection.DECREASE
                    message = (
                        f"Consecutive decrease detected: {consecutive_count} "
                        f"consecutive decreasing values ending at {valid_values[-1]}"
                    )

            timestamp = self._get_timestamp(data[idx], timestamp_column, idx)

            results.append(
                AnomalyResult(
                    rule_id=rule.id,
                    chart_id=rule.chart_id,
                    metric=metric,
                    anomaly_type=AnomalyRuleType.CONSECUTIVE,
                    direction=anomaly_direction or direction,
                    current_value=valid_values[-1],
                    is_anomaly=is_anomaly,
                    message=message,
                    row_index=idx,
                    timestamp=timestamp,
                    consecutive_count=consecutive_count,
                    consecutive_values=valid_values,
                )
            )

        return results

    def _get_numeric_value(self, row: dict[str, Any], metric: str) -> float | None:
        """
        Extract numeric value from a data row.
        """
        value = row.get(metric)
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _get_timestamp(
        self, row: dict[str, Any], timestamp_column: str | None, idx: int
    ) -> str | None:
        """
        Extract timestamp from a data row.
        """
        if timestamp_column:
            ts = row.get(timestamp_column)
            if ts:
                return str(ts)
        return f"row_{idx}"

    def _compute_summary(
        self, results: list[AnomalyResult], data: list[dict[str, Any]]
    ) -> AnomalySummary:
        """
        Compute summary statistics for anomaly detection results.
        """
        anomaly_results = [r for r in results if r.get("is_anomaly", False)]
        anomaly_count = len(anomaly_results)

        if not anomaly_results:
            return AnomalySummary(
                total_points=len(data),
                anomaly_count=0,
                first_anomaly_idx=None,
                last_anomaly_idx=None,
                max_deviation=None,
                max_deviation_direction=None,
            )

        first_idx = min(r["row_index"] for r in anomaly_results if r.get("row_index") is not None)
        last_idx = max(r["row_index"] for r in anomaly_results if r.get("row_index") is not None)

        max_deviation = 0.0
        max_deviation_dir: str | None = None

        for r in anomaly_results:
            change_percent = r.get("change_percent")
            if change_percent is not None and abs(change_percent) > abs(max_deviation):
                max_deviation = change_percent
                max_deviation_dir = r.get("direction")

        return AnomalySummary(
            total_points=len(data),
            anomaly_count=anomaly_count,
            first_anomaly_idx=first_idx,
            last_anomaly_idx=last_idx,
            max_deviation=max_deviation,
            max_deviation_direction=max_deviation_dir,
        )


anomaly_detector = AnomalyDetector()
