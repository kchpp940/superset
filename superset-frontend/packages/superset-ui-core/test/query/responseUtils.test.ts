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
import {
  getIsCached,
  getIsCachedFromQuery,
  getCachedDttm,
  getCachedDttmFromQuery,
  getQueriedDttm,
  getRowCount,
  getRowCountFromQueries,
  getCacheMetadata,
  hasCachedResult,
  getCacheKey,
  getCacheTimeout,
  getFirstQueryResponse,
  getSecondQueryResponse,
} from '@superset-ui/core';

const createMockQueryResponse = (overrides: Record<string, any> = {}) => ({
  is_cached: false,
  cached_dttm: '2024-01-15T10:00:00',
  queried_dttm: '2024-01-15T10:30:00',
  sql_rowcount: 100,
  rowcount: 100,
  cache_key: 'cache_key_123',
  cache_timeout: 3600,
  data: [{ col1: 'value1' }],
  ...overrides,
});

test('getIsCachedFromQuery returns is_cached value', () => {
  expect(getIsCachedFromQuery({ is_cached: true })).toBe(true);
  expect(getIsCachedFromQuery({ is_cached: false })).toBe(false);
  expect(getIsCachedFromQuery({})).toBe(false);
  expect(getIsCachedFromQuery(undefined)).toBe(false);
  expect(getIsCachedFromQuery(null)).toBe(false);
});

test('getIsCached extracts is_cached from all queries', () => {
  const queries = [
    createMockQueryResponse({ is_cached: true }),
    createMockQueryResponse({ is_cached: false }),
    createMockQueryResponse({ is_cached: true }),
  ];
  expect(getIsCached(queries)).toEqual([true, false, true]);
  expect(getIsCached([])).toEqual([]);
  expect(getIsCached(undefined)).toEqual([]);
  expect(getIsCached(null)).toEqual([]);
});

test('getCachedDttmFromQuery returns cached_dttm value', () => {
  expect(getCachedDttmFromQuery({ cached_dttm: '2024-01-15T10:00:00' })).toBe(
    '2024-01-15T10:00:00',
  );
  expect(getCachedDttmFromQuery({ cached_dttm: null })).toBe('');
  expect(getCachedDttmFromQuery({})).toBe('');
  expect(getCachedDttmFromQuery(undefined)).toBe('');
});

test('getCachedDttm extracts cached_dttm from all queries', () => {
  const queries = [
    createMockQueryResponse({ cached_dttm: '2024-01-15T10:00:00' }),
    createMockQueryResponse({ cached_dttm: '2024-01-15T11:00:00' }),
  ];
  expect(getCachedDttm(queries)).toEqual([
    '2024-01-15T10:00:00',
    '2024-01-15T11:00:00',
  ]);
  expect(getCachedDttm([])).toEqual([]);
  expect(getCachedDttm(undefined)).toEqual([]);
});

test('getQueriedDttm returns queried_dttm from last query', () => {
  const queries = [
    createMockQueryResponse({ queried_dttm: '2024-01-15T10:00:00' }),
    createMockQueryResponse({ queried_dttm: '2024-01-15T11:00:00' }),
  ];
  expect(getQueriedDttm(queries)).toBe('2024-01-15T11:00:00');
  expect(getQueriedDttm([])).toBe(null);
  expect(getQueriedDttm(undefined)).toBe(null);
  expect(getQueriedDttm(null)).toBe(null);
});

test('getFirstQueryResponse returns first element', () => {
  const queries = [
    createMockQueryResponse({ sql_rowcount: 100 }),
    createMockQueryResponse({ sql_rowcount: 200 }),
  ];
  expect(getFirstQueryResponse(queries)?.sql_rowcount).toBe(100);
  expect(getFirstQueryResponse([])).toBeUndefined();
  expect(getFirstQueryResponse(undefined)).toBeUndefined();
});

test('getSecondQueryResponse returns second element', () => {
  const queries = [
    createMockQueryResponse({ sql_rowcount: 100 }),
    createMockQueryResponse({ sql_rowcount: 200 }),
  ];
  expect(getSecondQueryResponse(queries)?.sql_rowcount).toBe(200);
  expect(getSecondQueryResponse([createMockQueryResponse()])).toBeUndefined();
  expect(getSecondQueryResponse([])).toBeUndefined();
});

test('getRowCountFromQueries returns rowcount from first query', () => {
  const first = createMockQueryResponse({ sql_rowcount: 100, rowcount: 50 });
  expect(getRowCountFromQueries(first, undefined, false)).toBe(100);

  const firstWithoutSql = createMockQueryResponse({
    sql_rowcount: undefined, rowcount: 50 });
  expect(getRowCountFromQueries(firstWithoutSql, undefined, false)).toBe(50);
});

test('getRowCountFromQueries returns rowcount from second query for table viz', () => {
  const first = createMockQueryResponse({ sql_rowcount: 10 });
  const second = createMockQueryResponse({
    data: [{ rowcount: 1000 }],
  });
  expect(getRowCountFromQueries(first, second, true)).toBe(1000);
  expect(getRowCountFromQueries(first, second, false)).toBe(10);
});

test('getRowCountFromQueries handles null/undefined responses', () => {
  expect(getRowCountFromQueries(undefined, undefined, false)).toBe(0);
  expect(getRowCountFromQueries(null, null, false)).toBe(0);
});

test('getRowCount returns rowcount from queries array', () => {
  const queries = [createMockQueryResponse({ sql_rowcount: 100 })];
  expect(getRowCount(queries, false)).toBe(100);
  expect(getRowCount([], false)).toBe(0);
  expect(getRowCount(undefined, false)).toBe(0);
  expect(getRowCount(null, false)).toBe(0);
});

test('getRowCount handles table viz with server pagination', () => {
  const queries = [
    createMockQueryResponse({ sql_rowcount: 10 }),
    createMockQueryResponse({ data: [{ rowcount: 500 }] }),
  ];
  expect(getRowCount(queries, true)).toBe(500);
  expect(getRowCount(queries, false)).toBe(10);
});

test('getCacheMetadata returns consolidated cache info', () => {
  const queries = [
    createMockQueryResponse({
      is_cached: true,
      cached_dttm: '2024-01-15T10:00:00',
      queried_dttm: '2024-01-15T10:30:00',
    }),
    createMockQueryResponse({
      is_cached: false,
      cached_dttm: '2024-01-15T11:00:00',
      queried_dttm: '2024-01-15T11:30:00',
    }),
  ];
  expect(getCacheMetadata(queries)).toEqual({
    isCached: [true, false],
    cachedDttm: ['2024-01-15T10:00:00', '2024-01-15T11:00:00'],
    queriedDttm: '2024-01-15T11:30:00',
  });
});

test('getCacheMetadata handles empty/null responses', () => {
  expect(getCacheMetadata([])).toEqual({
    isCached: [],
    cachedDttm: [],
    queriedDttm: null,
  });
  expect(getCacheMetadata(undefined)).toEqual({
    isCached: [],
    cachedDttm: [],
    queriedDttm: null,
  });
});

test('hasCachedResult returns true if any query is cached', () => {
  const cachedQueries = [
    createMockQueryResponse({ is_cached: false }),
    createMockQueryResponse({ is_cached: true }),
    createMockQueryResponse({ is_cached: false }),
  ];
  expect(hasCachedResult(cachedQueries)).toBe(true);

  const nonCachedQueries = [
    createMockQueryResponse({ is_cached: false }),
    createMockQueryResponse({ is_cached: false }),
  ];
  expect(hasCachedResult(nonCachedQueries)).toBe(false);
  expect(hasCachedResult([])).toBe(false);
  expect(hasCachedResult(undefined)).toBe(false);
  expect(hasCachedResult(null)).toBe(false);
});

test('getCacheKey returns cache_key from first query', () => {
  const queries = [
    createMockQueryResponse({ cache_key: 'cache_key_123' }),
    createMockQueryResponse({ cache_key: 'cache_key_456' }),
  ];
  expect(getCacheKey(queries)).toBe('cache_key_123');
  expect(getCacheKey([])).toBe(null);
  expect(getCacheKey(undefined)).toBe(null);
});

test('getCacheTimeout returns cache_timeout from first query', () => {
  const queries = [
    createMockQueryResponse({ cache_timeout: 3600 }),
    createMockQueryResponse({ cache_timeout: 7200 }),
  ];
  expect(getCacheTimeout(queries)).toBe(3600);
  expect(getCacheTimeout([])).toBe(null);
  expect(getCacheTimeout(undefined)).toBe(null);
});

test('getRowCount falls back to rowcount when sql_rowcount is missing', () => {
  const queries = [
    createMockQueryResponse({ sql_rowcount: undefined, rowcount: 50 }),
  ];
  expect(getRowCount(queries, false)).toBe(50);
});

test('getRowCount returns 0 when both sql_rowcount and rowcount are missing', () => {
  const queries = [
    createMockQueryResponse({ sql_rowcount: undefined, rowcount: undefined }),
  ];
  expect(getRowCount(queries, false)).toBe(0);
});

test('getRowCountFromQueries handles second query without rowcount data', () => {
  const first = createMockQueryResponse({ sql_rowcount: 100 });
  const second = createMockQueryResponse({ data: [] });
  expect(getRowCountFromQueries(first, second, true)).toBe(100);
});
