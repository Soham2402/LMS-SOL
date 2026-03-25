"""Shared test fixtures for the LMS test suite."""

import json
import shutil
import tempfile
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from dal.dalmain import DataAccessLayer
from main import app
from store.json_store import JsonStore


@pytest.fixture()
def mock_data_path():
    """
    Create a temp copy of mock_data.json so tests don't mutate
    the real file. Yields the temp path, cleans up after.
    """
    src = Path(__file__).resolve().parent.parent / "mock_data.json"
    tmp = tempfile.NamedTemporaryFile(
        suffix=".json", delete=False,
    )
    shutil.copy(src, tmp.name)
    tmp.close()
    yield tmp.name
    Path(tmp.name).unlink(missing_ok=True)


@pytest.fixture()
def client(mock_data_path):
    """FastAPI TestClient wired to a DAL backed by the temp JSON."""
    store = JsonStore(path=mock_data_path)
    dal = DataAccessLayer.from_json(store=store)
    app.state.dal = dal
    return TestClient(app)


@pytest.fixture()
def dal(mock_data_path):
    """Bare DAL instance for unit-testing utils without HTTP."""
    store = JsonStore(path=mock_data_path)
    return DataAccessLayer.from_json(store=store)


def load_raw(mock_data_path: str) -> dict:
    """Read the raw JSON dict from the temp mock file."""
    return json.loads(Path(mock_data_path).read_text())
