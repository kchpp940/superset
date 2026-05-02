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
from unittest.mock import MagicMock

import pytest

from superset.anomalies.detector import anomaly_detector
from superset.anomalies.models import (
    AnomalyRule,
    AnomalyRuleType,
    AnomalyRuleStatus,
    AnomalyDirection,
)


class TestThresholdDetection:
    """Test threshold-based anomaly detection."""

    def test_threshold_max_breach(self) -> None:
        """Test detection when value exceeds max threshold."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_max": 100}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 90},
            {"__timestamp": "2024-01-02", "sales": 105},
            {"__timestamp": "2024-01-03", "sales": 95},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True
        assert result["rule_id"] == 1
        assert result["metric"] == "sales"
        assert len(result["results"]) == 3
        assert result["results"][1]["is_anomaly"] is True
        assert result["results"][1]["current_value"] == 105
        assert result["results"][1]["threshold_max"] == 100

    def test_threshold_min_breach(self) -> None:
        """Test detection when value is below min threshold."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_min": 50}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 60},
            {"__timestamp": "2024-01-02", "sales": 45},
            {"__timestamp": "2024-01-03", "sales": 55},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True
        assert result["results"][1]["is_anomaly"] is True
        assert result["results"][1]["threshold_min"] == 50

    def test_threshold_both_bounds(self) -> None:
        """Test detection with both min and max thresholds."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_min": 50, "threshold_max": 100}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 75},
            {"__timestamp": "2024-01-02", "sales": 45},
            {"__timestamp": "2024-01-03", "sales": 105},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True
        assert result["results"][1]["is_anomaly"] is True
        assert result["results"][2]["is_anomaly"] is True

    def test_threshold_no_breach(self) -> None:
        """Test when no threshold is breached."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_min": 50, "threshold_max": 100}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 75},
            {"__timestamp": "2024-01-02", "sales": 80},
            {"__timestamp": "2024-01-03", "sales": 60},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is False


class TestChangeDetection:
    """Test change-based anomaly detection (MOM, YOY)."""

    def test_mom_increase_breach(self) -> None:
        """Test MOM increase detection."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.MOM
        rule.rule_config = {
            "change_percent": 10,
            "direction": AnomalyDirection.INCREASE,
        }
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 100},
            {"__timestamp": "2024-02-01", "sales": 105},
            {"__timestamp": "2024-03-01", "sales": 120},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True
        assert result["results"][2]["is_anomaly"] is True
        assert result["results"][2]["change_percent"] == 14.29

    def test_mom_decrease_breach(self) -> None:
        """Test MOM decrease detection."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.MOM
        rule.rule_config = {
            "change_percent": 10,
            "direction": AnomalyDirection.DECREASE,
        }
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 100},
            {"__timestamp": "2024-02-01", "sales": 95},
            {"__timestamp": "2024-03-01", "sales": 80},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True
        assert result["results"][2]["is_anomaly"] is True

    def test_mom_both_directions(self) -> None:
        """Test MOM detection for both directions."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.MOM
        rule.rule_config = {
            "change_percent": 10,
            "direction": AnomalyDirection.BOTH,
        }
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 100},
            {"__timestamp": "2024-02-01", "sales": 120},
            {"__timestamp": "2024-03-01", "sales": 80},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True
        assert result["results"][1]["is_anomaly"] is True
        assert result["results"][2]["is_anomaly"] is True

    def test_absolute_change_breach(self) -> None:
        """Test detection using absolute change threshold."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.MOM
        rule.rule_config = {
            "change_percent": 100,
            "change_absolute": 50,
            "direction": AnomalyDirection.BOTH,
        }
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 100},
            {"__timestamp": "2024-02-01", "sales": 160},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True
        assert result["results"][1]["change_absolute"] == 60


class TestConsecutiveDetection:
    """Test consecutive change detection."""

    def test_consecutive_increase(self) -> None:
        """Test detection of consecutive increases."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.CONSECUTIVE
        rule.rule_config = {
            "consecutive_count": 3,
            "direction": AnomalyDirection.INCREASE,
        }
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 100},
            {"__timestamp": "2024-01-02", "sales": 110},
            {"__timestamp": "2024-01-03", "sales": 120},
            {"__timestamp": "2024-01-04", "sales": 130},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True

    def test_consecutive_decrease(self) -> None:
        """Test detection of consecutive decreases."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.CONSECUTIVE
        rule.rule_config = {
            "consecutive_count": 3,
            "direction": AnomalyDirection.DECREASE,
        }
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 100},
            {"__timestamp": "2024-01-02", "sales": 90},
            {"__timestamp": "2024-01-03", "sales": 80},
            {"__timestamp": "2024-01-04", "sales": 70},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True

    def test_consecutive_no_breach(self) -> None:
        """Test when consecutive count is not reached."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.CONSECUTIVE
        rule.rule_config = {
            "consecutive_count": 4,
            "direction": AnomalyDirection.INCREASE,
        }
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 100},
            {"__timestamp": "2024-01-02", "sales": 110},
            {"__timestamp": "2024-01-03", "sales": 105},
            {"__timestamp": "2024-01-04", "sales": 120},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is False


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_data(self) -> None:
        """Test detection with empty data."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_max": 100}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data: list[dict] = []

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is False
        assert result["results"] == []
        assert result["summary"]["total_count"] == 0
        assert result["summary"]["anomaly_count"] == 0

    def test_single_data_point(self) -> None:
        """Test detection with single data point."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.MOM
        rule.rule_config = {"change_percent": 10, "direction": AnomalyDirection.BOTH}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [{"__timestamp": "2024-01-01", "sales": 100}]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is False

    def test_inactive_rule(self) -> None:
        """Test that inactive rules don't trigger detection."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_max": 100}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.INACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 150},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is False

    def test_missing_metric_column(self) -> None:
        """Test detection when metric column is missing."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_max": 100}
        rule.metric = "nonexistent"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 150},
        ]

        result = anomaly_detector.detect(rule, data, "nonexistent", "__timestamp")

        assert result["is_anomaly"] is False

    def test_none_values(self) -> None:
        """Test detection with None/None values in data."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_max": 100}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": None},
            {"__timestamp": "2024-01-02", "sales": 150},
            {"__timestamp": "2024-01-03", "sales": 90},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["is_anomaly"] is True
        assert result["results"][0]["is_anomaly"] is False
        assert result["results"][1]["is_anomaly"] is True


class TestSummary:
    """Test anomaly detection summary."""

    def test_summary_calculation(self) -> None:
        """Test that summary is correctly calculated."""
        rule = MagicMock(spec=AnomalyRule)
        rule.id = 1
        rule.rule_type = AnomalyRuleType.THRESHOLD
        rule.rule_config = {"threshold_min": 50, "threshold_max": 100}
        rule.metric = "sales"
        rule.status = AnomalyRuleStatus.ACTIVE

        data = [
            {"__timestamp": "2024-01-01", "sales": 75},
            {"__timestamp": "2024-01-02", "sales": 45},
            {"__timestamp": "2024-01-03", "sales": 105},
            {"__timestamp": "2024-01-04", "sales": 80},
        ]

        result = anomaly_detector.detect(rule, data, "sales", "__timestamp")

        assert result["summary"]["total_count"] == 4
        assert result["summary"]["anomaly_count"] == 2
