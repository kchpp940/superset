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


import pandas as pd
import pytest

from superset.reports.notifications.exceptions import (
    NotificationParamException,
)
from superset.reports.notifications.webhook import WebhookNotification
from superset.utils.core import (
    HeaderDataType,
    extract_webhook_header,
    WebhookHeaderDataType,
)


@pytest.fixture
def mock_header_data() -> HeaderDataType:
    return {
        "notification_format": "PNG",
        "notification_type": "Alert",
        "owners": [1],
        "notification_source": None,
        "chart_id": None,
        "dashboard_id": None,
        "slack_channels": None,
        "execution_id": "test-execution-id",
    }


def test_extract_webhook_header_basic(mock_header_data: HeaderDataType) -> None:
    """
    Test that extract_webhook_header correctly extracts only the required fields
    and excludes extra fields like owners, slack_channels, and execution_id
    """
    result = extract_webhook_header(mock_header_data)

    assert result["notification_format"] == "PNG"
    assert result["notification_type"] == "Alert"
    assert result["notification_source"] is None
    assert result["chart_id"] is None
    assert result["dashboard_id"] is None

    assert "owners" not in result
    assert "slack_channels" not in result
    assert "execution_id" not in result


def test_extract_webhook_header_with_chart_id() -> None:
    """
    Test that extract_webhook_header correctly extracts chart_id for chart sources
    """
    header_data: HeaderDataType = {
        "notification_format": "CSV",
        "notification_type": "Report",
        "owners": [1, 2],
        "notification_source": "chart",
        "chart_id": 123,
        "dashboard_id": None,
        "slack_channels": ["#alerts"],
        "execution_id": "chart-exec-123",
    }

    result: WebhookHeaderDataType = extract_webhook_header(header_data)

    assert result["chart_id"] == 123
    assert result["dashboard_id"] is None
    assert result["notification_source"] == "chart"
    assert result["notification_format"] == "CSV"
    assert result["notification_type"] == "Report"


def test_extract_webhook_header_with_dashboard_id() -> None:
    """
    Test that extract_webhook_header correctly extracts dashboard_id for dashboard sources
    """
    header_data: HeaderDataType = {
        "notification_format": "PDF",
        "notification_type": "Alert",
        "owners": [1],
        "notification_source": "dashboard",
        "chart_id": None,
        "dashboard_id": 456,
        "slack_channels": ["#dashboard-alerts"],
        "execution_id": "dash-exec-456",
    }

    result = extract_webhook_header(header_data)

    assert result["dashboard_id"] == 456
    assert result["chart_id"] is None
    assert result["notification_source"] == "dashboard"


def test_get_webhook_url(mock_header_data) -> None:
    """
    Test the _get_webhook_url function to ensure it correctly extracts
    the webhook URL from recipient configuration
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="test alert",
        header_data=mock_header_data,
        embedded_data=pd.DataFrame({"A": [1, 2, 3], "B": [4, 5, 6]}),
        description="Test description",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://example.com/webhook"}',
        ),
        content=content,
    )

    result = webhook_notification._get_webhook_url()

    assert result == "https://example.com/webhook"


def test_get_webhook_url_missing_url(mock_header_data) -> None:
    """
    Test that _get_webhook_url raises an exception when URL is missing
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="test alert",
        header_data=mock_header_data,
        description="Test description",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json="{}",
        ),
        content=content,
    )

    with pytest.raises(NotificationParamException, match="Webhook URL is required"):
        webhook_notification._get_webhook_url()


def test_get_req_payload_basic(mock_header_data) -> None:
    """
    Test that _get_req_payload returns correct payload structure
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="Payload Name",
        header_data=mock_header_data,
        embedded_data=None,
        description="Payload Description",
        url="http://example.com/report",
        text="Report Text",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://webhook.com"}',
        ),
        content=content,
    )

    payload = webhook_notification._get_req_payload()

    assert payload["name"] == "Payload Name"
    assert payload["description"] == "Payload Description"
    assert payload["url"] == "http://example.com/report"
    assert payload["text"] == "Report Text"
    assert isinstance(payload["header"], dict)
    # Optional fields from header_data
    assert payload["header"]["notification_format"] == "PNG"
    assert payload["header"]["notification_type"] == "Alert"


def test_get_files_includes_all_content_types(mock_header_data) -> None:
    """
    Test that _get_files correctly includes csv, pdf, and multiple screenshot attachments
    """  # noqa: E501

    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    csv_bytes = b"col1,col2\n1,2"
    pdf_bytes = b"%PDF-1.4"
    screenshots = [b"fakeimg1", b"fakeimg2"]

    content = NotificationContent(
        name="file test",
        header_data=mock_header_data,
        csv=csv_bytes,
        pdf=pdf_bytes,
        screenshots=screenshots,
        description="files test",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://webhook.com"}',
        ),
        content=content,
    )
    files = webhook_notification._get_files()
    # There should be 1 csv, 1 pdf, and 2 screenshots = 4 files total
    assert len(files) == 4

    file_names = [file_info[1][0] for file_info in files]
    assert "report.csv" in file_names
    assert "report.pdf" in file_names
    assert "screenshot_0.png" in file_names
    assert "screenshot_1.png" in file_names

    mime_types = [file_info[1][2] for file_info in files]
    assert "text/csv" in mime_types
    assert "application/pdf" in mime_types
    assert mime_types.count("image/png") == 2


def test_get_files_empty_when_no_content(mock_header_data) -> None:
    """
    Test that _get_files returns empty list when no files present
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="no files",
        header_data=mock_header_data,
        description="no files test",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://webhook.com"}',
        ),
        content=content,
    )
    files = webhook_notification._get_files()
    assert files == []


def test_send_http_only_https_check(monkeypatch, mock_header_data) -> None:
    """
    Test send raises when URL is not HTTPS and config enforces HTTPS only
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="test alert", header_data=mock_header_data, description="Test description"
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "http://notsecure.com/webhook"}',
        ),
        content=content,
    )

    class MockCurrentApp:
        config = {"ALERT_REPORTS_WEBHOOK_HTTPS_ONLY": True}

    monkeypatch.setattr(
        "superset.reports.notifications.webhook.current_app", MockCurrentApp
    )
    monkeypatch.setattr(
        "superset.reports.notifications.webhook.feature_flag_manager.is_feature_enabled",
        lambda flag: True,
    )

    with pytest.raises(NotificationParamException, match="HTTPS is required by config"):
        webhook_notification.send()


def test_get_req_payload_excludes_sensitive_fields(mock_header_data) -> None:
    """
    Contract test: Webhook payload MUST NOT expose sensitive fields.
    Prevents regression: owners/slack_channels/execution_id should never leak to webhook.
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    sensitive_header_data: HeaderDataType = {
        "notification_format": "PNG",
        "notification_type": "Alert",
        "notification_source": "chart",
        "chart_id": 123,
        "dashboard_id": 456,
        "owners": [1, 2, 3],
        "slack_channels": ["channel-id-1", "channel-id-2"],
        "execution_id": "sensitive-execution-uuid-12345",
    }

    content = NotificationContent(
        name="Sensitive Data Test",
        header_data=sensitive_header_data,
        description="Test description",
        url="http://example.com/report",
        text="Report Text",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://webhook.example.com/endpoint"}',
        ),
        content=content,
    )

    payload = webhook_notification._get_req_payload()

    assert "owners" not in payload, "owners field MUST NOT be present in webhook payload"
    assert (
        "slack_channels" not in payload
    ), "slack_channels field MUST NOT be present in webhook payload"
    assert (
        "execution_id" not in payload
    ), "execution_id field MUST NOT be present in webhook payload"

    assert "header" in payload, "header field MUST be present in webhook payload"
    header = payload["header"]

    assert (
        "owners" not in header
    ), "owners field MUST NOT be present in webhook header"
    assert (
        "slack_channels" not in header
    ), "slack_channels field MUST NOT be present in webhook header"
    assert (
        "execution_id" not in header
    ), "execution_id field MUST NOT be present in webhook header"

    assert header["notification_format"] == "PNG"
    assert header["notification_type"] == "Alert"
    assert header["notification_source"] == "chart"
    assert header["chart_id"] == 123
    assert header["dashboard_id"] == 456


def test_get_req_payload_header_contract(mock_header_data) -> None:
    """
    Contract test: Verify exact fields allowed in webhook header.
    This test documents the approved API surface for webhook headers.
    """
    from superset.reports.models import ReportRecipients, ReportRecipientType
    from superset.reports.notifications.base import NotificationContent

    content = NotificationContent(
        name="Contract Test",
        header_data=mock_header_data,
        description="Contract validation test",
        url="http://example.com",
    )
    webhook_notification = WebhookNotification(
        recipient=ReportRecipients(
            type=ReportRecipientType.WEBHOOK,
            recipient_config_json='{"target": "https://webhook.com"}',
        ),
        content=content,
    )

    payload = webhook_notification._get_req_payload()
    header = payload["header"]

    APPROVED_HEADER_FIELDS = {
        "notification_format",
        "notification_type",
        "notification_source",
        "chart_id",
        "dashboard_id",
    }

    actual_fields = set(header.keys())
    unexpected_fields = actual_fields - APPROVED_HEADER_FIELDS

    assert (
        unexpected_fields == set()
    ), f"Webhook header contains unapproved fields: {unexpected_fields}. Only these fields are allowed: {APPROVED_HEADER_FIELDS}"


def test_header_data_typed_dict_contains_sensitive_fields() -> None:
    """
    Documentation test: Verify HeaderDataType TypedDict includes sensitive fields.
    This test ensures we're aware of what fields exist in the type definition.
    """
    import sys

    if sys.version_info >= (3, 11):
        from typing import get_type_hints

        hints = get_type_hints(HeaderDataType)
        type_keys = set(hints.keys())

        assert "owners" in type_keys, "HeaderDataType should define owners"
        assert "slack_channels" in type_keys, "HeaderDataType should define slack_channels"
        assert "execution_id" in type_keys, "HeaderDataType should define execution_id"
    else:
        assert hasattr(HeaderDataType, "__annotations__")
        annotations = HeaderDataType.__annotations__
        assert "owners" in annotations, "HeaderDataType should define owners"
        assert (
            "slack_channels" in annotations
        ), "HeaderDataType should define slack_channels"
        assert (
            "execution_id" in annotations
        ), "HeaderDataType should define execution_id"
