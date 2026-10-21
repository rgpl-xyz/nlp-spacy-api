import importlib

from fastapi.testclient import TestClient

import app.api
from app.api import create_app
from app.tests.conftest import records


def test_root_redirects_to_the_docs(client):
    response = client.get("/")

    assert response.status_code == 200
    assert str(response.url).endswith("/docs")


def test_health_names_the_loaded_model(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "model": "en_core_web_sm"}


def test_noun_phrases(client):
    response = client.post("/noun_phrases", json=records("The quick brown fox jumps over the lazy dog."))

    assert response.status_code == 200
    [record] = response.json()["values"]
    assert record["recordId"] == "r0"
    assert record["data"]["noun_phrases"] == ["The quick brown fox", "the lazy dog"]


def test_entities(client):
    response = client.post("/entities", json=records("Apple Inc. was founded by Steve Jobs in California."))

    assert response.status_code == 200
    [record] = response.json()["values"]
    found = {(entity["name"], entity["label"]) for entity in record["data"]["entities"]}
    assert {("Apple Inc.", "ORG"), ("Steve Jobs", "PERSON"), ("California", "GPE")} <= found


def test_the_model_loads_at_startup_not_at_import(nlp):
    loads = []

    def load_nlp():
        loads.append("loaded")
        return nlp

    application = create_app(load_nlp=load_nlp)
    assert loads == []

    with TestClient(application) as started:
        assert loads == ["loaded"]
        assert started.get("/health").status_code == 200


def test_the_app_imports_from_any_working_directory(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    importlib.reload(app.api)
