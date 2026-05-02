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

/**
 * Interface representing the minimum shape of a query response
 * containing cache metadata. Used for type compatibility with
 * legacy QueryData type.
 */
export interface QueryCacheMetadata {
  is_cached?: boolean;
  cached_dttm?: string | null;
  queried_dttm?: string | null;
  cache_key?: string | null;
  cache_timeout?: number | null;
}

/**
 * Interface representing the minimum shape of a query response
 * containing row count information.
 */
export interface QueryRowCount {
  sql_rowcount?: number | null;
  rowcount?: number | null;
  data?: Array<{ rowcount?: number }>;
}

/**
 * Combined interface for a query response with all metadata.
 */
export type QueryResponseLike = QueryCacheMetadata & QueryRowCount;

/**
 * Extracts the `is_cached` value from a single query response.
 * Returns false if the value is not defined.
 */
export function getIsCachedFromQuery(
  query?: QueryCacheMetadata | null,
): boolean {
  return query?.is_cached ?? false;
}

/**
 * Extracts the `is_cached` values from an array of query responses.
 * Returns an empty array if queriesResponse is null/undefined.
 */
export function getIsCached(
  queriesResponse?: QueryResponseLike[] | null,
): boolean[] {
  return queriesResponse?.map(q => getIsCachedFromQuery(q)) ?? [];
}

/**
 * Extracts the `cached_dttm` value from a single query response.
 * Returns empty string if the value is not defined.
 */
export function getCachedDttmFromQuery(
  query?: QueryCacheMetadata | null,
): string {
  return query?.cached_dttm ?? '';
}

/**
 * Extracts the `cached_dttm` values from an array of query responses.
 * Returns an empty array if queriesResponse is null/undefined.
 */
export function getCachedDttm(
  queriesResponse?: QueryResponseLike[] | null,
): string[] {
  return queriesResponse?.map(q => getCachedDttmFromQuery(q)) ?? [];
}

/**
 * Extracts the `queried_dttm` from the last query response.
 * Returns null if queriesResponse is null/undefined or has no queried_dttm.
 */
export function getQueriedDttm(
  queriesResponse?: QueryResponseLike[] | null,
): string | null {
  if (!Array.isArray(queriesResponse) || queriesResponse.length === 0) {
    return null;
  }
  const lastResponse = queriesResponse[queriesResponse.length - 1];
  return lastResponse?.queried_dttm ?? null;
}

/**
 * Gets the first query response from the array.
 * Returns undefined if queriesResponse is null/undefined or empty.
 */
export function getFirstQueryResponse<T extends QueryResponseLike>(
  queriesResponse?: T[] | null,
): T | undefined {
  return queriesResponse?.[0];
}

/**
 * Gets the second query response from the array.
 * Used for table visualizations that have a separate count query.
 * Returns undefined if queriesResponse is null/undefined or has less than 2 elements.
 */
export function getSecondQueryResponse<T extends QueryResponseLike>(
  queriesResponse?: T[] | null,
): T | undefined {
  return queriesResponse?.[1];
}

/**
 * Gets the row count from a single query response.
 * For table visualizations with server pagination, checks the second query
 * for total count in data[0].rowcount.
 * Falls back to sql_rowcount, then rowcount.
 */
export function getRowCountFromQueries(
  firstQuery?: QueryRowCount | null,
  secondQuery?: QueryRowCount | null,
  isTableViz = false,
): number {
  if (isTableViz && secondQuery) {
    const countFromSecondQuery = secondQuery.data?.[0]?.rowcount;
    if (countFromSecondQuery != null) {
      return Number(countFromSecondQuery);
    }
  }

  return Number(firstQuery?.sql_rowcount ?? firstQuery?.rowcount ?? 0);
}

/**
 * Gets the row count from an array of query responses.
 * For table visualizations with server pagination, checks the second query
 * for total count in data[0].rowcount.
 * Falls back to sql_rowcount, then rowcount.
 */
export function getRowCount(
  queriesResponse?: QueryResponseLike[] | null,
  isTableViz = false,
): number {
  if (!queriesResponse || queriesResponse.length === 0) {
    return 0;
  }

  return getRowCountFromQueries(
    getFirstQueryResponse(queriesResponse),
    getSecondQueryResponse(queriesResponse),
    isTableViz,
  );
}

/**
 * Gets the effective row count for display purposes.
 * This is similar to getRowCount but returns 0 for null/undefined responses.
 * @deprecated Use getRowCount instead
 */
export function getSqlRowCount(
  queriesResponse?: QueryResponseLike[] | null,
  isTableViz = false,
): number {
  return getRowCount(queriesResponse, isTableViz);
}

/**
 * Extracts cache metadata from queriesResponse.
 * Returns a single object with consolidated cache information.
 */
export function getCacheMetadata(
  queriesResponse?: QueryResponseLike[] | null,
): {
  isCached: boolean[];
  cachedDttm: string[];
  queriedDttm: string | null;
} {
  return {
    isCached: getIsCached(queriesResponse),
    cachedDttm: getCachedDttm(queriesResponse),
    queriedDttm: getQueriedDttm(queriesResponse),
  };
}

/**
 * Determines if any query result is cached.
 */
export function hasCachedResult(
  queriesResponse?: QueryResponseLike[] | null,
): boolean {
  return queriesResponse?.some(q => getIsCachedFromQuery(q)) ?? false;
}

/**
 * Gets the cache key from the first query response.
 */
export function getCacheKey(
  queriesResponse?: QueryResponseLike[] | null,
): string | null {
  return getFirstQueryResponse(queriesResponse)?.cache_key ?? null;
}

/**
 * Gets the cache timeout from the first query response.
 */
export function getCacheTimeout(
  queriesResponse?: QueryResponseLike[] | null,
): number | null {
  return getFirstQueryResponse(queriesResponse)?.cache_timeout ?? null;
}

export default {};
