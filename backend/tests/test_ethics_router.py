"""Tests for the ethics router. Mocks the Gemini call so no network is required."""

from __future__ import annotations

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services import ethics_service


client = TestClient(app)


def _patch_gemini(monkeypatch, payload):
    async def fake_call(system_prompt, user_content, temperature=0.7, max_tokens=3000, model=None, debug_sink=None):
        # Minimal sanity: ensure prompt was built
        assert "AI Ethics Assistant" in system_prompt
        return json.dumps(payload)

    monkeypatch.setattr(ethics_service.llm_service, "_call_gemini", fake_call)


def test_list_frameworks():
    resp = client.get("/ethics/frameworks")
    assert resp.status_code == 200
    items = resp.json()
    assert isinstance(items, list) and len(items) > 0
    ids = {f["id"] for f in items}
    assert "eu-ai-act-art-10" in ids
    assert "nist-map-1-5" in ids


def test_list_findings_filtered():
    resp = client.get("/ethics/findings", params={"dimension": "privacy", "stakeholder": "HCP"})
    assert resp.status_code == 200
    items = resp.json()
    for x in items:
        assert x["dimension"] == "privacy"
        assert x["stakeholder"] == "HCP"


def test_create_requirements(monkeypatch):
    _patch_gemini(
        monkeypatch,
        {
            "concerns": [
                {
                    "dimension": "privacy",
                    "title": "Patient Data Exposure",
                    "description": "Medical images may contain identifiable patient information.",
                    "requirement": "Remove patient identifiers from images; store scans in password-protected database.",
                    "guideline_refs": [{"id": "eu-ai-act-art-10", "framework": "EU AI Act", "article": "Art. 10"}],
                }
            ]
        },
    )
    resp = client.post(
        "/ethics/create",
        json={
            "stakeholder": "SEng",
            "system_context": "diagnostic imaging AI system",
            "concern_text": "patient data exposure",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["concerns"][0]["dimension"] == "privacy"
    ref = body["concerns"][0]["guideline_refs"][0]
    # KB enrichment should populate the article title
    assert ref["title"] == "Data Governance"


def test_validate_requirements(monkeypatch):
    _patch_gemini(
        monkeypatch,
        {
            "checks": [
                {
                    "id": "eu-ai-act-art-12",
                    "framework": "EU AI Act",
                    "article": "Art. 12",
                    "status": "missing",
                    "gap": "no logging requirement",
                    "suggested_addition": "log who accessed each scan with timestamps",
                }
            ],
            "summary": "Requirement needs 1 addition for full compliance",
        },
    )
    resp = client.post(
        "/ethics/validate",
        json={
            "stakeholder": "SEng",
            "requirement_text": "Only radiologists can access patient scans",
            "framework_names": ["EU AI Act"],
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["checks"][0]["status"] == "missing"
    assert body["checks"][0]["title"] == "Record-keeping (Logging)"
    assert "addition" in body["summary"].lower()


def test_chat_validate_custom_topic_uses_topic_guidance(monkeypatch):
    calls = []

    async def fake_call(system_prompt, user_content, temperature=0.7, max_tokens=3000, model=None, debug_sink=None):
        calls.append({"system_prompt": system_prompt, "user_content": user_content})
        if "intent classifier" in system_prompt:
            return json.dumps(
                {
                    "mode": "validate",
                    "assistant_text": "I will validate this requirement against the chat topic.",
                    "concern_text": "",
                    "system_context": "",
                    "requirement_text": "Only owners may unlock the smart-home hub remotely.",
                    "dimension": "privacy",
                }
            )
        assert "TARGET GUIDANCE" in system_prompt
        assert "TARGET FRAMEWORKS" not in system_prompt
        assert "OWASP IoT" in system_prompt
        assert "Do NOT return every check as \"not_applicable\"" in system_prompt
        return json.dumps(
            {
                "checks": [
                    {
                        "id": "smart-home-iot-privacy-check-1",
                        "framework": "OWASP IoT",
                        "article": "Guidance",
                        "title": "Remote access authorization",
                        "status": "missing",
                        "gap": "The requirement does not define authentication strength or auditability.",
                        "suggested_addition": "Require MFA and audit logs for every remote unlock attempt.",
                    }
                ],
                "summary": "Requirement needs 1 addition for the custom topic.",
            }
        )

    monkeypatch.setattr(ethics_service.llm_service, "_call_gemini", fake_call)

    resp = client.post(
        "/ethics/chat",
        json={
            "stakeholder": "SEng",
            "prompt": 'Validate this requirement: "Only owners may unlock the smart-home hub remotely."',
            "topic": "Smart-Home IoT Privacy",
            "topic_prompt": "Focus on consumer smart-home privacy and security. Reference OWASP IoT guidance where appropriate.",
        },
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mode"] == "validate"
    assert body["validate"]["checks"][0]["framework"] == "OWASP IoT"
    assert len(calls) == 2


def test_compare_scenarios(monkeypatch):
    _patch_gemini(
        monkeypatch,
        {
            "original_requirement": "Store patient CT scans in encrypted database",
            "suggestions": [
                {
                    "id": "int-hcp-privacy-1",
                    "source": "interview",
                    "stakeholder": "HCP",
                    "dimension": "privacy",
                    "quote": "stub",
                    "recommendation": "Host AI system within hospital network",
                },
                {
                    "id": "reddit-hcp-privacy-1",
                    "source": "reddit",
                    "stakeholder": "HCP",
                    "dimension": "privacy",
                    "quote": "stub",
                    "recommendation": "Remove hidden identifiers from files",
                },
            ],
            "enhanced_requirement": "Store patient CT scans in encrypted on-premises database with stripped DICOM identifiers.",
        },
    )
    resp = client.post(
        "/ethics/compare",
        json={
            "stakeholder": "HCP",
            "requirement_text": "Store patient CT scans in encrypted database",
            "dimension": "privacy",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert len(body["suggestions"]) == 2
    # KB should have replaced the stub quote with the canonical one
    assert body["suggestions"][0]["quote"].startswith("In Chinese hospitals")
    assert "encrypted" in body["enhanced_requirement"]
