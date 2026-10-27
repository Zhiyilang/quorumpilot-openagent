"""QuorumPilot - a quorum of specialist agents that must show its work.

Agents may propose. The verifier decides what counts. The arbiter decides
what to do. Nothing else in the system is allowed an opinion.
"""

__version__ = "1.0.0"

from .market import (Account, Position, Proposal, Snapshot, compute_metrics,
                     parse_snapshot, policy_check, solve_units_for_risk)
from .agents import run_specialists
from .verify import fact_bundle, verify_claims, verify_claim
from .arbitrate import arbitrate
from .brain import Brain, OfflineBrain, LLMBrain, get_brain
from .nemotron import NemotronBrain, get_nemotron_brain
from .explain import render_transcript
from .agent import review
from .receipts import build_receipt, receipt_json, render_html

__all__ = [
    "__version__", "Account", "Position", "Proposal", "Snapshot",
    "compute_metrics", "parse_snapshot", "policy_check", "solve_units_for_risk",
    "run_specialists", "fact_bundle", "verify_claims", "verify_claim",
    "arbitrate", "Brain", "OfflineBrain", "LLMBrain", "get_brain", "review",
    "NemotronBrain", "get_nemotron_brain", "render_transcript",
    "build_receipt", "receipt_json", "render_html",
]
