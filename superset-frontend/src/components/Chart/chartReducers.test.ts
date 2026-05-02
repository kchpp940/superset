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
import { JsonObject } from '@superset-ui/core';
import chartReducer, { chart } from 'src/components/Chart/chartReducer';
import * as actions from 'src/components/Chart/chartAction';
import { ChartState } from 'src/explore/types';

// eslint-disable-next-line no-restricted-globals -- TODO: Migrate from describe blocks
describe('chart reducers', () => {
  const chartKey = 1;
  let testChart: ChartState;
  let charts: Record<number, ChartState>;
  beforeEach(() => {
    testChart = {
      ...chart,
      id: chartKey,
    };
    charts = { [chartKey]: testChart };
  });

  test('should update endtime on fail', () => {
    const newState = chartReducer(charts, actions.chartUpdateStopped(chartKey));
    expect(newState[chartKey].chartUpdateEndTime).toBeGreaterThan(0);
    expect(newState[chartKey].chartStatus).toEqual('stopped');
  });

  test('should handle chartUpdateStopped without queryController', () => {
    const newState = chartReducer(charts, actions.chartUpdateStopped(chartKey));
    expect(newState[chartKey].chartStatus).toEqual('stopped');
    expect(newState[chartKey].chartAlert).toContain(
      'Updating chart was stopped',
    );
    expect(newState[chartKey].chartUpdateEndTime).toBeGreaterThan(0);
  });

  test('chartUpdateStopped sets state correctly', () => {
    const chartsWithController = {
      [chartKey]: {
        ...testChart,
        queryController: new AbortController(),
      },
    };
    const newState = chartReducer(
      chartsWithController,
      actions.chartUpdateStopped(chartKey),
    );
    // Verify the chart status and alert are set
    expect(newState[chartKey].chartStatus).toEqual('stopped');
    expect(newState[chartKey].chartAlert).toContain(
      'Updating chart was stopped',
    );
  });

  test('should update endtime on timeout', () => {
    const newState = chartReducer(
      charts,
      actions.chartUpdateFailed(
        [
          {
            statusText: 'timeout',
            error: 'Request timed out',
            errors: [
              {
                error_type: 'FRONTEND_TIMEOUT_ERROR',
                extra: { timeout: 1 },
                level: 'error',
                message: 'Request timed out',
              },
            ],
          } as JsonObject,
        ],
        chartKey,
      ),
    );
    expect(newState[chartKey].chartUpdateEndTime).toBeGreaterThan(0);
    expect(newState[chartKey].chartStatus).toEqual('failed');
  });

  test('should preserve queriesResponse structure on CHART_UPDATE_SUCCEEDED', () => {
    const mockQueriesResponse = [
      {
        cache_key: 'test-cache-key-123',
        cache_timeout: 3600,
        cached_dttm: '2024-01-15T10:00:00',
        queried_dttm: '2024-01-15T10:30:00',
        rowcount: 100,
        sql_rowcount: 100,
        query: 'SELECT * FROM test_table',
        status: 'success',
        is_cached: true,
        data: [{ col1: 'value1', col2: 'value2' }],
        colnames: ['col1', 'col2'],
        coltypes: [1, 2],
        error: null,
        stacktrace: null,
      },
    ];

    const newState = chartReducer(
      charts,
      actions.chartUpdateSucceeded(mockQueriesResponse, chartKey),
    );

    expect(newState[chartKey].chartStatus).toEqual('success');
    expect(newState[chartKey].queriesResponse).not.toBeNull();
    expect(newState[chartKey].queriesResponse).toHaveLength(1);

    const response = newState[chartKey].queriesResponse![0];
    expect(response.cache_key).toEqual('test-cache-key-123');
    expect(response.is_cached).toEqual(true);
    expect(response.cached_dttm).toEqual('2024-01-15T10:00:00');
    expect(response.queried_dttm).toEqual('2024-01-15T10:30:00');
    expect(response.rowcount).toEqual(100);
    expect(response.sql_rowcount).toEqual(100);
    expect(response.query).toEqual('SELECT * FROM test_table');
    expect(response.status).toEqual('success');
    expect(response.data).toEqual([{ col1: 'value1', col2: 'value2' }]);
  });

  test('should preserve cache metadata fields when is_cached is true', () => {
    const cachedQueryResponse = [
      {
        cache_key: 'cached-result-key',
        cached_dttm: '2024-01-20T09:00:00',
        queried_dttm: '2024-01-20T09:00:00',
        is_cached: true,
        rowcount: 50,
        sql_rowcount: 50,
        data: [{ metric: 100 }],
        status: 'success',
      },
    ];

    const newState = chartReducer(
      charts,
      actions.chartUpdateSucceeded(cachedQueryResponse, chartKey),
    );

    const response = newState[chartKey].queriesResponse![0];
    expect(response.is_cached).toEqual(true);
    expect(response.cache_key).toEqual('cached-result-key');
    expect(response.cached_dttm).toEqual('2024-01-20T09:00:00');
    expect(response.queried_dttm).toEqual('2024-01-20T09:00:00');
    expect(response.rowcount).toEqual(50);
  });

  test('should handle non-cached result with null cache fields', () => {
    const nonCachedResponse = [
      {
        cache_key: null,
        cached_dttm: null,
        queried_dttm: '2024-01-20T10:30:00',
        is_cached: false,
        rowcount: 25,
        sql_rowcount: 25,
        data: [{ id: 1 }, { id: 2 }],
        status: 'success',
      },
    ];

    const newState = chartReducer(
      charts,
      actions.chartUpdateSucceeded(nonCachedResponse, chartKey),
    );

    const response = newState[chartKey].queriesResponse![0];
    expect(response.is_cached).toEqual(false);
    expect(response.cache_key).toBeNull();
    expect(response.cached_dttm).toBeNull();
    expect(response.queried_dttm).toEqual('2024-01-20T10:30:00');
    expect(response.rowcount).toEqual(25);
    expect(response.data).toEqual([{ id: 1 }, { id: 2 }]);
  });

  test('should preserve multiple queries response structure', () => {
    const multiQueryResponse = [
      {
        cache_key: 'query-1-key',
        is_cached: true,
        cached_dttm: '2024-01-15T10:00:00',
        rowcount: 100,
        data: [{ col1: 'value1' }],
        status: 'success',
      },
      {
        cache_key: 'query-2-key',
        is_cached: false,
        cached_dttm: null,
        rowcount: 200,
        data: [{ col2: 'value2' }],
        status: 'success',
      },
    ];

    const newState = chartReducer(
      charts,
      actions.chartUpdateSucceeded(multiQueryResponse, chartKey),
    );

    expect(newState[chartKey].queriesResponse).toHaveLength(2);
    expect(newState[chartKey].queriesResponse![0].cache_key).toEqual(
      'query-1-key',
    );
    expect(newState[chartKey].queriesResponse![0].is_cached).toEqual(true);
    expect(newState[chartKey].queriesResponse![1].cache_key).toEqual(
      'query-2-key',
    );
    expect(newState[chartKey].queriesResponse![1].is_cached).toEqual(false);
  });

  test('should preserve queriesResponse on CHART_UPDATE_FAILED', () => {
    const errorResponse = [
      {
        error: 'Query failed',
        status: 'failed',
        rowcount: 0,
      },
    ];

    const newState = chartReducer(
      charts,
      actions.chartUpdateFailed(errorResponse, chartKey),
    );

    expect(newState[chartKey].chartStatus).toEqual('failed');
    expect(newState[chartKey].queriesResponse).not.toBeNull();
    expect(newState[chartKey].queriesResponse![0].error).toEqual(
      'Query failed',
    );
    expect(newState[chartKey].chartAlert).toEqual('Query failed');
  });
});
