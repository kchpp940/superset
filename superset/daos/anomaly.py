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
from datetime import datetime, timedelta
from typing import Any, cast, Optional
from uuid import UUID

from flask_appbuilder.models.sqla.interface import SQLAInterface
from sqlalchemy import and_

from superset.daos.base import BaseDAO
from superset.extensions import db
from superset.models.dashboard import Dashboard
from superset.models.slice import Slice
from superset.anomalies.models import (
    AnomalyDetectionLog,
    AnomalyRule,
    AnomalyRuleStatus,
)

logger = logging.getLogger(__name__)


class AnomalyRuleDAO(BaseDAO[AnomalyRule]):
    """
    DAO for AnomalyRule model.
    """

    @staticmethod
    def find_by_chart_id(chart_id: int) -> list[AnomalyRule]:
        """
        Find all active anomaly rules for a specific chart.
        """
        return (
            db.session.query(AnomalyRule)
            .filter(
                AnomalyRule.chart_id == chart_id,
                AnomalyRule.status == AnomalyRuleStatus.ACTIVE,
            )
            .all()
        )

    @staticmethod
    def find_by_chart_ids(chart_ids: list[int]) -> list[AnomalyRule]:
        """
        Find all active anomaly rules for a list of charts.
        """
        if not chart_ids:
            return []
        return (
            db.session.query(AnomalyRule)
            .filter(
                AnomalyRule.chart_id.in_(chart_ids),
                AnomalyRule.status == AnomalyRuleStatus.ACTIVE,
            )
            .all()
        )

    @staticmethod
    def find_by_dashboard_id(dashboard_id: int) -> list[AnomalyRule]:
        """
        Find all active anomaly rules for a specific dashboard.
        """
        return (
            db.session.query(AnomalyRule)
            .filter(
                AnomalyRule.dashboard_id == dashboard_id,
                AnomalyRule.status == AnomalyRuleStatus.ACTIVE,
            )
            .all()
        )

    @staticmethod
    def find_by_chart_and_metric(chart_id: int, metric: str) -> list[AnomalyRule]:
        """
        Find all active anomaly rules for a specific chart and metric.
        """
        return (
            db.session.query(AnomalyRule)
            .filter(
                AnomalyRule.chart_id == chart_id,
                AnomalyRule.metric == metric,
                AnomalyRule.status == AnomalyRuleStatus.ACTIVE,
            )
            .all()
        )

    @staticmethod
    def find_by_id(rule_id: int) -> AnomalyRule | None:
        """
        Find an anomaly rule by ID.
        """
        return db.session.query(AnomalyRule).filter_by(id=rule_id).one_or_none()

    @staticmethod
    def find_by_uuid(uuid: str | UUID) -> AnomalyRule | None:
        """
        Find an anomaly rule by UUID.
        """
        return (
            db.session.query(AnomalyRule)
            .filter(AnomalyRule.uuid == str(uuid))
            .one_or_none()
        )

    @staticmethod
    def find_rules_with_notification_enabled() -> list[AnomalyRule]:
        """
        Find all active rules with notifications enabled.
        """
        return (
            db.session.query(AnomalyRule)
            .filter(
                AnomalyRule.status == AnomalyRuleStatus.ACTIVE,
                AnomalyRule.notify_enabled.is_(True),
            )
            .all()
        )

    @staticmethod
    def create(
        item: AnomalyRule | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> AnomalyRule:
        """
        Create an anomaly rule with owner handling.
        """
        if not item:
            item = AnomalyRule()

        if attributes:
            if owners := attributes.pop("owners", None):
                from superset.extensions import security_manager

                user_model = security_manager.user_model
                user_ids = (
                    [owners] if isinstance(owners, int) else list(owners)
                )
                users = (
                    db.session.query(user_model)
                    .filter(user_model.id.in_(user_ids))
                    .all()
                )
                attributes["owners"] = users

        return super().create(item, attributes)

    @staticmethod
    def update(
        item: AnomalyRule | None = None,
        attributes: dict[str, Any] | None = None,
    ) -> AnomalyRule:
        """
        Update an anomaly rule with owner handling.
        """
        if attributes and "owners" in attributes:
            from superset.extensions import security_manager

            user_model = security_manager.user_model
            owners = attributes.pop("owners")
            user_ids = [owners] if isinstance(owners, int) else list(owners)
            users = (
                db.session.query(user_model)
                .filter(user_model.id.in_(user_ids))
                .all()
            )
            attributes["owners"] = users

        return super().update(item, attributes)


class AnomalyDetectionLogDAO(BaseDAO[AnomalyDetectionLog]):
    """
    DAO for AnomalyDetectionLog model.
    """

    @staticmethod
    def find_by_rule_id(
        rule_id: int, limit: int = 100
    ) -> list[AnomalyDetectionLog]:
        """
        Find detection logs for a specific rule, ordered by dttm descending.
        """
        return (
            db.session.query(AnomalyDetectionLog)
            .filter(AnomalyDetectionLog.rule_id == rule_id)
            .order_by(AnomalyDetectionLog.dttm.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def find_anomalies_by_rule_id(
        rule_id: int,
        start_dttm: datetime | None = None,
        end_dttm: datetime | None = None,
        limit: int = 1000,
    ) -> list[AnomalyDetectionLog]:
        """
        Find anomaly detection logs (where is_anomaly is True) for a rule.
        """
        query = db.session.query(AnomalyDetectionLog).filter(
            AnomalyDetectionLog.rule_id == rule_id,
            AnomalyDetectionLog.is_anomaly.is_(True),
        )

        if start_dttm:
            query = query.filter(AnomalyDetectionLog.dttm >= start_dttm)
        if end_dttm:
            query = query.filter(AnomalyDetectionLog.dttm <= end_dttm)

        return (
            query.order_by(AnomalyDetectionLog.dttm.desc())
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_recent_anomaly_count(
        rule_id: int, hours: int = 24
    ) -> int:
        """
        Get the count of anomalies detected in the last N hours.
        """
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        return (
            db.session.query(AnomalyDetectionLog)
            .filter(
                AnomalyDetectionLog.rule_id == rule_id,
                AnomalyDetectionLog.is_anomaly.is_(True),
                AnomalyDetectionLog.dttm >= cutoff_time,
            )
            .count()
        )

    @staticmethod
    def get_last_anomaly(rule_id: int) -> AnomalyDetectionLog | None:
        """
        Get the most recent anomaly for a rule.
        """
        return (
            db.session.query(AnomalyDetectionLog)
            .filter(
                AnomalyDetectionLog.rule_id == rule_id,
                AnomalyDetectionLog.is_anomaly.is_(True),
            )
            .order_by(AnomalyDetectionLog.dttm.desc())
            .first()
        )

    @staticmethod
    def get_consecutive_anomalies(
        rule_id: int,
        count: int,
        direction: str | None = None,
    ) -> list[AnomalyDetectionLog]:
        """
        Get the last N anomalies to check for consecutive patterns.
        """
        query = (
            db.session.query(AnomalyDetectionLog)
            .filter(
                AnomalyDetectionLog.rule_id == rule_id,
                AnomalyDetectionLog.is_anomaly.is_(True),
            )
            .order_by(AnomalyDetectionLog.dttm.desc())
        )

        if direction:
            query = query.filter(AnomalyDetectionLog.direction == direction)

        return query.limit(count).all()

    @staticmethod
    def create_log(
        rule: AnomalyRule,
        is_anomaly: bool,
        anomaly_type: str | None = None,
        direction: str | None = None,
        current_value: float | None = None,
        reference_value: float | None = None,
        change_percent: float | None = None,
        change_absolute: float | None = None,
        threshold: float | None = None,
        threshold_min: float | None = None,
        threshold_max: float | None = None,
        row_index: int | None = None,
        timestamp: datetime | None = None,
        consecutive_count: int | None = None,
        message: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> AnomalyDetectionLog:
        """
        Create a new detection log entry.
        """
        from uuid import uuid4

        log = AnomalyDetectionLog(
            uuid=uuid4(),
            rule=rule,
            dttm=datetime.utcnow(),
            is_anomaly=is_anomaly,
            anomaly_type=anomaly_type,
            direction=direction,
            current_value=current_value,
            reference_value=reference_value,
            change_percent=change_percent,
            change_absolute=change_absolute,
            threshold=threshold,
            threshold_min=threshold_min,
            threshold_max=threshold_max,
            row_index=row_index,
            timestamp=timestamp,
            consecutive_count=consecutive_count,
            message=message,
            notification_sent=False,
            extra_json=extra or {},
        )
        db.session.add(log)
        return log

    @staticmethod
    def mark_notification_sent(log_id: int) -> None:
        """
        Mark a detection log as having notification sent.
        """
        log = (
            db.session.query(AnomalyDetectionLog)
            .filter_by(id=log_id)
            .one_or_none()
        )
        if log:
            log.notification_sent = True
            log.notification_dttm = datetime.utcnow()
            db.session.commit()
