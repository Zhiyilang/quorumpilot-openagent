"""NVIDIA Nemotron backend for QuorumPilot.

In-window increment for the Open Agent hackathon: the same Brain interface
quorumpilot.brain already defines, pointed at NVIDIA's OpenAI-compatible
endpoint. Nemotron is a sponsor prize ("Best use of NVIDIA Nemotron"), so this
module is the integration the prize is asking for - not a rewrite.

Design rules carried over from the rest of the project:

  * zero dependencies - urllib from the standard library only
  * never fabricate: if the call fails or the key is missing, degrade loudly
    instead of inventing proposals
  * the model is handed a closed list of locators and their exact values and
    told it may cite nothing else. It is free to ignore that instruction -
    quorumpilot.verify is the gate, not this module. A hallucinated locator
    or a number that is not the one in the bundle costs the model its claim
    in the receipt, not the user money.

Interface parity with quorumpilot.brain.LLMBrain matters: the pipeline reads
``brain.degraded`` as a property and ``brain.name`` / ``brain.error`` for the
receipt, so this class provides all three, and its propose() returns the same
claim shape.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from .brain import Brain

NEMOTRON_BASE_URL = "https://integrate.api.nvidia.com/v1"
DEFAULT_MODEL = "nvidia/nemotron-4-340b-instruct"
TIMEOUT = 30.0
STANCES = ("support", "caution", "objection")
MAX_CLAIMS = 3

SYSTEM = (
    "You are one member of a risk quorum reviewing a proposed trade.\n"
    "Return JSON: an array of objects, each with statement, stance "
    "(support|caution|objection) and evidence (a list of locator/excerpt "
    "pairs).\n"
    "Rules: cite ONLY locators from the provided list. The excerpt must quote "
    "the value exactly as given. Every claim needs at least one citation. "
    "Never suggest increasing the position size. Return at most 3 claims."
)


def closed_list(bundle: Any) -> Dict[str, Any]:
    """The locators the model may cite, mapped to their exact values.

    Accepts either the fact-bundle dict the pipeline hands to Brain.propose
    (its scalar entries only - a list or dict is not a citable fact), or any
    object exposing locators() -> iterable of {"id", "value"} / plain strings.
    """
    out: Dict[str, Any] = {}
    if hasattr(bundle, "locators"):
        for loc in (bundle.locators() or []):
            if isinstance(loc, dict) and loc.get("id") is not None:
                out[str(loc["id"])] = loc.get("value")
            elif isinstance(loc, str):
                out[loc] = None
        return out
    if isinstance(bundle, dict):
        for k, v in bundle.items():
            if not isinstance(v, (list, dict)):
                out[str(k)] = v
    return out


class NemotronBrain(Brain):
    """Brain backed by NVIDIA Nemotron over its OpenAI-compatible API."""

    name = "nemotron-specialist"

    def __init__(self, api_key: Optional[str] = None,
                 model: Optional[str] = None,
                 base_url: Optional[str] = None,
                 timeout: float = TIMEOUT) -> None:
        self.api_key = api_key or os.environ.get("NEMOTRON_API_KEY", "")
        self.model = model or os.environ.get("NEMOTRON_MODEL") or DEFAULT_MODEL
        self.base_url = (base_url or os.environ.get("NEMOTRON_BASE_URL")
                         or NEMOTRON_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.degraded_flag = not self.api_key
        self.error: Optional[str] = (None if self.api_key
                                     else "NEMOTRON_API_KEY not set")

    @property
    def degraded(self) -> bool:
        return self.degraded_flag

    def propose(self, snap, m, bundle) -> List[Dict[str, Any]]:
        if self.degraded_flag:
            return []
        allowed = closed_list(bundle)
        payload = {
            "model": self.model,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": json.dumps(
                    {"locators": allowed}, ensure_ascii=True, sort_keys=True)},
            ],
        }
        req = urllib.request.Request(
            self.base_url + "/chat/completions",
            data=json.dumps(payload).encode(),
            method="POST",
            headers={
                "Authorization": "Bearer " + self.api_key,
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                body = json.loads(resp.read().decode())
            if not isinstance(body, dict):
                raise ValueError("response body is not a JSON object")
            choices = body.get("choices") or [{}]
            first = choices[0] if isinstance(choices, list) and choices else {}
            text = (first.get("message", {}).get("content", "")
                    if isinstance(first, dict) else "")
        except (urllib.error.URLError, OSError, ValueError) as exc:
            # Degrade loudly: the caller falls back to the deterministic
            # quorum, and the receipt records that the LLM tier was down.
            self.degraded_flag = True
            self.error = "%s: %s" % (type(exc).__name__, exc)
            return []
        return _parse_claims(text)


def _parse_claims(text: str) -> List[Dict[str, Any]]:
    """Model reply -> claims in the shape the pipeline consumes.

    This function normalises; it does not judge. Whether a claim is *true* is
    decided by quorumpilot.verify, which drops anything it cannot prove and
    records the reason in the receipt - the same contract LLMBrain follows.
    Shape rules mirror LLMBrain: at most three claims, a stance the arbiter
    understands, a non-empty statement, and at least one evidence entry.
    """
    start, end = text.find("["), text.rfind("]")
    if start < 0 or end <= start:
        return []
    try:
        raw = json.loads(text[start:end + 1])
    except ValueError:
        return []
    if not isinstance(raw, list):
        return []

    out: List[Dict[str, Any]] = []
    for i, item in enumerate(raw[:MAX_CLAIMS]):
        if not isinstance(item, dict):
            continue
        stance = str(item.get("stance") or "").lower()
        if stance not in STANCES:
            continue
        statement = str(item.get("statement") or "")[:300]
        if not statement.strip():
            continue
        evidence = []
        for ev in (item.get("evidence") or []):
            if not isinstance(ev, dict):
                continue
            locator = str(ev.get("locator") or "")
            if not locator:
                continue
            evidence.append({"source": "nemotron",
                             "locator": locator,
                             "excerpt": str(ev.get("excerpt") or "")})
        if not evidence:
            continue
        out.append({
            "id": "nemotron-%d" % (i + 1),
            "agent": "nemotron-specialist",
            "statement": statement,
            "stance": stance,
            "evidence": evidence,
        })
    return out


def get_nemotron_brain(prefer: bool = True) -> Brain:
    """Factory mirroring brain.get_brain, so the CLI can select the tier."""
    if prefer and os.environ.get("NEMOTRON_API_KEY"):
        return NemotronBrain()
    from .brain import OfflineBrain
    return OfflineBrain()
