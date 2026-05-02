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

from typing import Any, TypedDict


class AnomalyRuleType:
    THRESHOLD = "threshold"
    MOM = "mom"
    YOY = "yoy"
    PERIOD_OVER_PERIOD = "period_over_period"
    CONSECUTIVE = "consecutive"


class AnomalyDirection:
    INCREASE = "increase"
    DECREASE = "decrease"
    BOTH = "both"


class AnomalyRuleConfig(TypedDict, total=False):
    metric: str
    metric_label: str | None
    rule_type: str
    direction: str

    threshold_min: float | None
    threshold_max: float | None

    mom_threshold: float | None
    yoy_threshold: float | None
    period_offset: str | None
    period_offset_count: int | None

    consecutive_count: int | None
    consecutive_direction: str | None

    time_granularity: str | None

    description: str | None


class AnomalyResult(TypedDict, total=False):
    rule_id: int
    rule_uuid: str
    chart_id: int
    metric: str
    metric_label: str | None

    anomaly_type: str
    direction: str

    current_value: float | None
    previous_value: float | None
    reference_value: float | None

    change_percent: float | None
    change_absolute: float | None

    threshold: float | None
    threshold_min: float | None
    threshold_max: float | None

    is_anomaly: bool
    message: str | None

    row_index: int | None
    timestamp: str | None

    consecutive_count: int | None
    consecutive_values: list[float] | None


class AnomalyDetectionResult(TypedDict, total=False):
    rule_id: int
    chart_id: int
    metric: str
    is_anomaly: bool
    results: list[AnomalyResult]
    summary: AnomalySummary | None


class AnomalySummary(TypedDict, total=False):
    total_points: int
    anomaly_count: int
    first_anomaly_idx: int | None
    last_anomaly_idx: int | None
    max_deviation: float | None
    max_deviation_direction: str | None


class AnomalyNotificationConfig(TypedDict, total=False):
    enabled: bool
    notify_on_first_anomaly: bool
    notify_on_all_anomalies: bool
    min_anomaly_count: int
    include_chart_screenshot: bool
    include_data_table: bool
