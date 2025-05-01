from unittest.mock import MagicMock, patch

import pytest
from pandas import DataFrame

from snowflake_opendic.catalog import OpenDicSnowflakeCatalog
from snowflake_opendic.pretty_pesponse import PrettyResponse

MOCK_API_URL = "https://mock-api-url.com"


@pytest.fixture
def mock_conn():
    """Creates a mock SnowflakeConn."""
    return MagicMock()


@pytest.fixture
@patch("snowflake_opendic.client.OpenDicClient.get_polaris_oauth_token", return_value="mocked_token")
def catalog(mock_get_token, mock_conn):
    """Creates an instance of OpenDicCatalog with mock Spark and mock credentials."""
    return OpenDicSnowflakeCatalog(mock_conn, MOCK_API_URL, "mock_client_id", "mock_client_secret")


# ---- Tests for SHOW ----
@patch("snowflake_opendic.client.OpenDicClient.get")
def test_show(mock_get, catalog):
    mock_get.return_value = DataFrame()

    query = "SHOW OPEN function"

    response: PrettyResponse = catalog.sql(query)

    mock_get.assert_called_once_with("/objects/function")
    assert isinstance(response, PrettyResponse)

@patch("snowflake_opendic.client.OpenDicClient.get")
def test_sync(mock_get, catalog):
    mock_get.return_value = [{"definition": "CREATE OR REPLACE FUNCTION my_function AS\n    'SELECT 1';"}]

    query = "SYNC OPEN function for snowflake"

    response = catalog.sql(query)

    mock_get.assert_called_once_with("/objects/function/platforms/snowflake/pull")
    assert isinstance(response, PrettyResponse)
