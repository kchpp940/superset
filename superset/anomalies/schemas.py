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

import re
from typing import Any

from croniter import croniter
from flask_babel import gettext as _
from marshmallow import EXCLUDE, fields, Schema, validate, validates, validates_schema
from marshmallow.validate import Length, Range, ValidationError
from pytz import all_timezones

from superset.anomalies.models import (
    AnomalyDirection,
    AnomalyRuleStatus,
    AnomalyRuleType,
)
from superset.utils import json


openapi_spec_methods_override = {
    "get": {"get": {"summary": "Get an anomaly rule"}},
    "get_list": {
        "get": {
            "summary": "Get a list of anomaly rules",
            "description": "Gets a list of anomaly rules, use Rison or JSON "
            "query parameters for filtering, sorting,"
            " pagination and for selecting specific"
            " columns and metadata.",
        }
    },
    "post": {"post": {"summary": "Create an anomaly rule"}},
    "put": {"put": {"summary": "Update an anomaly rule"}},
    "delete": {"delete": {"summary": "Delete an anomaly rule"}},
    "info": {"get": {"summary": "Get metadata information about this API resource"}},
}

get_delete_ids_schema = {"type": "array", "items": {"type": "integer"}}

name_description = "The name of the anomaly rule."
description_description = "A description of the anomaly rule."
chart_description = "The chart id this rule applies to."
dashboard_description = "The dashboard id this rule applies to."
metric_description = "The metric column name to monitor."
metric_label_description = "The display label for the metric."
rule_type_description = "The type of anomaly detection rule. Options: threshold, mom (month-over-month), yoy (year-over-year), period_over_period, consecutive."
direction_description = "The direction to monitor for anomalies. Options: increase, decrease, both."
threshold_min_description = "Minimum threshold for threshold-based detection. Values below this trigger an anomaly."
threshold_max_description = "Maximum threshold for threshold-based detection. Values above this trigger an anomaly."
mom_threshold_description = "Threshold for month-over-month comparison (e.g., 0.2 means 20% change)."
yoy_threshold_description = "Threshold for year-over-year comparison (e.g., 0.2 means 20% change)."
period_offset_description = "Period offset for custom period-over-period comparison (e.g., 'P1W' for 1 week)."
period_offset_count_description = "Number of periods to offset for period-over-period comparison."
consecutive_count_description = "Number of consecutive anomalies to trigger an alert."
consecutive_direction_description = "Direction for consecutive anomaly detection: increase, decrease, or either."
time_granularity_description = "Time granularity for the analysis (e.g., 'PT1H' for hourly, 'P1D' for daily)."
status_description = "The status of the rule: active, paused, or disabled."
notify_enabled_description = "Whether notifications are enabled for this rule."
notify_on_first_anomaly_description = "Notify on the first anomaly detected."
notify_on_all_anomalies_description = "Notify on every anomaly (not just first)."
notify_min_anomaly_count_description = "Minimum number of anomalies required before sending notification."
notify_include_screenshot_description = "Include chart screenshot in notification."
notify_include_data_description = "Include data table in notification."
owners_description = "Owner user ids allowed to modify this rule. If left empty, current user will be an owner."


EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")


class AnomalyRuleValidatorConfigSchema(Schema):
    threshold_min = fields.Float(
        metadata={"description": threshold_min_description},
        allow_none=True,
    )
    threshold_max = fields.Float(
        metadata={"description": threshold_max_description},
        allow_none=True,
    )
    mom_threshold = fields.Float(
        metadata={"description": mom_threshold_description},
        allow_none=True,
    )
    yoy_threshold = fields.Float(
        metadata={"description": yoy_threshold_description},
        allow_none=True,
    )
    period_offset = fields.String(
        metadata={"description": period_offset_description},
        allow_none=True,
    )
    period_offset_count = fields.Integer(
        metadata={"description": period_offset_count_description},
        allow_none=True,
    )
    consecutive_count = fields.Integer(
        metadata={"description": consecutive_count_description},
        allow_none=True,
        validate=[Range(min=1, error=_("Value must be greater than 0"))],
    )
    consecutive_direction = fields.String(
        metadata={"description": consecutive_direction_description},
        allow_none=True,
        validate=validate.OneOf(
            choices=[AnomalyDirection.INCREASE, AnomalyDirection.DECREASE]
        ),
    )


class AnomalyNotificationConfigSchema(Schema):
    enabled = fields.Boolean(
        metadata={"description": notify_enabled_description},
        allow_none=True,
    )
    notify_on_first_anomaly = fields.Boolean(
        metadata={"description": notify_on_first_anomaly_description},
        allow_none=True,
    )
    notify_on_all_anomalies = fields.Boolean(
        metadata={"description": notify_on_all_anomalies_description},
        allow_none=True,
    )
    min_anomaly_count = fields.Integer(
        metadata={"description": notify_min_anomaly_count_description},
        allow_none=True,
        validate=[Range(min=1, error=_("Value must be greater than 0"))],
    )
    include_chart_screenshot = fields.Boolean(
        metadata={"description": notify_include_screenshot_description},
        allow_none=True,
    )
    include_data_table = fields.Boolean(
        metadata={"description": notify_include_data_description},
        allow_none=True,
    )


class AnomalyRecipientConfigSchema(Schema):
    target = fields.String()
    ccTarget = fields.String()  # noqa: N815
    bccTarget = fields.String()  # noqa: N815


class AnomalyRecipientSchema(Schema):
    type = fields.String(
        metadata={"description": "The recipient type: Email or Slack"},
        allow_none=False,
        required=True,
        validate=validate.OneOf(choices=["Email", "Slack"]),
    )
    recipient_config_json = fields.Nested(AnomalyRecipientConfigSchema)

    @validates_schema
    def validate_email_recipients(self, data: dict[str, Any], **kwargs: Any) -> None:
        if data.get("type") != "Email":
            return

        config = data.get("recipient_config_json") or {}

        def validate_addresses(field: str, value: str | None, required: bool) -> None:
            if not value or not value.strip():
                if required:
                    raise ValidationError(
                        {field: ["Email target is required for Email recipients"]}
                    )
                return
            invalid = [
                addr.strip()
                for addr in re.split(r"[,;]", value)
                if addr.strip() and not EMAIL_REGEX.match(addr.strip())
            ]
            if invalid:
                raise ValidationError(
                    {field: [f"Invalid email address(es): {', '.join(invalid)}"]}
                )

        validate_addresses("target", config.get("target"), required=True)
        validate_addresses("ccTarget", config.get("ccTarget"), required=False)
        validate_addresses("bccTarget", config.get("bccTarget"), required=False)


class AnomalyScheduleConfigSchema(Schema):
    crontab = fields.String(
        metadata={
            "description": "A CRON expression for scheduling. "
            "[Crontab Guru](https://crontab.guru/) is a helpful resource.",
            "example": "0 */6 * * *",
        },
        allow_none=True,
    )
    timezone = fields.String(
        metadata={"description": "A timezone string for the schedule."},
        allow_none=True,
        validate=validate.OneOf(choices=tuple(all_timezones)),
    )

    @validates("crontab")
    def validate_crontab(self, value: str | None) -> None:
        if value is not None and not croniter.is_valid(str(value)):
            raise ValidationError("Cron expression is not valid")


class AnomalyRulePostSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(
        metadata={"description": name_description, "example": "Sales Anomaly Monitor"},
        allow_none=False,
        required=True,
        validate=[Length(1, 250)],
    )
    description = fields.String(
        metadata={"description": description_description},
        allow_none=True,
        required=False,
    )
    chart = fields.Integer(
        metadata={"description": chart_description},
        required=False,
        allow_none=True,
    )
    dashboard = fields.Integer(
        metadata={"description": dashboard_description},
        required=False,
        allow_none=True,
    )
    metric = fields.String(
        metadata={"description": metric_description, "example": "sum__sales"},
        allow_none=False,
        required=True,
        validate=[Length(1, 255)],
    )
    metric_label = fields.String(
        metadata={"description": metric_label_description, "example": "Total Sales"},
        allow_none=True,
        required=False,
    )
    rule_type = fields.String(
        metadata={"description": rule_type_description},
        allow_none=False,
        required=True,
        validate=validate.OneOf(
            choices=[
                AnomalyRuleType.THRESHOLD,
                AnomalyRuleType.MOM,
                AnomalyRuleType.YOY,
                AnomalyRuleType.PERIOD_OVER_PERIOD,
                AnomalyRuleType.CONSECUTIVE,
            ]
        ),
    )
    direction = fields.String(
        metadata={"description": direction_description},
        allow_none=False,
        required=True,
        validate=validate.OneOf(
            choices=[
                AnomalyDirection.INCREASE,
                AnomalyDirection.DECREASE,
                AnomalyDirection.BOTH,
            ]
        ),
    )

    threshold_min = fields.Float(
        metadata={"description": threshold_min_description},
        allow_none=True,
        required=False,
    )
    threshold_max = fields.Float(
        metadata={"description": threshold_max_description},
        allow_none=True,
        required=False,
    )
    mom_threshold = fields.Float(
        metadata={"description": mom_threshold_description},
        allow_none=True,
        required=False,
    )
    yoy_threshold = fields.Float(
        metadata={"description": yoy_threshold_description},
        allow_none=True,
        required=False,
    )
    period_offset = fields.String(
        metadata={"description": period_offset_description},
        allow_none=True,
        required=False,
    )
    period_offset_count = fields.Integer(
        metadata={"description": period_offset_count_description},
        allow_none=True,
        required=False,
        validate=[Range(min=1, error=_("Value must be greater than 0"))],
    )
    consecutive_count = fields.Integer(
        metadata={"description": consecutive_count_description},
        allow_none=True,
        required=False,
        validate=[Range(min=1, error=_("Value must be greater than 0"))],
    )
    consecutive_direction = fields.String(
        metadata={"description": consecutive_direction_description},
        allow_none=True,
        required=False,
        validate=validate.OneOf(
            choices=[AnomalyDirection.INCREASE, AnomalyDirection.DECREASE]
        ),
    )
    time_granularity = fields.String(
        metadata={"description": time_granularity_description},
        allow_none=True,
        required=False,
    )
    status = fields.String(
        metadata={"description": status_description},
        allow_none=True,
        required=False,
        validate=validate.OneOf(
            choices=[
                AnomalyRuleStatus.ACTIVE,
                AnomalyRuleStatus.PAUSED,
                AnomalyRuleStatus.DISABLED,
            ]
        ),
    )

    notify_enabled = fields.Boolean(
        metadata={"description": notify_enabled_description},
        required=False,
    )
    notify_on_first_anomaly = fields.Boolean(
        metadata={"description": notify_on_first_anomaly_description},
        required=False,
    )
    notify_on_all_anomalies = fields.Boolean(
        metadata={"description": notify_on_all_anomalies_description},
        required=False,
    )
    notify_min_anomaly_count = fields.Integer(
        metadata={"description": notify_min_anomaly_count_description},
        required=False,
        validate=[Range(min=1, error=_("Value must be greater than 0"))],
    )
    notify_include_screenshot = fields.Boolean(
        metadata={"description": notify_include_screenshot_description},
        required=False,
    )
    notify_include_data = fields.Boolean(
        metadata={"description": notify_include_data_description},
        required=False,
    )

    schedule_config = fields.Nested(
        AnomalyScheduleConfigSchema,
        required=False,
        allow_none=True,
    )
    recipients = fields.List(
        fields.Nested(AnomalyRecipientSchema),
        required=False,
        allow_none=True,
    )

    owners = fields.List(
        fields.Integer(metadata={"description": owners_description}),
        required=False,
    )

    @validates_schema
    def validate_rule_config(
        self, data: dict[str, Any], **kwargs: Any
    ) -> None:
        rule_type = data.get("rule_type")
        exceptions: list[ValidationError] = []

        if rule_type == AnomalyRuleType.THRESHOLD:
            if data.get("threshold_min") is None and data.get("threshold_max") is None:
                exceptions.append(
                    ValidationError(
                        _("At least one of threshold_min or threshold_max is required for threshold rules"),
                        field_name="threshold_min",
                    )
                )

        elif rule_type == AnomalyRuleType.MOM:
            if data.get("mom_threshold") is None:
                exceptions.append(
                    ValidationError(
                        _("mom_threshold is required for MOM rules"),
                        field_name="mom_threshold",
                    )
                )

        elif rule_type == AnomalyRuleType.YOY:
            if data.get("yoy_threshold") is None:
                exceptions.append(
                    ValidationError(
                        _("yoy_threshold is required for YOY rules"),
                        field_name="yoy_threshold",
                    )
                )

        elif rule_type == AnomalyRuleType.PERIOD_OVER_PERIOD:
            if data.get("period_offset") is None and data.get("period_offset_count") is None:
                exceptions.append(
                    ValidationError(
                        _("period_offset or period_offset_count is required for period_over_period rules"),
                        field_name="period_offset",
                    )
                )

        elif rule_type == AnomalyRuleType.CONSECUTIVE:
            if data.get("consecutive_count") is None:
                exceptions.append(
                    ValidationError(
                        _("consecutive_count is required for consecutive rules"),
                        field_name="consecutive_count",
                    )
                )

        if exceptions:
            raise ValidationError(exceptions)

    @validates_schema
    def validate_chart_or_dashboard(
        self, data: dict[str, Any], **kwargs: Any
    ) -> None:
        chart_id = data.get("chart")
        dashboard_id = data.get("dashboard")

        if chart_id is None and dashboard_id is None:
            raise ValidationError(
                _("Either chart or dashboard must be specified"),
                field_name="chart",
            )


class AnomalyRulePutSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    name = fields.String(
        metadata={"description": name_description},
        allow_none=True,
        required=False,
        validate=[Length(1, 250)],
    )
    description = fields.String(
        metadata={"description": description_description},
        allow_none=True,
        required=False,
    )
    metric = fields.String(
        metadata={"description": metric_description},
        allow_none=True,
        required=False,
        validate=[Length(1, 255)],
    )
    metric_label = fields.String(
        metadata={"description": metric_label_description},
        allow_none=True,
        required=False,
    )
    rule_type = fields.String(
        metadata={"description": rule_type_description},
        allow_none=True,
        required=False,
        validate=validate.OneOf(
            choices=[
                AnomalyRuleType.THRESHOLD,
                AnomalyRuleType.MOM,
                AnomalyRuleType.YOY,
                AnomalyRuleType.PERIOD_OVER_PERIOD,
                AnomalyRuleType.CONSECUTIVE,
            ]
        ),
    )
    direction = fields.String(
        metadata={"description": direction_description},
        allow_none=True,
        required=False,
        validate=validate.OneOf(
            choices=[
                AnomalyDirection.INCREASE,
                AnomalyDirection.DECREASE,
                AnomalyDirection.BOTH,
            ]
        ),
    )

    threshold_min = fields.Float(
        metadata={"description": threshold_min_description},
        allow_none=True,
        required=False,
    )
    threshold_max = fields.Float(
        metadata={"description": threshold_max_description},
        allow_none=True,
        required=False,
    )
    mom_threshold = fields.Float(
        metadata={"description": mom_threshold_description},
        allow_none=True,
        required=False,
    )
    yoy_threshold = fields.Float(
        metadata={"description": yoy_threshold_description},
        allow_none=True,
        required=False,
    )
    period_offset = fields.String(
        metadata={"description": period_offset_description},
        allow_none=True,
        required=False,
    )
    period_offset_count = fields.Integer(
        metadata={"description": period_offset_count_description},
        allow_none=True,
        required=False,
        validate=[Range(min=1, error=_("Value must be greater than 0"))],
    )
    consecutive_count = fields.Integer(
        metadata={"description": consecutive_count_description},
        allow_none=True,
        required=False,
        validate=[Range(min=1, error=_("Value must be greater than 0"))],
    )
    consecutive_direction = fields.String(
        metadata={"description": consecutive_direction_description},
        allow_none=True,
        required=False,
        validate=validate.OneOf(
            choices=[AnomalyDirection.INCREASE, AnomalyDirection.DECREASE]
        ),
    )
    time_granularity = fields.String(
        metadata={"description": time_granularity_description},
        allow_none=True,
        required=False,
    )
    status = fields.String(
        metadata={"description": status_description},
        allow_none=True,
        required=False,
        validate=validate.OneOf(
            choices=[
                AnomalyRuleStatus.ACTIVE,
                AnomalyRuleStatus.PAUSED,
                AnomalyRuleStatus.DISABLED,
            ]
        ),
    )

    notify_enabled = fields.Boolean(
        metadata={"description": notify_enabled_description},
        required=False,
    )
    notify_on_first_anomaly = fields.Boolean(
        metadata={"description": notify_on_first_anomaly_description},
        required=False,
    )
    notify_on_all_anomalies = fields.Boolean(
        metadata={"description": notify_on_all_anomalies_description},
        required=False,
    )
    notify_min_anomaly_count = fields.Integer(
        metadata={"description": notify_min_anomaly_count_description},
        required=False,
        validate=[Range(min=1, error=_("Value must be greater than 0"))],
    )
    notify_include_screenshot = fields.Boolean(
        metadata={"description": notify_include_screenshot_description},
        required=False,
    )
    notify_include_data = fields.Boolean(
        metadata={"description": notify_include_data_description},
        required=False,
    )

    schedule_config = fields.Nested(
        AnomalyScheduleConfigSchema,
        required=False,
        allow_none=True,
    )
    recipients = fields.List(
        fields.Nested(AnomalyRecipientSchema),
        required=False,
        allow_none=True,
    )

    owners = fields.List(
        fields.Integer(metadata={"description": owners_description}),
        required=False,
    )
