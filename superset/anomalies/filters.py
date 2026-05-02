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
from typing import Any

from flask_babel import lazy_gettext as _
from sqlalchemy import or_
from sqlalchemy.orm.query import Query

from superset import db, security_manager
from superset.anomalies.models import AnomalyRule
from superset.views.base import BaseFilter


class AnomalyRuleFilter(BaseFilter):
    """
    Base filter for anomaly rules.
    Filters rules to only show those owned by the current user
    unless the user can access all datasources.
    """

    def apply(self, query: Query, value: Any) -> Query:
        if security_manager.can_access_all_datasources():
            return query
        owner_ids_query = (
            db.session.query(AnomalyRule.id)
            .join(AnomalyRule.owners)
            .filter(
                security_manager.user_model.id
                == security_manager.user_model.get_user_id()
            )
        )
        return query.filter(AnomalyRule.id.in_(owner_ids_query))


class AnomalyRuleAllTextFilter(BaseFilter):
    """
    All text search filter for anomaly rules.
    """

    name = _("All Text")
    arg_name = "anomaly_rule_all_text"

    def apply(self, query: Query, value: Any) -> Query:
        if not value:
            return query
        ilike_value = f"%{value}%"
        return query.filter(
            or_(
                AnomalyRule.name.ilike(ilike_value),
                AnomalyRule.description.ilike(ilike_value),
                AnomalyRule.metric.ilike(ilike_value),
                AnomalyRule.metric_label.ilike(ilike_value),
            )
        )
