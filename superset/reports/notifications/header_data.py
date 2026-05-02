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
"""
Utilities for building report/alert notification header data.

This module provides helper functions to:
1. Build HeaderDataType from ReportSchedule and execution_id

The extract_webhook_header function is in superset.utils.core to avoid
circular imports (this module depends on ReportSchedule model).
"""

from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from superset.reports.models import (
    ReportRecipientType,
    ReportSourceFormat,
)

if TYPE_CHECKING:
    from superset.reports.models import ReportSchedule
    from superset.utils.core import HeaderDataType


def build_header_data(
    report_schedule: ReportSchedule,
    execution_id: UUID | str,
) -> HeaderDataType:
    """
    Build a HeaderDataType dictionary from a ReportSchedule and execution ID.

    This function centralizes the logic that was previously in
    BaseReportState._get_log_data(). It determines:
    - Whether the report source is a Chart or Dashboard
    - Extracts relevant IDs (chart_id or dashboard_id)
    - Collects Slack channel configurations from recipients
    - Maps report_schedule type and format to notification_type/format

    Args:
        report_schedule: The ReportSchedule ORM model instance
        execution_id: UUID or string identifying the execution context

    Returns:
        HeaderDataType: A typed dictionary containing all notification header fields:
            - notification_type: "Alert" or "Report"
            - notification_source: "chart" or "dashboard"
            - notification_format: "PDF", "PNG", "CSV", or "TEXT"
            - chart_id: Integer ID if source is chart, None otherwise
            - dashboard_id: Integer ID if source is dashboard, None otherwise
            - owners: List of user IDs who own this report
            - slack_channels: List of Slack channel configs from recipients
            - execution_id: Stringified execution UUID

    Example:
        >>> header = build_header_data(report_schedule, execution_id)
        >>> header["notification_source"]
        'chart'
        >>> header["chart_id"]
        123
    """
    from superset.utils.core import HeaderDataType

    chart_id: int | None = None
    dashboard_id: int | None = None
    report_source: ReportSourceFormat | None = None
    slack_channels: list[str] | None = None

    if report_schedule.chart:
        report_source = ReportSourceFormat.CHART
        chart_id = report_schedule.chart_id
    else:
        report_source = ReportSourceFormat.DASHBOARD
        dashboard_id = report_schedule.dashboard_id

    if report_schedule.recipients:
        slack_channels = [
            recipient.recipient_config_json
            for recipient in report_schedule.recipients
            if recipient.type
            in [ReportRecipientType.SLACK, ReportRecipientType.SLACKV2]
        ]

    header_data: HeaderDataType = {
        "notification_type": report_schedule.type,
        "notification_source": report_source,
        "notification_format": report_schedule.report_format,
        "chart_id": chart_id,
        "dashboard_id": dashboard_id,
        "owners": report_schedule.owners,
        "slack_channels": slack_channels,
        "execution_id": str(execution_id),
    }

    return header_data
