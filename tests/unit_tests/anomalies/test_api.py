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
from unittest.mock import MagicMock, patch

import prison
import pytest


class TestAnomalyRuleListApi:
    """Test anomaly rule list API endpoints."""

    @patch("superset.daos.anomaly.AnomalyRuleDAO.find_by_chart_id")
    def test_list_rules_by_chart(
        self,
        mock_find_by_chart_id: MagicMock,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test listing anomaly rules by chart ID."""
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_rule.name = "Test Rule"
        mock_rule.chart_id = 123
        mock_rule.metric = "sales"
        mock_rule.rule_type = "threshold"
        mock_rule.status = "active"
        mock_rule.rule_config = {"threshold_max": 100}
        mock_rule.owners = []
        mock_rule.created_on = "2024-01-01T00:00:00"
        mock_rule.changed_on = "2024-01-01T00:00:00"

        mock_find_by_chart_id.return_value = [mock_rule]

        params = prison.dumps({
            "filters": [
                {"col": "chart_id", "opr": "eq", "value": 123}
            ]
        })

        rv = client.get(f"/api/v1/anomaly-rule/?q={params}")

        assert rv.status_code == 200


class TestAnomalyRuleCreateApi:
    """Test anomaly rule creation API."""

    @patch("superset.commands.anomaly.create.CreateAnomalyRuleCommand.run")
    def test_create_threshold_rule(
        self,
        mock_create: MagicMock,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test creating a threshold-based anomaly rule."""
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_create.return_value = mock_rule

        data = {
            "name": "Sales Spike Alert",
            "description": "Alert when sales exceed 1000",
            "chart_id": 123,
            "metric": "sales",
            "rule_type": "threshold",
            "rule_config": {
                "threshold_max": 1000,
                "threshold_min": 100,
            },
            "status": "active",
            "owners": [1],
        }

        rv = client.post(
            "/api/v1/anomaly-rule/",
            json=data,
        )

        assert rv.status_code == 200

    @patch("superset.commands.anomaly.create.CreateAnomalyRuleCommand.run")
    def test_create_mom_rule(
        self,
        mock_create: MagicMock,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test creating a MOM-based anomaly rule."""
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_create.return_value = mock_rule

        data = {
            "name": "MOM Spike Alert",
            "chart_id": 123,
            "metric": "sales",
            "rule_type": "mom",
            "rule_config": {
                "change_percent": 20,
                "direction": "increase",
            },
            "status": "active",
            "owners": [1],
        }

        rv = client.post(
            "/api/v1/anomaly-rule/",
            json=data,
        )

        assert rv.status_code == 200

    @patch("superset.commands.anomaly.create.CreateAnomalyRuleCommand.run")
    def test_create_consecutive_rule(
        self,
        mock_create: MagicMock,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test creating a consecutive-based anomaly rule."""
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_create.return_value = mock_rule

        data = {
            "name": "Consecutive Drop Alert",
            "chart_id": 123,
            "metric": "sales",
            "rule_type": "consecutive",
            "rule_config": {
                "consecutive_count": 3,
                "direction": "decrease",
            },
            "status": "active",
            "owners": [1],
        }

        rv = client.post(
            "/api/v1/anomaly-rule/",
            json=data,
        )

        assert rv.status_code == 200

    def test_create_invalid_rule_missing_required(
        self,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test creating a rule with missing required fields."""
        data = {
            "name": "Invalid Rule",
            "rule_type": "threshold",
            "status": "active",
        }

        rv = client.post(
            "/api/v1/anomaly-rule/",
            json=data,
        )

        assert rv.status_code == 422


class TestAnomalyRuleUpdateApi:
    """Test anomaly rule update API."""

    @patch("superset.daos.anomaly.AnomalyRuleDAO.update")
    @patch("superset.commands.anomaly.update.UpdateAnomalyRuleCommand.run")
    @patch("superset.daos.anomaly.AnomalyRuleDAO.find_by_id")
    def test_update_rule(
        self,
        mock_find_by_id: MagicMock,
        mock_update: MagicMock,
        mock_command_run: MagicMock,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test updating an anomaly rule."""
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_find_by_id.return_value = mock_rule
        mock_command_run.return_value = mock_rule

        data = {
            "name": "Updated Rule Name",
            "rule_config": {
                "threshold_max": 2000,
            },
        }

        rv = client.put(
            "/api/v1/anomaly-rule/1",
            json=data,
        )

        assert rv.status_code == 200


class TestAnomalyRuleDeleteApi:
    """Test anomaly rule deletion API."""

    @patch("superset.commands.anomaly.delete.DeleteAnomalyRuleCommand.run")
    @patch("superset.daos.anomaly.AnomalyRuleDAO.find_by_id")
    def test_delete_rule(
        self,
        mock_find_by_id: MagicMock,
        mock_delete: MagicMock,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test deleting an anomaly rule."""
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_find_by_id.return_value = mock_rule

        rv = client.delete("/api/v1/anomaly-rule/1")

        assert rv.status_code == 200

    @patch("superset.commands.anomaly.delete.DeleteAnomalyRuleCommand.run")
    def test_bulk_delete_rules(
        self,
        mock_delete: MagicMock,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test bulk deleting anomaly rules."""
        data = {"ids": [1, 2, 3]}

        rv = client.delete(
            "/api/v1/anomaly-rule/",
            json=data,
        )

        assert rv.status_code == 200


class TestAnomalyRuleValidation:
    """Test anomaly rule validation."""

    def test_threshold_validation_no_thresholds(
        self,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test validation error when no thresholds provided for threshold rule."""
        data = {
            "name": "Invalid Threshold Rule",
            "chart_id": 123,
            "metric": "sales",
            "rule_type": "threshold",
            "rule_config": {},
            "status": "active",
            "owners": [1],
        }

        rv = client.post(
            "/api/v1/anomaly-rule/",
            json=data,
        )

        assert rv.status_code == 422

    def test_mom_validation_missing_change_percent(
        self,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test validation error when change_percent is missing for MOM rule."""
        data = {
            "name": "Invalid MOM Rule",
            "chart_id": 123,
            "metric": "sales",
            "rule_type": "mom",
            "rule_config": {
                "direction": "increase",
            },
            "status": "active",
            "owners": [1],
        }

        rv = client.post(
            "/api/v1/anomaly-rule/",
            json=data,
        )

        assert rv.status_code == 422

    def test_consecutive_validation_missing_count(
        self,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test validation error when consecutive_count is missing."""
        data = {
            "name": "Invalid Consecutive Rule",
            "chart_id": 123,
            "metric": "sales",
            "rule_type": "consecutive",
            "rule_config": {
                "direction": "both",
            },
            "status": "active",
            "owners": [1],
        }

        rv = client.post(
            "/api/v1/anomaly-rule/",
            json=data,
        )

        assert rv.status_code == 422


class TestAnomalyRuleStatus:
    """Test anomaly rule status management."""

    @patch("superset.daos.anomaly.AnomalyRuleDAO.update")
    @patch("superset.commands.anomaly.update.UpdateAnomalyRuleCommand.run")
    @patch("superset.daos.anomaly.AnomalyRuleDAO.find_by_id")
    def test_deactivate_rule(
        self,
        mock_find_by_id: MagicMock,
        mock_update: MagicMock,
        mock_command_run: MagicMock,
        client: Any,
        full_api_access: None,
    ) -> None:
        """Test deactivating an anomaly rule."""
        mock_rule = MagicMock()
        mock_rule.id = 1
        mock_find_by_id.return_value = mock_rule
        mock_command_run.return_value = mock_rule

        data = {
            "status": "inactive",
        }

        rv = client.put(
            "/api/v1/anomaly-rule/1",
            json=data,
        )

        assert rv.status_code == 200
