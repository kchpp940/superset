/**
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 *
 *   http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 */

export enum AnomalyRuleType {
  Threshold = 'threshold',
  MOM = 'mom',
  YOY = 'yoy',
  PeriodOverPeriod = 'period_over_period',
  Consecutive = 'consecutive',
}

export enum AnomalyDirection {
  Increase = 'increase',
  Decrease = 'decrease',
  Both = 'both',
}

export enum AnomalyRuleStatus {
  Active = 'active',
  Inactive = 'inactive',
  Disabled = 'disabled',
}

export interface ThresholdRuleConfig {
  threshold_min?: number;
  threshold_max?: number;
}

export interface ChangeRuleConfig {
  change_percent: number;
  change_absolute?: number;
  direction: AnomalyDirection;
}

export interface PeriodOverPeriodRuleConfig extends ChangeRuleConfig {
  period_offset: number;
}

export interface ConsecutiveRuleConfig {
  consecutive_count: number;
  direction: AnomalyDirection;
}

export type AnomalyRuleConfig =
  | ThresholdRuleConfig
  | ChangeRuleConfig
  | PeriodOverPeriodRuleConfig
  | ConsecutiveRuleConfig;

export interface AnomalyRule {
  id: number;
  name: string;
  description?: string;
  chart_id: number;
  dashboard_id?: number;
  metric: string;
  rule_type: AnomalyRuleType;
  rule_config: AnomalyRuleConfig;
  status: AnomalyRuleStatus;
  owners: number[];
  created_by?: { id: number; username: string; first_name: string; last_name: string };
  last_anomaly_at?: string;
  last_anomaly_value?: number;
  last_anomaly_message?: string;
  created_on: string;
  changed_on: string;
  changed_by?: { id: number; username: string; first_name: string; last_name: string };
}

export interface AnomalyResult {
  is_anomaly: boolean;
  row_index?: number;
  current_value?: number;
  previous_value?: number;
  reference_value?: number;
  change_percent?: number;
  change_absolute?: number;
  threshold?: number;
  threshold_min?: number;
  threshold_max?: number;
  direction?: AnomalyDirection;
  anomaly_type?: string;
  message?: string;
}

export interface AnomalySummary {
  total_count: number;
  anomaly_count: number;
  increase_count: number;
  decrease_count: number;
  last_anomaly_value?: number;
  last_anomaly_at?: string;
}

export interface AnomalyDetectionResult {
  rule_id: number;
  metric: string;
  rule_type: AnomalyRuleType;
  is_anomaly: boolean;
  results: AnomalyResult[];
  summary: AnomalySummary;
}

export interface AnomalyDetection {
  has_anomaly_rules: boolean;
  has_anomalies?: boolean;
  anomaly_results?: Array<{
    rule_id: number;
    rule_name: string;
    metric: string;
    rule_type: AnomalyRuleType;
    is_anomaly: boolean;
    results: AnomalyResult[];
    summary: AnomalySummary;
  }>;
}

export interface AnomalyRuleRequest {
  name: string;
  description?: string;
  chart_id: number;
  dashboard_id?: number;
  metric: string;
  rule_type: AnomalyRuleType;
  rule_config: AnomalyRuleConfig;
  status: AnomalyRuleStatus;
  owners?: number[];
}

export interface AnomalyRuleListResponse {
  count: number;
  ids: number[];
  result: AnomalyRule[];
}
