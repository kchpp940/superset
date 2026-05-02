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
from functools import partial
from typing import Any, Optional

from marshmallow import ValidationError

from superset import security_manager
from superset.anomalies.models import AnomalyRule, AnomalyRuleType
from superset.commands.base import BaseCommand, UpdateMixin
from superset.commands.anomaly.exceptions import (
    AnomalyRuleForbiddenError,
    AnomalyRuleInvalidError,
    AnomalyRuleNotFoundError,
    AnomalyRuleUpdateFailedError,
    ChartNotFoundValidationError,
    DashboardNotFoundValidationError,
)
from superset.daos.anomaly import AnomalyRuleDAO
from superset.daos.chart import ChartDAO
from superset.daos.dashboard import DashboardDAO
from superset.exceptions import SupersetSecurityException
from superset.utils import json
from superset.utils.decorators import on_error, transaction

logger = logging.getLogger(__name__)


class UpdateAnomalyRuleCommand(UpdateMixin, BaseCommand):
    def __init__(self, model_id: int, data: dict[str, Any]):
        self._model_id = model_id
        self._properties = data.copy()
        self._model: Optional[AnomalyRule] = None

    @transaction(on_error=partial(on_error, reraise=AnomalyRuleUpdateFailedError))
    def run(self) -> AnomalyRule:
        self.validate()
        return AnomalyRuleDAO.update(self._model, self._properties)

    def validate(self) -> None:
        """
        Validates the properties of an anomaly rule configuration for update.
        """
        exceptions: list[ValidationError] = []

        self._model = AnomalyRuleDAO.find_by_id(self._model_id)
        if not self._model:
            raise AnomalyRuleNotFoundError()

        try:
            security_manager.raise_for_ownership(self._model)
        except SupersetSecurityException as ex:
            raise AnomalyRuleForbiddenError() from ex

        chart_id = self._properties.get("chart")
        dashboard_id = self._properties.get("dashboard")
        owner_ids: Optional[list[int]] = self._properties.get("owners")
        rule_type = self._properties.get("rule_type", self._model.rule_type)

        if chart_id:
            chart = ChartDAO.find_by_id(chart_id)
            if not chart:
                exceptions.append(ChartNotFoundValidationError())
            else:
                self._properties["chart"] = chart
        elif dashboard_id:
            dashboard = DashboardDAO.find_by_id(dashboard_id)
            if not dashboard:
                exceptions.append(DashboardNotFoundValidationError())
            else:
                self._properties["dashboard"] = dashboard

        if "schedule_config" in self._properties:
            schedule_config = self._properties.pop("schedule_config", {})
            if schedule_config:
                existing_extra = json.loads(self._model.extra_json or "{}")
                existing_extra["schedule_config"] = schedule_config
                self._properties["extra_json"] = json.dumps(existing_extra)

        if "recipients" in self._properties:
            recipients = self._properties.pop("recipients", [])
            if recipients is not None:
                existing_extra = json.loads(
                    self._properties.get("extra_json", self._model.extra_json or "{}")
                )
                existing_extra["recipients"] = recipients
                self._properties["extra_json"] = json.dumps(existing_extra)

        self._validate_rule_type_config(rule_type, exceptions)

        try:
            owners = self.compute_owners(self._model.owners, owner_ids)
            self._properties["owners"] = owners
        except ValidationError as ex:
            exceptions.append(ex)

        if exceptions:
            raise AnomalyRuleInvalidError(exceptions=exceptions)

    def _validate_rule_type_config(
        self, rule_type: str, exceptions: list[ValidationError]
    ) -> None:
        from marshmallow import ValidationError as MarshmallowValidationError
        from flask_babel import gettext as _

        if rule_type == AnomalyRuleType.THRESHOLD:
            threshold_min = self._properties.get(
                "threshold_min", self._model.threshold_min if self._model else None
            )
            threshold_max = self._properties.get(
                "threshold_max", self._model.threshold_max if self._model else None
            )
            if threshold_min is None and threshold_max is None:
                exceptions.append(
                    MarshmallowValidationError(
                        _(
                            "At least one of threshold_min or threshold_max is required for threshold rules"
                        ),
                        field_name="threshold_min",
                    )
                )

        elif rule_type == AnomalyRuleType.MOM:
            mom_threshold = self._properties.get(
                "mom_threshold", self._model.mom_threshold if self._model else None
            )
            if mom_threshold is None:
                exceptions.append(
                    MarshmallowValidationError(
                        _("mom_threshold is required for MOM rules"),
                        field_name="mom_threshold",
                    )
                )

        elif rule_type == AnomalyRuleType.YOY:
            yoy_threshold = self._properties.get(
                "yoy_threshold", self._model.yoy_threshold if self._model else None
            )
            if yoy_threshold is None:
                exceptions.append(
                    MarshmallowValidationError(
                        _("yoy_threshold is required for YOY rules"),
                        field_name="yoy_threshold",
                    )
                )

        elif rule_type == AnomalyRuleType.PERIOD_OVER_PERIOD:
            period_offset = self._properties.get(
                "period_offset",
                self._model.period_offset if self._model else None,
            )
            period_offset_count = self._properties.get(
                "period_offset_count",
                self._model.period_offset_count if self._model else None,
            )
            if period_offset is None and period_offset_count is None:
                exceptions.append(
                    MarshmallowValidationError(
                        _(
                            "period_offset or period_offset_count is required for period_over_period rules"
                        ),
                        field_name="period_offset",
                    )
                )

        elif rule_type == AnomalyRuleType.CONSECUTIVE:
            consecutive_count = self._properties.get(
                "consecutive_count",
                self._model.consecutive_count if self._model else None,
            )
            if consecutive_count is None:
                exceptions.append(
                    MarshmallowValidationError(
                        _("consecutive_count is required for consecutive rules"),
                        field_name="consecutive_count",
                    )
                )
