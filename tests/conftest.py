import pytest
from fastapi.testclient import TestClient

from slotbook import app as app_module


@pytest.fixture()
def client():
    app_module.engine.clear()
    app_module.engine.add_resource("room-a", "Meeting Room A")
    app_module.engine.add_resource("room-b", "Meeting Room B")
    with TestClient(app_module.app) as c:
        yield c
