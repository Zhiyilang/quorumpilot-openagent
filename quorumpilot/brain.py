"""Optional LLM specialist.

The model is handed a closed list of locators and their exact values and is
told it may cite nothing else. Anything it hallucinates fails verification
and is dropped - visibly, in the receipt. With no API key the quorum runs the
four deterministic specialists alone and says so.
"""

import json
import os
import urllib.request
from typing import Any, Dict, List, Optional

from .verify import fact_bundle

SYSTEM = (
    "You are one member of a risk quorum reviewing a proposed trade.\n"
    "Return JSON: {\"claims\": [{\"statement\": str, \"stance\": "
    "\"support|caution|objection\", \"evidence\": [{\"locator\": str, "
    "\"excerpt\": str}]}]}\n"
    "Rules: cite ONLY locators from the provided map. The excerpt must quote "
    "the value exactly as given. Every claim needs at least one citation. "
    "Never suggest increasing the position size. Return at most 3 claims."
)


class Brain:
    name = "none"

    def propose(self, snap, m, bundle) -> List[Dict[str, Any]]:
        return []

    @property
    def degraded(self) -> bool:
        return False


class OfflineBrain(Brain):
    """No network. The deterministic specialists carry the whole quorum."""

    name = "offline-deterministic"


class LLMBrain(Brain):
    """Any OpenAI-compatible chat endpoint (Gemini, vLLM, Together, ...)."""

    name = "llm-specialist"

    def __init__(self, base_url: Optional[str] = None,
                 api_key: Optional[str] = None,
                 model: Optional[str] = None, timeout: float = 20.0):
        self.base_url = (base_url or os.environ.get("OPENAI_BASE_URL")
                         or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY", "")
        self.model = model or os.environ.get("OPENAI_MODEL") or "gpt-4o-mini"
        self.timeout = timeout
        self.degraded_flag = False
        self.error: Optional[str] = None

    @property
    def degraded(self) -> bool:
        return self.degraded_flag

    def propose(self, snap, m, bundle) -> List[Dict[str, Any]]:
        if not self.api_key:
            return []
        allowed = {k: v for k, v in bundle.items()
                   if not isinstance(v, (list, dict))}
        prompt = (
            "Proposed trade: %s %s %.0f units at %.5f, stop %.5f, target %s.\n"
            "Account equity: %.2f %s. Open positions: %d.\n"
            "Locator map (cite only these):\n%s"
            % (m["proposal.side"], m["proposal.symbol"], m["proposal.units"],
               m["proposal.entry"], m["proposal.stop"] or 0,
               m["proposal.take_profit"] or 0, m["account.equity"],
               m["account.currency"], m["account.open_positions"],
               json.dumps(allowed, ensure_ascii=False)[:4000])
        )
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        req = urllib.request.Request(
            "%s/chat/completions" % self.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json",
                     "Authorization": "Bearer " + self.api_key},
            method="POST")
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            content = data["choices"][0]["message"]["content"]
            raw = json.loads(content).get("claims") or []
        except Exception as exc:                       # degrade, never crash
            self.degraded_flag = True
            self.error = "%s: %s" % (type(exc).__name__, exc)
            return []

        out: List[Dict[str, Any]] = []
        for i, c in enumerate(raw[:3]):
            if not isinstance(c, dict):
                continue
            stance = str(c.get("stance") or "").lower()
            if stance not in ("support", "caution", "objection"):
                continue
            ev = []
            for e in (c.get("evidence") or []):
                if isinstance(e, dict) and e.get("locator"):
                    ev.append({"source": "llm",
                               "locator": str(e["locator"]),
                               "excerpt": str(e.get("excerpt") or "")})
            if not ev:
                continue
            out.append({
                "id": "llm-%d" % (i + 1),
                "agent": "llm-specialist",
                "statement": str(c.get("statement") or "")[:300],
                "stance": stance,
                "evidence": ev,
            })
        return out


def get_brain(prefer_llm: bool = True) -> Brain:
    if not prefer_llm:
        return OfflineBrain()
    if os.environ.get("OPENAI_API_KEY"):
        return LLMBrain()
    return OfflineBrain()
