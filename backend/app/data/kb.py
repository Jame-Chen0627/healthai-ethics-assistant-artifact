"""Static knowledge base loader for the HealthAI Ethics Assistant.

Loads frameworks (EU AI Act / NIST AI RMF articles) and triangulated findings
(interview + Reddit quotes from the underlying paper) from JSON files shipped
with the backend. Loaded once at import time.
"""

import json
from pathlib import Path
from typing import Optional

_DATA_DIR = Path(__file__).parent

ETHICAL_DIMENSIONS = ["privacy", "safety", "bias", "transparency", "accountability"]
STAKEHOLDERS = ["HCP", "SEng", "HCR"]
SOURCES = ["interview", "reddit"]


def _load_json(name: str) -> list[dict]:
    with (_DATA_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


_FRAMEWORKS: list[dict] = _load_json("frameworks.json")
_FINDINGS: list[dict] = _load_json("triangulation_findings.json")


def get_frameworks() -> list[dict]:
    """Return all framework articles."""
    return list(_FRAMEWORKS)


def get_framework_names() -> list[str]:
    """Return distinct framework names (e.g. 'EU AI Act', 'NIST AI RMF')."""
    seen: list[str] = []
    for f in _FRAMEWORKS:
        if f["framework"] not in seen:
            seen.append(f["framework"])
    return seen


def find_frameworks(
    dimensions: Optional[list[str]] = None,
    framework_names: Optional[list[str]] = None,
) -> list[dict]:
    """Filter frameworks by ethical dimension and/or framework name."""
    items = _FRAMEWORKS
    if framework_names:
        wanted = {n.lower() for n in framework_names}
        items = [f for f in items if f["framework"].lower() in wanted]
    if dimensions:
        wanted_d = {d.lower() for d in dimensions}
        items = [f for f in items if any(d.lower() in wanted_d for d in f.get("applies_to", []))]
    return list(items)


def get_findings() -> list[dict]:
    """Return all triangulated findings."""
    return list(_FINDINGS)


def find_findings(
    dimension: Optional[str] = None,
    stakeholder: Optional[str] = None,
    source: Optional[str] = None,
) -> list[dict]:
    """Filter findings by dimension / stakeholder / source."""
    items = _FINDINGS
    if dimension:
        d = dimension.lower()
        items = [x for x in items if x["dimension"].lower() == d]
    if stakeholder:
        s = stakeholder.lower()
        items = [x for x in items if x["stakeholder"].lower() == s]
    if source:
        src = source.lower()
        items = [x for x in items if x["source"].lower() == src]
    return list(items)
