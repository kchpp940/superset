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
"""Tests for query_actions module, specifically testing cache field consistency."""

from unittest.mock import MagicMock

import pandas as pd
import pytest

from superset.common.chart_data import ChartDataResultType
from superset.common.query_actions import _get_full
from superset.common.db_query_status import QueryStatus


@pytest.fixture
def mock_query_context() -> MagicMock:
    """Create a mock QueryContext for testing."""
    context = MagicMock()
    context.result_type = ChartDataResultType.FULL
    context.result_format = "json"
    context.form_data = {}
    return context


@pytest.fixture
def mock_query_obj() -> MagicMock:
    """Create a mock QueryObject for testing."""
    obj = MagicMock()
    obj.result_type = None
    return obj


@pytest.fixture
def mock_datasource() -> MagicMock:
    """Create a mock datasource for testing."""
    datasource = MagicMock()
    datasource.query_language = "sql"
    datasource.get_time_grains = MagicMock(return_value=[])
    datasource.get_query_str = MagicMock(return_value="SELECT * FROM table")
    datasource.columns = []
    return datasource


def create_mock_payload(
    is_cached: bool = False,
    cached_dttm: str | None = "2024-01-15T10:00:00",
    queried_dttm: str | None = "2024-01-15T10:30:00",
    rowcount: int = 100,
    sql_rowcount: int = 100,
    cache_key: str | None = "cache_key_123",
    cache_timeout: int = 3600,
    status: str = QueryStatus.SUCCESS,
) -> dict:
    """Create a mock payload for testing."""
    df = pd.DataFrame({"col1": ["value1", "value2"], "col2": [1, 2]})
    return {
        "cache_key": cache_key,
        "cached_dttm": cached_dttm,
        "queried_dttm": queried_dttm,
        "cache_timeout": cache_timeout,
        "df": df,
        "is_cached": is_cached,
        "rowcount": rowcount,
        "sql_rowcount": sql_rowcount,
        "status": status,
        "applied_filter_columns": [],
        "rejected_filter_columns": [],
        "applied_time_extras": {},
    }


class TestGetFullCacheFields:
    """Tests for cache field consistency in _get_full function."""

    def test_results_type_includes_all_cache_fields_when_cached(
        self,
        mock_query_context: MagicMock,
        mock_query_obj: MagicMock,
        mock_datasource: MagicMock,
    ) -> None:
        """
        Test that ChartDataResultType.RESULTS includes all cache fields
        when the query is cached.

        This test verifies that the fix for the missing cache fields
        in ChartDataResultType.RESULTS is working correctly.
        """
        mock_query_obj.result_type = ChartDataResultType.RESULTS
        mock_payload = create_mock_payload(
            is_cached=True,
            cached_dttm="2024-01-15T10:00:00",
            queried_dttm="2024-01-15T10:30:00",
            rowcount=100,
            sql_rowcount=500,
            cache_key="test_cache_key_456",
            cache_timeout=7200,
        )

        mock_query_context.get_df_payload = MagicMock(return_value=mock_payload)
        mock_query_context.get_data = MagicMock(return_value=[{"col1": "value1"}])
        mock_query_context.datasource = mock_datasource
        mock_query_obj.datasource = None

        result = _get_full(mock_query_context, mock_query_obj)

        assert result.get("is_cached") is True
        assert result.get("cached_dttm") == "2024-01-15T10:00:00"
        assert result.get("queried_dttm") == "2024-01-15T10:30:00"
        assert result.get("cache_key") == "test_cache_key_456"
        assert result.get("cache_timeout") == 7200
        assert result.get("rowcount") == 100
        assert result.get("sql_rowcount") == 500

    def test_results_type_includes_all_cache_fields_when_not_cached(
        self,
        mock_query_context: MagicMock,
        mock_query_obj: MagicMock,
        mock_datasource: MagicMock,
    ) -> None:
        """
        Test that ChartDataResultType.RESULTS includes all cache fields
        even when the query is NOT cached.

        This ensures that the fields are consistently present regardless
        of cache status, preventing undefined/null access errors.
        """
        mock_query_obj.result_type = ChartDataResultType.RESULTS
        mock_payload = create_mock_payload(
            is_cached=False,
            cached_dttm=None,
            queried_dttm="2024-01-15T11:00:00",
            rowcount=50,
            sql_rowcount=50,
            cache_key=None,
            cache_timeout=0,
        )

        mock_query_context.get_df_payload = MagicMock(return_value=mock_payload)
        mock_query_context.get_data = MagicMock(return_value=[{"col1": "value1"}])
        mock_query_context.datasource = mock_datasource
        mock_query_obj.datasource = None

        result = _get_full(mock_query_context, mock_query_obj)

        assert result.get("is_cached") is False
        assert result.get("cached_dttm") is None
        assert result.get("queried_dttm") == "2024-01-15T11:00:00"
        assert result.get("cache_key") is None
        assert result.get("cache_timeout") == 0
        assert result.get("rowcount") == 50
        assert result.get("sql_rowcount") == 50

    def test_full_type_includes_all_cache_fields(
        self,
        mock_query_context: MagicMock,
        mock_query_obj: MagicMock,
        mock_datasource: MagicMock,
    ) -> None:
        """
        Test that ChartDataResultType.FULL includes all cache fields.

        This verifies that the full result type already had the correct
        behavior and hasn't regressed.
        """
        mock_query_obj.result_type = ChartDataResultType.FULL
        mock_payload = create_mock_payload(
            is_cached=True,
            cached_dttm="2024-01-15T10:00:00",
            queried_dttm="2024-01-15T10:30:00",
            rowcount=200,
            sql_rowcount=1000,
            cache_key="full_cache_key",
            cache_timeout=3600,
        )

        mock_query_context.get_df_payload = MagicMock(return_value=mock_payload)
        mock_query_context.get_data = MagicMock(return_value=[{"col1": "value1"}])
        mock_query_context.datasource = mock_datasource
        mock_query_obj.datasource = None

        result = _get_full(mock_query_context, mock_query_obj)

        assert result.get("is_cached") is True
        assert result.get("cached_dttm") == "2024-01-15T10:00:00"
        assert result.get("queried_dttm") == "2024-01-15T10:30:00"
        assert result.get("cache_key") == "full_cache_key"
        assert result.get("cache_timeout") == 3600
        assert result.get("rowcount") == 200
        assert result.get("sql_rowcount") == 1000

    def test_results_type_does_not_include_extra_full_type_fields(
        self,
        mock_query_context: MagicMock,
        mock_query_obj: MagicMock,
        mock_datasource: MagicMock,
    ) -> None:
        """
        Test that ChartDataResultType.RESULTS does NOT include fields
        that are specific to FULL type, like applied_filters, rejected_filters, etc.

        This verifies that we're only adding the cache fields, not changing
        the overall behavior of RESULTS vs FULL result types.
        """
        mock_query_obj.result_type = ChartDataResultType.RESULTS
        mock_payload = create_mock_payload(
            is_cached=True,
        )

        mock_query_context.get_df_payload = MagicMock(return_value=mock_payload)
        mock_query_context.get_data = MagicMock(return_value=[{"col1": "value1"}])
        mock_query_context.datasource = mock_datasource
        mock_query_obj.datasource = None

        result = _get_full(mock_query_context, mock_query_obj)

        assert "applied_filters" not in result
        assert "rejected_filters" not in result

    def test_results_type_includes_data_and_rowcount_fields(
        self,
        mock_query_context: MagicMock,
        mock_query_obj: MagicMock,
        mock_datasource: MagicMock,
    ) -> None:
        """
        Test that ChartDataResultType.RESULTS still includes the required
        data fields (data, colnames, coltypes, rowcount, sql_rowcount, detected_currency).

        This ensures that we haven't broken the existing behavior while
        adding the cache fields.
        """
        mock_query_obj.result_type = ChartDataResultType.RESULTS
        mock_payload = create_mock_payload(
            is_cached=True,
            rowcount=150,
            sql_rowcount=750,
        )

        mock_query_context.get_df_payload = MagicMock(return_value=mock_payload)
        mock_query_context.get_data = MagicMock(
            return_value=[{"col1": "value1"}, {"col1": "value2"}]
        )
        mock_query_context.datasource = mock_datasource
        mock_query_obj.datasource = None

        result = _get_full(mock_query_context, mock_query_obj)

        assert "data" in result
        assert "colnames" in result
        assert "coltypes" in result
        assert result.get("rowcount") == 150
        assert result.get("sql_rowcount") == 750
        assert "detected_currency" in result
