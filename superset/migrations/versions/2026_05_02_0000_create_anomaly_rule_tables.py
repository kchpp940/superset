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
"""Create anomaly_rule and anomaly_detection_log tables for Anomaly Detection Framework

Revision ID: 5a3b9c7e2f4a
Revises: 4b2a8c9d3e1f
Create Date: 2026-05-02 00:00:00.000000

"""

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy_utils import UUIDType

from superset.migrations.shared.utils import (
    create_fks_for_table,
    create_index,
    create_table,
    drop_fks_for_table,
    drop_index,
    drop_table,
)

# revision identifiers, used by Alembic.
revision = "5a3b9c7e2f4a"
down_revision = "4b2a8c9d3e1f"

ANOMALY_RULE_TABLE = "anomaly_rule"
ANOMALY_RULE_USER_TABLE = "anomaly_rule_user"
ANOMALY_DETECTION_LOG_TABLE = "anomaly_detection_log"


def upgrade():
    """
    Create anomaly detection tables for the Anomaly Detection Framework.

    This migration creates:
    1. anomaly_rule table - stores anomaly detection rule configurations
       - Supports threshold, MOM/YOY period-over-period, and consecutive anomaly rules
       - Links to charts (slices) and dashboards
       - Includes notification configuration
    2. anomaly_rule_user table - many-to-many relationship for rule owners
    3. anomaly_detection_log table - logs of anomaly detection runs
       - Records detected anomalies and their details
       - Tracks notification status
    """

    # Create anomaly_rule table
    create_table(
        ANOMALY_RULE_TABLE,
        Column("id", Integer, primary_key=True),
        Column("uuid", UUIDType(binary=True), nullable=False, unique=True),
        Column("name", String(255), nullable=False),
        Column("description", Text, nullable=True),
        Column("chart_id", Integer, nullable=True),
        Column("dashboard_id", Integer, nullable=True),
        Column("metric", String(255), nullable=False),
        Column("metric_label", String(500), nullable=True),
        Column("rule_type", String(50), nullable=False),
        Column("direction", String(50), nullable=False, server_default="both"),
        Column("threshold_min", Float, nullable=True),
        Column("threshold_max", Float, nullable=True),
        Column("mom_threshold", Float, nullable=True),
        Column("yoy_threshold", Float, nullable=True),
        Column("period_offset", String(50), nullable=True),
        Column("period_offset_count", Integer, nullable=True),
        Column("consecutive_count", Integer, nullable=True),
        Column("consecutive_direction", String(50), nullable=True),
        Column("time_granularity", String(50), nullable=True),
        Column("status", String(50), nullable=False, server_default="active"),
        Column("last_anomaly_dttm", DateTime, nullable=True),
        Column("last_anomaly_value", Float, nullable=True),
        Column("last_anomaly_message", Text, nullable=True),
        Column("notify_enabled", Boolean, nullable=True, server_default="0"),
        Column(
            "notify_on_first_anomaly", Boolean, nullable=True, server_default="1"
        ),
        Column(
            "notify_on_all_anomalies", Boolean, nullable=True, server_default="0"
        ),
        Column("notify_min_anomaly_count", Integer, nullable=True, server_default="1"),
        Column(
            "notify_include_screenshot", Boolean, nullable=True, server_default="1"
        ),
        Column("notify_include_data", Boolean, nullable=True, server_default="0"),
        # AuditMixinNullable columns
        Column("created_on", DateTime, nullable=True),
        Column("changed_on", DateTime, nullable=True),
        Column("created_by_fk", Integer, nullable=True),
        Column("changed_by_fk", Integer, nullable=True),
        # ExtraJSONMixin columns
        Column("extra_json", Text, nullable=True, server_default="{}"),
    )

    # Create indexes for anomaly_rule
    create_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_chart_id", ["chart_id"])
    create_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_dashboard_id", ["dashboard_id"])
    create_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_status", ["status"])
    create_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_created_by", ["created_by_fk"])
    create_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_uuid", ["uuid"], unique=True)

    # Create foreign key constraints for anomaly_rule
    create_fks_for_table(
        foreign_key_name="fk_anomaly_rule_chart_id_slices",
        table_name=ANOMALY_RULE_TABLE,
        referenced_table="slices",
        local_cols=["chart_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )

    create_fks_for_table(
        foreign_key_name="fk_anomaly_rule_dashboard_id_dashboards",
        table_name=ANOMALY_RULE_TABLE,
        referenced_table="dashboards",
        local_cols=["dashboard_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )

    create_fks_for_table(
        foreign_key_name="fk_anomaly_rule_created_by_fk_ab_user",
        table_name=ANOMALY_RULE_TABLE,
        referenced_table="ab_user",
        local_cols=["created_by_fk"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )

    create_fks_for_table(
        foreign_key_name="fk_anomaly_rule_changed_by_fk_ab_user",
        table_name=ANOMALY_RULE_TABLE,
        referenced_table="ab_user",
        local_cols=["changed_by_fk"],
        remote_cols=["id"],
        ondelete="SET NULL",
    )

    # Create anomaly_rule_user table (many-to-many)
    create_table(
        ANOMALY_RULE_USER_TABLE,
        Column("id", Integer, primary_key=True),
        Column("user_id", Integer, nullable=False),
        Column("anomaly_rule_id", Integer, nullable=False),
        # Unique constraint defined as part of table creation (SQLite compatible)
        UniqueConstraint("user_id", "anomaly_rule_id", name="uq_anomaly_rule_user"),
    )

    # Create indexes for anomaly_rule_user
    create_index(
        ANOMALY_RULE_USER_TABLE, "ix_anomaly_rule_user_user_id", ["user_id"]
    )
    create_index(
        ANOMALY_RULE_USER_TABLE,
        "ix_anomaly_rule_user_anomaly_rule_id",
        ["anomaly_rule_id"],
    )

    # Create foreign key constraints for anomaly_rule_user
    create_fks_for_table(
        foreign_key_name="fk_anomaly_rule_user_user_id_ab_user",
        table_name=ANOMALY_RULE_USER_TABLE,
        referenced_table="ab_user",
        local_cols=["user_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )

    create_fks_for_table(
        foreign_key_name="fk_anomaly_rule_user_anomaly_rule_id_anomaly_rule",
        table_name=ANOMALY_RULE_USER_TABLE,
        referenced_table=ANOMALY_RULE_TABLE,
        local_cols=["anomaly_rule_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )

    # Create anomaly_detection_log table
    create_table(
        ANOMALY_DETECTION_LOG_TABLE,
        Column("id", Integer, primary_key=True),
        Column("uuid", UUIDType(binary=True), nullable=False, unique=True),
        Column("rule_id", Integer, nullable=False),
        Column("dttm", DateTime, nullable=False),
        Column("is_anomaly", Boolean, nullable=False),
        Column("anomaly_type", String(50), nullable=True),
        Column("direction", String(50), nullable=True),
        Column("current_value", Float, nullable=True),
        Column("reference_value", Float, nullable=True),
        Column("change_percent", Float, nullable=True),
        Column("change_absolute", Float, nullable=True),
        Column("threshold", Float, nullable=True),
        Column("threshold_min", Float, nullable=True),
        Column("threshold_max", Float, nullable=True),
        Column("row_index", Integer, nullable=True),
        Column("timestamp", DateTime, nullable=True),
        Column("consecutive_count", Integer, nullable=True),
        Column("message", Text, nullable=True),
        Column("notification_sent", Boolean, nullable=True, server_default="0"),
        Column("notification_dttm", DateTime, nullable=True),
        Column("extra_json", Text, nullable=True, server_default="{}"),
    )

    # Create indexes for anomaly_detection_log
    create_index(
        ANOMALY_DETECTION_LOG_TABLE, "ix_anomaly_detection_log_rule_id", ["rule_id"]
    )
    create_index(
        ANOMALY_DETECTION_LOG_TABLE, "ix_anomaly_detection_log_dttm", ["dttm"]
    )
    create_index(
        ANOMALY_DETECTION_LOG_TABLE,
        "ix_anomaly_detection_log_is_anomaly",
        ["is_anomaly"],
    )
    create_index(
        ANOMALY_DETECTION_LOG_TABLE, "ix_anomaly_detection_log_uuid", ["uuid"], unique=True
    )

    # Create foreign key constraints for anomaly_detection_log
    create_fks_for_table(
        foreign_key_name="fk_anomaly_detection_log_rule_id_anomaly_rule",
        table_name=ANOMALY_DETECTION_LOG_TABLE,
        referenced_table=ANOMALY_RULE_TABLE,
        local_cols=["rule_id"],
        remote_cols=["id"],
        ondelete="CASCADE",
    )


def downgrade():
    """
    Drop anomaly detection tables and all related indexes and foreign keys.
    """
    # Drop anomaly_detection_log first (depends on anomaly_rule)
    drop_fks_for_table(
        ANOMALY_DETECTION_LOG_TABLE,
        ["fk_anomaly_detection_log_rule_id_anomaly_rule"],
    )
    drop_index(ANOMALY_DETECTION_LOG_TABLE, "ix_anomaly_detection_log_rule_id")
    drop_index(ANOMALY_DETECTION_LOG_TABLE, "ix_anomaly_detection_log_dttm")
    drop_index(ANOMALY_DETECTION_LOG_TABLE, "ix_anomaly_detection_log_is_anomaly")
    drop_index(ANOMALY_DETECTION_LOG_TABLE, "ix_anomaly_detection_log_uuid")
    drop_table(ANOMALY_DETECTION_LOG_TABLE)

    # Drop anomaly_rule_user (depends on anomaly_rule)
    drop_fks_for_table(
        ANOMALY_RULE_USER_TABLE,
        [
            "fk_anomaly_rule_user_user_id_ab_user",
            "fk_anomaly_rule_user_anomaly_rule_id_anomaly_rule",
        ],
    )
    drop_index(ANOMALY_RULE_USER_TABLE, "ix_anomaly_rule_user_user_id")
    drop_index(ANOMALY_RULE_USER_TABLE, "ix_anomaly_rule_user_anomaly_rule_id")
    drop_table(ANOMALY_RULE_USER_TABLE)

    # Drop anomaly_rule
    drop_fks_for_table(
        ANOMALY_RULE_TABLE,
        [
            "fk_anomaly_rule_chart_id_slices",
            "fk_anomaly_rule_dashboard_id_dashboards",
            "fk_anomaly_rule_created_by_fk_ab_user",
            "fk_anomaly_rule_changed_by_fk_ab_user",
        ],
    )
    drop_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_chart_id")
    drop_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_dashboard_id")
    drop_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_status")
    drop_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_created_by")
    drop_index(ANOMALY_RULE_TABLE, "ix_anomaly_rule_uuid")
    drop_table(ANOMALY_RULE_TABLE)
