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

from flask import request, Response
from flask_appbuilder.api import expose, permission_name, protect, rison, safe
from flask_appbuilder.models.sqla.interface import SQLAInterface
from flask_babel import ngettext
from marshmallow import ValidationError

from superset.charts.filters import ChartFilter
from superset.commands.anomaly.create import CreateAnomalyRuleCommand
from superset.commands.anomaly.delete import DeleteAnomalyRuleCommand
from superset.commands.anomaly.exceptions import (
    AnomalyRuleCreateFailedError,
    AnomalyRuleDeleteFailedError,
    AnomalyRuleForbiddenError,
    AnomalyRuleInvalidError,
    AnomalyRuleNotFoundError,
    AnomalyRuleUpdateFailedError,
)
from superset.commands.anomaly.update import UpdateAnomalyRuleCommand
from superset.constants import MODEL_API_RW_METHOD_PERMISSION_MAP, RouteMethod
from superset.dashboards.filters import DashboardAccessFilter
from superset.daos.anomaly import AnomalyRuleDAO
from superset.extensions import event_logger
from superset.anomalies.filters import AnomalyRuleAllTextFilter, AnomalyRuleFilter
from superset.anomalies.models import AnomalyRule
from superset.anomalies.schemas import (
    AnomalyRulePostSchema,
    AnomalyRulePutSchema,
    get_delete_ids_schema,
    openapi_spec_methods_override,
)
from superset.views.base_api import (
    BaseSupersetModelRestApi,
    RelatedFieldFilter,
    requires_json,
    statsd_metrics,
)
from superset.views.filters import BaseFilterRelatedUsers, FilterRelatedOwners

logger = logging.getLogger(__name__)


class AnomalyRuleRestApi(BaseSupersetModelRestApi):
    datamodel = SQLAInterface(AnomalyRule)

    include_route_methods = RouteMethod.REST_MODEL_VIEW_CRUD_SET | {
        RouteMethod.RELATED,
        "bulk_delete",
    }
    class_permission_name = "AnomalyRule"
    method_permission_name = MODEL_API_RW_METHOD_PERMISSION_MAP
    resource_name = "anomaly-rule"
    allow_browser_login = True

    extra_fields_rel_fields = {
        **BaseSupersetModelRestApi.extra_fields_rel_fields,
        "created_by": ["email", "active"],
    }

    base_filters = [
        ["id", AnomalyRuleFilter, lambda: []],
    ]

    show_columns = [
        "id",
        "uuid",
        "name",
        "description",
        "chart.id",
        "chart.slice_name",
        "chart.viz_type",
        "dashboard.id",
        "dashboard.dashboard_title",
        "metric",
        "metric_label",
        "rule_type",
        "direction",
        "threshold_min",
        "threshold_max",
        "mom_threshold",
        "yoy_threshold",
        "period_offset",
        "period_offset_count",
        "consecutive_count",
        "consecutive_direction",
        "time_granularity",
        "status",
        "last_anomaly_dttm",
        "last_anomaly_value",
        "last_anomaly_message",
        "notify_enabled",
        "notify_on_first_anomaly",
        "notify_on_all_anomalies",
        "notify_min_anomaly_count",
        "notify_include_screenshot",
        "notify_include_data",
        "owners.first_name",
        "owners.id",
        "owners.last_name",
        "owners.email",
        "created_by.first_name",
        "created_by.last_name",
        "created_by.id",
        "changed_by.first_name",
        "changed_by.last_name",
        "changed_by.id",
        "created_on",
        "changed_on",
        "extra_json",
    ]
    list_columns = [
        "id",
        "uuid",
        "name",
        "description",
        "chart_id",
        "dashboard_id",
        "metric",
        "metric_label",
        "rule_type",
        "direction",
        "status",
        "notify_enabled",
        "last_anomaly_dttm",
        "last_anomaly_value",
        "created_by.first_name",
        "created_by.last_name",
        "created_on",
        "changed_by.first_name",
        "changed_by.last_name",
        "changed_on",
    ]
    add_columns = [
        "name",
        "description",
        "chart",
        "dashboard",
        "metric",
        "metric_label",
        "rule_type",
        "direction",
        "threshold_min",
        "threshold_max",
        "mom_threshold",
        "yoy_threshold",
        "period_offset",
        "period_offset_count",
        "consecutive_count",
        "consecutive_direction",
        "time_granularity",
        "status",
        "notify_enabled",
        "notify_on_first_anomaly",
        "notify_on_all_anomalies",
        "notify_min_anomaly_count",
        "notify_include_screenshot",
        "notify_include_data",
        "owners",
        "schedule_config",
        "recipients",
    ]
    edit_columns = add_columns
    add_model_schema = AnomalyRulePostSchema()
    edit_model_schema = AnomalyRulePutSchema()

    order_columns = [
        "name",
        "created_on",
        "changed_on",
        "last_anomaly_dttm",
        "status",
    ]
    search_columns = [
        "name",
        "metric",
        "rule_type",
        "status",
        "chart_id",
        "dashboard_id",
        "notify_enabled",
        "owners",
        "created_by",
        "changed_by",
    ]
    search_filters = {"name": [AnomalyRuleAllTextFilter]}
    allowed_rel_fields = {
        "owners",
        "chart",
        "dashboard",
        "created_by",
        "changed_by",
    }

    base_related_field_filters = {
        "chart": [["id", ChartFilter, lambda: []]],
        "dashboard": [["id", DashboardAccessFilter, lambda: []]],
        "owners": [["id", BaseFilterRelatedUsers, lambda: []]],
        "created_by": [["id", BaseFilterRelatedUsers, lambda: []]],
        "changed_by": [["id", BaseFilterRelatedUsers, lambda: []]],
    }
    text_field_rel_fields = {
        "dashboard": "dashboard_title",
        "chart": "slice_name",
    }
    related_field_filters = {
        "dashboard": "dashboard_title",
        "chart": "slice_name",
        "created_by": RelatedFieldFilter("first_name", FilterRelatedOwners),
        "changed_by": RelatedFieldFilter("first_name", FilterRelatedOwners),
        "owners": RelatedFieldFilter("first_name", FilterRelatedOwners),
    }

    apispec_parameter_schemas = {
        "get_delete_ids_schema": get_delete_ids_schema,
    }
    openapi_spec_tag = "Anomaly Rules"
    openapi_spec_methods = openapi_spec_methods_override

    @expose("/<int:pk>", methods=("DELETE",))
    @protect()
    @safe
    @permission_name("delete")
    @statsd_metrics
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.delete",
        log_to_statsd=False,
    )
    def delete(self, pk: int) -> Response:
        """Delete an anomaly rule.
        ---
        delete:
          summary: Delete an anomaly rule
          parameters:
          - in: path
            schema:
              type: integer
            name: pk
            description: The anomaly rule pk
          responses:
            200:
              description: Item deleted
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
            403:
              $ref: '#/components/responses/403'
            404:
              $ref: '#/components/responses/404'
            422:
              $ref: '#/components/responses/422'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            DeleteAnomalyRuleCommand([pk]).run()
            return self.response(200, message="OK")
        except AnomalyRuleNotFoundError:
            return self.response_404()
        except AnomalyRuleForbiddenError:
            return self.response_403()
        except AnomalyRuleDeleteFailedError as ex:
            logger.error(
                "Error deleting anomaly rule %s: %s",
                self.__class__.__name__,
                str(ex),
                exc_info=True,
            )
            return self.response_422(message=str(ex))

    @expose("/", methods=("POST",))
    @protect()
    @statsd_metrics
    @permission_name("post")
    @requires_json
    def post(
        self,
    ) -> Response:
        """Create a new anomaly rule.
        ---
        post:
          summary: Create a new anomaly rule
          requestBody:
            description: Anomaly Rule schema
            required: true
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/{{self.__class__.__name__}}.post'
          responses:
            201:
              description: Anomaly rule added
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      id:
                        type: number
                      result:
                        $ref: '#/components/schemas/{{self.__class__.__name__}}.post'
            400:
              $ref: '#/components/responses/400'
            401:
              $ref: '#/components/responses/401'
            404:
              $ref: '#/components/responses/404'
            422:
              $ref: '#/components/responses/422'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            item = self.add_model_schema.load(request.json)
            event_logger.log_with_context(
                action="AnomalyRuleRestApi.post",
                dashboard_id=request.json.get("dashboard", None),
                chart_id=request.json.get("chart", None),
                rule_type=request.json.get("rule_type", None),
                metric=request.json.get("metric", None),
            )
        except ValidationError as error:
            return self.response_400(message=error.messages)
        try:
            new_model = CreateAnomalyRuleCommand(item).run()
            return self.response(201, id=new_model.id, result=item)
        except AnomalyRuleNotFoundError as ex:
            return self.response_400(message=str(ex))
        except AnomalyRuleInvalidError as ex:
            return self.response_422(message=ex.normalized_messages())
        except AnomalyRuleCreateFailedError as ex:
            logger.error(
                "Error creating anomaly rule %s: %s",
                self.__class__.__name__,
                str(ex),
                exc_info=True,
            )
            return self.response_422(message=str(ex))

    @expose("/<int:pk>", methods=("PUT",))
    @protect()
    @safe
    @statsd_metrics
    @permission_name("put")
    @requires_json
    def put(self, pk: int) -> Response:
        """Update an anomaly rule.
        ---
        put:
          summary: Update an anomaly rule
          parameters:
          - in: path
            schema:
              type: integer
            name: pk
            description: The Anomaly Rule pk
          requestBody:
            description: Anomaly Rule schema
            required: true
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/{{self.__class__.__name__}}.put'
          responses:
            200:
              description: Anomaly Rule changed
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      id:
                        type: number
                      result:
                        $ref: '#/components/schemas/{{self.__class__.__name__}}.put'
            400:
              $ref: '#/components/responses/400'
            401:
              $ref: '#/components/responses/401'
            403:
              $ref: '#/components/responses/403'
            404:
              $ref: '#/components/responses/404'
            422:
              $ref: '#/components/responses/422'
            500:
              $ref: '#/components/responses/500'
        """
        try:
            item = self.edit_model_schema.load(request.json)
            event_logger.log_with_context(
                action="AnomalyRuleRestApi.put",
                dashboard_id=request.json.get("dashboard", None),
                chart_id=request.json.get("chart", None),
                rule_type=request.json.get("rule_type", None),
                metric=request.json.get("metric", None),
            )
        except ValidationError as error:
            return self.response_400(message=error.messages)
        try:
            new_model = UpdateAnomalyRuleCommand(pk, item).run()
            return self.response(200, id=new_model.id, result=item)
        except AnomalyRuleNotFoundError:
            return self.response_404()
        except AnomalyRuleInvalidError as ex:
            return self.response_422(message=ex.normalized_messages())
        except AnomalyRuleForbiddenError:
            return self.response_403()
        except AnomalyRuleUpdateFailedError as ex:
            logger.error(
                "Error updating anomaly rule %s: %s",
                self.__class__.__name__,
                str(ex),
                exc_info=True,
            )
            return self.response_422(message=str(ex))

    @expose("/", methods=("DELETE",))
    @protect()
    @safe
    @statsd_metrics
    @rison(get_delete_ids_schema)
    @event_logger.log_this_with_context(
        action=lambda self, *args, **kwargs: f"{self.__class__.__name__}.bulk_delete",
        log_to_statsd=False,
    )
    def bulk_delete(self, **kwargs: Any) -> Response:
        """Bulk delete anomaly rules.
        ---
        delete:
          summary: Bulk delete anomaly rules
          parameters:
          - in: query
            name: q
            content:
              application/json:
                schema:
                  $ref: '#/components/schemas/get_delete_ids_schema'
          responses:
            200:
              description: Anomaly Rule bulk delete
              content:
                application/json:
                  schema:
                    type: object
                    properties:
                      message:
                        type: string
            401:
              $ref: '#/components/responses/401'
            403:
              $ref: '#/components/responses/403'
            404:
              $ref: '#/components/responses/404'
            422:
              $ref: '#/components/responses/422'
            500:
              $ref: '#/components/responses/500'
        """
        item_ids = kwargs["rison"]
        try:
            DeleteAnomalyRuleCommand(item_ids).run()
            return self.response(
                200,
                message=ngettext(
                    "Deleted %(num)d anomaly rule",
                    "Deleted %(num)d anomaly rules",
                    num=len(item_ids),
                ),
            )
        except AnomalyRuleNotFoundError:
            return self.response_404()
        except AnomalyRuleForbiddenError:
            return self.response_403()
        except AnomalyRuleDeleteFailedError as ex:
            return self.response_422(message=str(ex))
