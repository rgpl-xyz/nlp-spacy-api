import importlib

from fastapi.testclient import TestClient

import app.api
from app.api import create_app
from app.tests.conftest import records


def test_root_redirects_to_the_docs(client):
    response = client.get("/")

    assert response.status_code == 200
    assert str(response.url).endswith("/docs")


def test_the_openapi_schema_builds_with_the_example_request(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200
    body = response.json()["paths"]["/noun_phrases"]["post"]["requestBody"]["content"]["application/json"]
    assert body["schema"]["examples"][0]["values"][0]["recordId"] == "a1"


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


def test_every_route_returns_the_same_record_envelope(client):
    for path in ["/entities", "/entities_by_type", "/noun_phrases", "/extract_all"]:
        response = client.post(path, json=records("Apple was founded in California."))

        assert response.status_code == 200, path
        [record] = response.json()["values"]
        assert set(record) == {"recordId", "data", "errors", "warnings"}, path


def test_entities_by_type_groups_names_under_plural_labels(client):
    response = client.post("/entities_by_type", json=records("Apple Inc. was founded by Steve Jobs in California."))

    data = response.json()["values"][0]["data"]
    assert data["organizations"] == ["Apple Inc."]
    assert data["people"] == ["Steve Jobs"]
    assert data["gpes"] == ["California"]


def test_extract_all_returns_both_and_keeps_records_that_share_an_id(client):
    body = records("Apple makes phones.", "Google makes search.")
    body["values"][1]["recordId"] = "r0"

    response = client.post("/extract_all", json=body)

    values = response.json()["values"]
    assert len(values) == 2
    assert [entity["name"] for entity in values[1]["data"]["entities"]] == ["Google"]
    assert values[1]["data"]["noun_phrases"] == ["Google", "search"]


def test_a_failing_record_does_not_fail_the_request(client, nlp):
    too_long = "word " * (nlp.max_length // 5 + 1)

    response = client.post("/noun_phrases", json=records("The quick brown fox.", too_long))

    assert response.status_code == 200
    assert response.json()["values"][1]["errors"]


def test_warns_about_languages_the_model_does_not_speak(client):
    response = client.post("/noun_phrases", json=records("Le chat noir dort.", language="fr"))

    [record] = response.json()["values"]
    assert record["warnings"] == [{"message": "Language 'fr' isn't supported; the text was analyzed as 'en'."}]


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
