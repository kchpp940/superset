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
from datetime import datetime
from typing import Any

from flask_appbuilder import Model
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
)
from sqlalchemy.orm import backref, relationship
from sqlalchemy_utils import UUIDType

from superset.extensions import security_manager
from superset.models.dashboard import Dashboard
from superset.models.helpers import AuditMixinNullable, ExtraJSONMixin, ImportExportMixin
from superset.models.slice import Slice
from superset.utils.backports import StrEnum

logger = logging.getLogger(__name__)


class AnomalyRuleType(StrEnum):
    THRESHOLD = "threshold"
    MOM = "mom"
    YOY = "yoy"
    PERIOD_OVER_PERIOD = "period_over_period"
    CONSECUTIVE = "consecutive"


class AnomalyDirection(StrEnum):
    INCREASE = "increase"
    DECREASE = "decrease"
    BOTH = "both"


class AnomalyRuleStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    DISABLED = "disabled"


anomaly_rule_user = Table(
    "anomaly_rule_user",
    Model.metadata,  # pylint: disable=no-member
    Column("id", Integer, primary_key=True),
    Column(
        "user_id",
        Integer,
        ForeignKey("ab_user.id", ondelete="CASCADE"),
        nullable=False,
    ),
    Column(
        "anomaly_rule_id",
        Integer,
        ForeignKey("anomaly_rule.id", ondelete="CASCADE"),
        nullable=False,
    ),
)


class AnomalyRule(
    AuditMixinNullable, ExtraJSONMixin, ImportExportMixin, Model
):
    """
    Anomaly detection rules for charts and dashboards.
    Allows users to configure anomaly detection rules for metrics in charts.
    """

    __tablename__ = "anomaly_rule"
    __table_args__ = (
        Index("ix_anomaly_rule_chart_id", "chart_id"),
        Index("ix_anomaly_rule_dashboard_id", "dashboard_id"),
        Index("ix_anomaly_rule_status", "status"),
        Index("ix_anomaly_rule_created_by", "created_by_fk"),
    )

    id = Column(Integer, primary_key=True)
    uuid = Column(
        UUIDType(binary=True), primary_key=False, unique=True, nullable=False
    )

    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    chart_id = Column(Integer, ForeignKey("slices.id"), nullable=True)
    dashboard_id = Column(Integer, ForeignKey("dashboards.id"), nullable=True)

    chart = relationship(Slice, backref="anomaly_rules", foreign_keys=[chart_id])
    dashboard = relationship(
        Dashboard, backref="anomaly_rules", foreign_keys=[dashboard_id]
    )

    metric = Column(String(255), nullable=False)
    metric_label = Column(String(500), nullable=True)

    rule_type = Column(String(50), nullable=False)
    direction = Column(String(50), nullable=False, default=AnomalyDirection.BOTH)

    threshold_min = Column(Float, nullable=True)
    threshold_max = Column(Float, nullable=True)

    mom_threshold = Column(Float, nullable=True)
    yoy_threshold = Column(Float, nullable=True)
    period_offset = Column(String(50), nullable=True)
    period_offset_count = Column(Integer, nullable=True)

    consecutive_count = Column(Integer, nullable=True)
    consecutive_direction = Column(String(50), nullable=True)

    time_granularity = Column(String(50), nullable=True)

    status = Column(
        String(50), nullable=False, default=AnomalyRuleStatus.ACTIVE
    )

    last_anomaly_dttm = Column(DateTime, nullable=True)
    last_anomaly_value = Column(Float, nullable=True)
    last_anomaly_message = Column(Text, nullable=True)

    notify_enabled = Column(Boolean, default=False)
    notify_on_first_anomaly = Column(Boolean, default=True)
    notify_on_all_anomalies = Column(Boolean, default=False)
    notify_min_anomaly_count = Column(Integer, default=1)
    notify_include_screenshot = Column(Boolean, default=True)
    notify_include_data = Column(Boolean, default=False)

    owners = relationship(
        security_manager.user_model,
        secondary=anomaly_rule_user,
        passive_deletes=True,
    )

    def __repr__(self) -> str:
        return f"<AnomalyRule {self.id}: {self.name}>"

    @property
    def rule_config(self) -> dict[str, Any]:
        return {
            "rule_type": self.rule_type,
            "direction": self.direction,
            "threshold_min": self.threshold_min,
            "threshold_max": self.threshold_max,
            "mom_threshold": self.mom_threshold,
            "yoy_threshold": self.yoy_threshold,
            "period_offset": self.period_offset,
            "period_offset_count": self.period_offset_count,
            "consecutive_count": self.consecutive_count,
            "consecutive_direction": self.consecutive_direction,
            "time_granularity": self.time_granularity,
        }

    @property
    def notification_config(self) -> dict[str, Any]:
        return {
            "enabled": self.notify_enabled,
            "notify_on_first_anomaly": self.notify_on_first_anomaly,
            "notify_on_all_anomalies": self.notify_on_all_anomalies,
            "min_anomaly_count": self.notify_min_anomaly_count,
            "include_chart_screenshot": self.notify_include_screenshot,
            "include_data_table": self.notify_include_data,
        }

    def update_last_anomaly(
        self,
        value: float,
        message: str,
    ) -> None:
        self.last_anomaly_dttm = datetime.utcnow()
        self.last_anomaly_value = value
        self.last_anomaly_message = message


class AnomalyDetectionLog(Model):
    """
    Log of anomaly detections for audit and notification history.
    """

    __tablename__ = "anomaly_detection_log"
    __table_args__ = (
        Index("ix_anomaly_detection_log_rule_id", "rule_id"),
        Index("ix_anomaly_detection_log_dttm", "dttm"),
        Index("ix_anomaly_detection_log_is_anomaly", "is_anomaly"),
    )

    id = Column(Integer, primary_key=True)
    uuid = Column(
        UUIDType(binary=True), primary_key=False, unique=True, nullable=False
    )

    rule_id = Column(
        Integer, ForeignKey("anomaly_rule.id", ondelete="CASCADE"), nullable=False
    )
    rule = relationship(
        AnomalyRule,
        backref=backref(
            "detection_logs", cascade="all,delete,delete-orphan"
        ),
        foreign_keys=[rule_id],
    )

    dttm = Column(DateTime, nullable=False, default=datetime.utcnow)

    is_anomaly = Column(Boolean, nullable=False)
    anomaly_type = Column(String(50), nullable=True)
    direction = Column(String(50), nullable=True)

    current_value = Column(Float, nullable=True)
    reference_value = Column(Float, nullable=True)
    change_percent = Column(Float, nullable=True)
    change_absolute = Column(Float, nullable=True)

    threshold = Column(Float, nullable=True)
    threshold_min = Column(Float, nullable=True)
    threshold_max = Column(Float, nullable=True)

    row_index = Column(Integer, nullable=True)
    timestamp = Column(DateTime, nullable=True)

    consecutive_count = Column(Integer, nullable=True)

    message = Column(Text, nullable=True)

    notification_sent = Column(Boolean, default=False)
    notification_dttm = Column(DateTime, nullable=True)

    extra_json = Column(Text, default="{}")

    def __repr__(self) -> str:
        return f"<AnomalyDetectionLog {self.id}: rule={self.rule_id}, anomaly={self.is_anomaly}>"
