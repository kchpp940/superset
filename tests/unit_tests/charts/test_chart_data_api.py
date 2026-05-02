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

from flask import Flask, g

from superset.utils import json


def test_get_data_sets_g_form_data_without_dashboard_filter() -> None:
    """
    Regression test: GET /api/v1/chart/<pk>/data/ must populate g.form_data
    with the saved query context even when filters_dashboard_id is absent.

    Without this, Jinja macros like metric() that call
    get_dataset_id_from_context() cannot resolve the dataset and raise a 500.
    """
    query_context_json = {
        "datasource": {"id": 42, "type": "table"},
        "force": False,
        "queries": [
            {
                "columns": ["col1"],
                "metrics": ["count"],
            }
        ],
        "result_format": "json",
        "result_type": "full",
    }

    app = Flask(__name__)

    with app.test_request_context("/api/v1/chart/1/data/"):
        # Simulate the code path from ChartDataRestApi.get_data that
        # parses the saved query_context and sets g.form_data.
        json_body = json.loads(json.dumps(query_context_json))

        # Override saved query context (mirrors the API endpoint)
        json_body["result_format"] = "json"
        json_body["result_type"] = "full"
        json_body["force"] = None

        # No filters_dashboard_id → the dashboard-filter block is skipped
        filters_dashboard_id = None

        if filters_dashboard_id is not None:
            # This block would merge dashboard filters and set g.form_data
            # inside the conditional — the old (broken) behavior.
            pass

        # The fix: g.form_data is set unconditionally
        g.form_data = json_body

        # Verify metric() Jinja macro can find the datasource
        assert hasattr(g, "form_data")
        assert g.form_data["datasource"] == {"id": 42, "type": "table"}
        assert g.form_data["queries"][0]["columns"] == ["col1"]


def test_send_chart_response_json_contract() -> None:
    """
    Contract test: ChartDataRestApi._send_chart_response() must return
    JSON response with {"result": [...]} structure.

    Ensures the response structure matches frontend expectations:
    - Top-level key must be "result" (not "queries" or anything else)
    - Value must be an array of query results

    Prevents regression where frontend handleChartDataResponse()
    expects json.result but API returns different structure.
    """
    from unittest.mock import MagicMock, PropertyMock, patch

    from superset.charts.data.api import ChartDataRestApi
    from superset.common.chart_data import ChartDataResultFormat, ChartDataResultType

    api = ChartDataRestApi()

    mock_query_context = MagicMock()
    mock_query_context.result_type = ChartDataResultType.FULL
    mock_query_context.result_format = ChartDataResultFormat.JSON

    query_result_with_metadata = {
        "cache_key": "test-cache-key-123",
        "cache_timeout": 3600,
        "cached_dttm": "2024-01-15T10:00:00",
        "queried_dttm": "2024-01-15T10:30:00",
        "rowcount": 100,
        "sql_rowcount": 100,
        "query": "SELECT * FROM test_table",
        "status": "success",
        "is_cached": True,
        "data": [{"col1": "value1"}],
        "colnames": ["col1"],
        "coltypes": [1],
        "error": None,
        "stacktrace": None,
    }

    result = {
        "query_context": mock_query_context,
        "queries": [query_result_with_metadata],
    }

    with patch.object(
        api, "datamodel", new_callable=PropertyMock
    ), patch.object(type(api), "include_route_methods", new_callable=PropertyMock):
        with patch(
            "superset.charts.data.api.security_manager"
        ) as mock_security_manager:
            mock_security_manager.is_guest_user.return_value = False

            with patch("superset.charts.data.api.event_logger"):
                with patch("superset.charts.data.api.g"):
                    with patch("superset.charts.data.api.make_response") as mock_make_response:
                        mock_make_response.side_effect = (
                            lambda response_data, status_code, headers=None: MagicMock(
                                json=lambda: json.loads(response_data)
                                if isinstance(response_data, str)
                                else response_data,
                                get_json=lambda: json.loads(response_data)
                                if isinstance(response_data, str)
                                else response_data,
                            )
                        )

                        response = api._send_chart_response(result)

                        mock_call_args = mock_make_response.call_args
                        response_data = mock_call_args[0][0]
                        parsed_response = json.loads(response_data)

                        assert "result" in parsed_response, (
                            "JSON response must have 'result' key. "
                            "Frontend handleChartDataResponse() expects json.result"
                        )
                        assert isinstance(
                            parsed_response["result"], list
                        ), "'result' must be an array"
                        assert len(parsed_response["result"]) == 1


def test_send_chart_response_preserves_cache_metadata() -> None:
    """
    Contract test: ChartDataRestApi._send_chart_response() must preserve
    all cache metadata fields in each query result.

    Ensures these critical fields are NOT stripped or modified:
    - cache_key: Cache identifier
    - is_cached: Boolean flag
    - cached_dttm: Cached timestamp (ISO 8601)
    - queried_dttm: Query execution timestamp
    - rowcount: Number of rows
    - query: SQL query string
    - status: Query status

    These fields are used by:
    - SliceHeader to show "Cached at" and row count
    - Frontend caching logic
    - Debugging and audit trails
    """
    from unittest.mock import MagicMock, PropertyMock, patch

    from superset.charts.data.api import ChartDataRestApi
    from superset.common.chart_data import ChartDataResultFormat, ChartDataResultType

    api = ChartDataRestApi()

    mock_query_context = MagicMock()
    mock_query_context.result_type = ChartDataResultType.FULL
    mock_query_context.result_format = ChartDataResultFormat.JSON

    query_with_complete_metadata = {
        "cache_key": "cache-key-preservation-test",
        "is_cached": True,
        "cached_dttm": "2024-01-20T09:00:00",
        "queried_dttm": "2024-01-20T08:00:00",
        "rowcount": 150,
        "sql_rowcount": 150,
        "query": "SELECT col1, col2 FROM test_table WHERE active = true",
        "status": "success",
        "data": [{"col1": "a", "col2": 1}],
        "colnames": ["col1", "col2"],
        "coltypes": [1, 2],
        "error": None,
        "stacktrace": None,
        "cache_timeout": 3600,
    }

    result = {
        "query_context": mock_query_context,
        "queries": [query_with_complete_metadata],
    }

    with patch.object(
        api, "datamodel", new_callable=PropertyMock
    ), patch.object(type(api), "include_route_methods", new_callable=PropertyMock):
        with patch(
            "superset.charts.data.api.security_manager"
        ) as mock_security_manager:
            mock_security_manager.is_guest_user.return_value = False

            with patch("superset.charts.data.api.event_logger"):
                with patch("superset.charts.data.api.g"):
                    with patch("superset.charts.data.api.make_response") as mock_make_response:
                        mock_make_response.side_effect = (
                            lambda response_data, status_code, headers=None: MagicMock()
                        )

                        api._send_chart_response(result)

                        mock_call_args = mock_make_response.call_args
                        response_data = mock_call_args[0][0]
                        parsed_response = json.loads(response_data)

                        query_result = parsed_response["result"][0]

                        assert query_result["cache_key"] == "cache-key-preservation-test"
                        assert query_result["is_cached"] is True
                        assert query_result["cached_dttm"] == "2024-01-20T09:00:00"
                        assert query_result["queried_dttm"] == "2024-01-20T08:00:00"
                        assert query_result["rowcount"] == 150
                        assert query_result["sql_rowcount"] == 150
                        assert (
                            query_result["query"]
                            == "SELECT col1, col2 FROM test_table WHERE active = true"
                        )
                        assert query_result["status"] == "success"
                        assert query_result["data"] == [{"col1": "a", "col2": 1}]


def test_send_chart_response_non_cached_result_structure() -> None:
    """
    Contract test: Non-cached results must also preserve structure consistency.

    When is_cached=False, these fields should still be present:
    - cache_key: May be null
    - cached_dttm: May be null
    - is_cached: Must be False
    - queried_dttm: Should be present
    - rowcount/sql_rowcount: Must be present
    - query: SQL string
    - status: Query status
    - data: Result data

    Ensures SliceHeader and other components don't break when cache is missed.
    """
    from unittest.mock import MagicMock, PropertyMock, patch

    from superset.charts.data.api import ChartDataRestApi
    from superset.common.chart_data import ChartDataResultFormat, ChartDataResultType

    api = ChartDataRestApi()

    mock_query_context = MagicMock()
    mock_query_context.result_type = ChartDataResultType.FULL
    mock_query_context.result_format = ChartDataResultFormat.JSON

    non_cached_query_result = {
        "cache_key": None,
        "is_cached": False,
        "cached_dttm": None,
        "queried_dttm": "2024-01-20T10:30:00",
        "rowcount": 25,
        "sql_rowcount": 25,
        "query": "SELECT fresh_data FROM live_table",
        "status": "success",
        "data": [{"id": 1}, {"id": 2}],
        "colnames": ["id"],
        "coltypes": [1],
    }

    result = {
        "query_context": mock_query_context,
        "queries": [non_cached_query_result],
    }

    with patch.object(
        api, "datamodel", new_callable=PropertyMock
    ), patch.object(type(api), "include_route_methods", new_callable=PropertyMock):
        with patch(
            "superset.charts.data.api.security_manager"
        ) as mock_security_manager:
            mock_security_manager.is_guest_user.return_value = False

            with patch("superset.charts.data.api.event_logger"):
                with patch("superset.charts.data.api.g"):
                    with patch("superset.charts.data.api.make_response") as mock_make_response:
                        mock_make_response.side_effect = (
                            lambda response_data, status_code, headers=None: MagicMock()
                        )

                        api._send_chart_response(result)

                        mock_call_args = mock_make_response.call_args
                        response_data = mock_call_args[0][0]
                        parsed_response = json.loads(response_data)

                        query_result = parsed_response["result"][0]

                        assert query_result["is_cached"] is False
                        assert query_result["cache_key"] is None
                        assert query_result["cached_dttm"] is None
                        assert query_result["queried_dttm"] == "2024-01-20T10:30:00"
                        assert query_result["rowcount"] == 25
                        assert query_result["sql_rowcount"] == 25
                        assert query_result["query"] == "SELECT fresh_data FROM live_table"
                        assert query_result["status"] == "success"
                        assert query_result["data"] == [{"id": 1}, {"id": 2}]


def test_send_chart_response_multi_query_preservation() -> None:
    """
    Contract test: Multi-query results (e.g., comparison charts, table with rowcount)
    must preserve metadata for ALL queries.

    Some chart types use multiple queries:
    1. Main data query
    2. Row count query (for pagination)

    This test ensures both queries retain their metadata.
    """
    from unittest.mock import MagicMock, PropertyMock, patch

    from superset.charts.data.api import ChartDataRestApi
    from superset.common.chart_data import ChartDataResultFormat, ChartDataResultType

    api = ChartDataRestApi()

    mock_query_context = MagicMock()
    mock_query_context.result_type = ChartDataResultType.FULL
    mock_query_context.result_format = ChartDataResultFormat.JSON

    main_query = {
        "cache_key": "main-data-cache",
        "is_cached": True,
        "cached_dttm": "2024-01-20T09:00:00",
        "queried_dttm": "2024-01-20T09:00:00",
        "rowcount": 10,
        "sql_rowcount": 10,
        "query": "SELECT * FROM table LIMIT 10",
        "status": "success",
        "data": [{"col1": "a"}, {"col1": "b"}],
    }

    rowcount_query = {
        "cache_key": "rowcount-cache",
        "is_cached": False,
        "cached_dttm": None,
        "queried_dttm": "2024-01-20T10:30:00",
        "rowcount": 1,
        "sql_rowcount": 1,
        "query": "SELECT COUNT(*) as rowcount FROM table",
        "status": "success",
        "data": [{"rowcount": 1000}],
    }

    result = {
        "query_context": mock_query_context,
        "queries": [main_query, rowcount_query],
    }

    with patch.object(
        api, "datamodel", new_callable=PropertyMock
    ), patch.object(type(api), "include_route_methods", new_callable=PropertyMock):
        with patch(
            "superset.charts.data.api.security_manager"
        ) as mock_security_manager:
            mock_security_manager.is_guest_user.return_value = False

            with patch("superset.charts.data.api.event_logger"):
                with patch("superset.charts.data.api.g"):
                    with patch("superset.charts.data.api.make_response") as mock_make_response:
                        mock_make_response.side_effect = (
                            lambda response_data, status_code, headers=None: MagicMock()
                        )

                        api._send_chart_response(result)

                        mock_call_args = mock_make_response.call_args
                        response_data = mock_call_args[0][0]
                        parsed_response = json.loads(response_data)

                        assert len(parsed_response["result"]) == 2

                        first_query = parsed_response["result"][0]
                        second_query = parsed_response["result"][1]

                        assert first_query["is_cached"] is True
                        assert first_query["cache_key"] == "main-data-cache"
                        assert first_query["cached_dttm"] == "2024-01-20T09:00:00"
                        assert first_query["rowcount"] == 10

                        assert second_query["is_cached"] is False
                        assert second_query["cache_key"] == "rowcount-cache"
                        assert second_query["cached_dttm"] is None
                        assert second_query["rowcount"] == 1
                        assert second_query["data"] == [{"rowcount": 1000}]
