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
import { SupersetClient, JsonResponse } from '@superset-ui/core';
import rison from 'rison';
import type {
  AnomalyRule,
  AnomalyRuleRequest,
  AnomalyRuleListResponse,
} from './types';

const API_PREFIX = '/api/v1/anomaly-rule';

export const getAnomalyRules = async (
  chartId?: number,
  dashboardId?: number,
  status?: string,
): Promise<AnomalyRuleListResponse> => {
  const query_params: Record<string, unknown> = {};

  if (chartId) {
    query_params.filters = [
      {
        col: 'chart_id',
        opr: 'eq',
        value: chartId,
      },
    ];
  }

  if (dashboardId) {
    const existingFilters = query_params.filters
      ? [...(query_params.filters as Array<Record<string, unknown>>)]
      : [];
    query_params.filters = [
      ...existingFilters,
      {
        col: 'dashboard_id',
        opr: 'eq',
        value: dashboardId,
      },
    ];
  }

  if (status) {
    const existingFilters = query_params.filters
      ? [...(query_params.filters as Array<Record<string, unknown>>)]
      : [];
    query_params.filters = [
      ...existingFilters,
      {
        col: 'status',
        opr: 'eq',
        value: status,
      },
    ];
  }

  const response: JsonResponse = await SupersetClient.get({
    endpoint: `${API_PREFIX}/?q=${rison.encode(query_params)}`,
  });

  return response.json as AnomalyRuleListResponse;
};

export const getAnomalyRule = async (id: number): Promise<AnomalyRule> => {
  const response: JsonResponse = await SupersetClient.get({
    endpoint: `${API_PREFIX}/${id}`,
  });

  return (response.json as { result: AnomalyRule }).result;
};

export const createAnomalyRule = async (
  data: AnomalyRuleRequest,
): Promise<AnomalyRule> => {
  const response: JsonResponse = await SupersetClient.post({
    endpoint: API_PREFIX,
    jsonPayload: data,
  });

  return (response.json as { id: number }).id as unknown as AnomalyRule;
};

export const updateAnomalyRule = async (
  id: number,
  data: Partial<AnomalyRuleRequest>,
): Promise<void> => {
  await SupersetClient.put({
    endpoint: `${API_PREFIX}/${id}`,
    jsonPayload: data,
  });
};

export const deleteAnomalyRule = async (id: number): Promise<void> => {
  await SupersetClient.delete({
    endpoint: `${API_PREFIX}/${id}`,
  });
};

export const bulkDeleteAnomalyRules = async (ids: number[]): Promise<void> => {
  await SupersetClient.delete({
    endpoint: API_PREFIX,
    jsonPayload: { ids },
  });
};
