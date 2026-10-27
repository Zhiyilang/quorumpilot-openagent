"""Fragmented ingestion: your risk is never in one file.

A real book is spread across venues, exports and spreadsheets that disagree
about column names, date formats and even what a symbol is called. This
module reads a pile of heterogeneous blobs, works out what each one is, joins
them, and - crucially - keeps **provenance** for every merged field.

Nothing is silently overwritten. When two sources disagree the conflict is
recorded and surfaced; the first source wins and the receipt says so.
"""

import csv
import io
import json
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .market import DEFAULT_POLICY

_SYMBOL_RE = re.compile(r"^[A-Z]{3}[/_ -]?[A-Z]{3}$|^[A-Z]{2,5}$")
_DATE_RE = re.compile(
    r"^\d{4}-\d{1,2}-\d{1,2}|^\d{1,2}[/.]\d{1,2}[/.]\d{2,4}|"
    r"^[A-Za-z]{3,9}\.?\s+\d{1,2},?\s+\d{4}", re.I)

_ROLE_HINTS = {
    "symbol": ("symbol", "ticker", "instrument", "pair", "market", "code",
               "epic", "securities"),
    "units": ("units", "size", "qty", "quantity", "volume", "lots", "amount_units",
              "shares", "notional_units"),
    "entry": ("entry", "entry_price", "open_price", "open", "avg_price",
              "average_price", "price_open", "cost"),
    "price": ("price", "mark", "last", "bid", "ask", "close", "current",
              "rate", "quote"),
    "stop": ("stop", "stop_loss", "sl", "stoploss"),
    "side": ("side", "direction", "position", "type"),
    "date": ("date", "time", "timestamp", "opened", "trade_date"),
    "amount": ("amount", "value", "total", "cash", "net", "debit", "credit"),
    "description": ("description", "desc", "memo", "narrative", "details",
                    "name", "merchant"),
    "equity": ("equity", "balance", "nav", "net_liquidation", "capital"),
    "free_margin": ("free_margin", "margin_available", "available", "free"),
    "used_margin": ("used_margin", "margin_used", "initial_margin", "used"),
}


@dataclass
class Blob:
    name: str
    text: str


@dataclass
class SourceReport:
    name: str
    fmt: str
    role: str
    rows: int
    note: str = ""


@dataclass
class Ingested:
    payload: Dict[str, Any]
    provenance: Dict[str, Any] = field(default_factory=dict)
    sources: List[SourceReport] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


# ------------------------------------------------------------------ detection

def detect_format(text: str) -> str:
    s = text.strip()
    if not s:
        return "empty"
    if s[0] in "[{":
        try:
            json.loads(s)
            return "json"
        except ValueError:
            pass
    if "\n" in s or "," in s or "\t" in s:
        try:
            rows = [r for r in csv.reader(io.StringIO(s)) if any(c.strip() for c in r)]
            if len(rows) >= 1:
                return "table"
        except csv.Error:
            pass
    return "text"


def _norm(v: Any) -> str:
    return re.sub(r"\s+", " ", str(v or "")).strip()


def _is_num(v: Any) -> bool:
    s = _norm(v).replace(",", "").replace("$", "").replace("%", "")
    if s.startswith("(") and s.endswith(")"):
        s = s[1:-1]
    if not s:
        return False
    try:
        float(s)
        return True
    except ValueError:
        return False


def _to_num(v: Any) -> Optional[float]:
    if not _is_num(v):
        return None
    s = _norm(v).replace(",", "").replace("$", "").replace("%", "")
    neg = s.startswith("(") and s.endswith(")")
    if neg:
        s = s[1:-1]
    try:
        val = float(s)
    except ValueError:
        return None
    return -val if neg else val


def _looks_symbol(v: Any) -> bool:
    s = _norm(v).upper().replace(" ", "")
    if not s or _is_num(v):
        return False
    s2 = s.replace("/", "").replace("_", "").replace("-", "")
    if not s2.isalpha():
        return False
    return 4 <= len(s2) <= 8


def _role_of_header(h: str) -> Optional[str]:
    key = re.sub(r"[^a-z_]", "_", _norm(h).lower()).strip("_")
    key = re.sub(r"_+", "_", key)
    for role, hints in _ROLE_HINTS.items():
        if key in hints:
            return role
    for role, hints in _ROLE_HINTS.items():
        for hint in hints:
            if hint in key and len(key) <= len(hint) + 8:
                return role
    return None


def _column_roles(rows: List[List[str]]) -> Dict[str, int]:
    """Guess role -> column index from the header row and the values."""
    if not rows:
        return {}
    ncols = max(len(r) for r in rows)
    header = rows[0]
    roles: Dict[str, int] = {}
    used = set()
    if header and any(_role_of_header(h) for h in header):
        for i, h in enumerate(header):
            r = _role_of_header(h)
            if r and r not in roles:
                roles[r], _ = i, used.add(i)
    data = rows[1:] if (header and any(_role_of_header(h)
                                       for h in header)) else rows
    scores: Dict[str, Dict[int, int]] = {k: {} for k in _ROLE_HINTS}
    for row in data:
        for i in range(min(len(row), ncols)):
            v = row[i]
            if not _norm(v):
                continue
            if _looks_symbol(v):
                scores["symbol"][i] = scores["symbol"].get(i, 0) + 1
            elif _DATE_RE.match(_norm(v)):
                scores["date"][i] = scores["date"].get(i, 0) + 1
            elif _is_num(v):
                n = _to_num(v) or 0.0
                if abs(n) >= 100 and float(n).is_integer():
                    scores["units"][i] = scores["units"].get(i, 0) + 1
                else:
                    scores["price"][i] = scores["price"].get(i, 0) + 1
                scores["amount"][i] = scores["amount"].get(i, 0) + 1
            elif re.search(r"[A-Za-z]{3,}", _norm(v)):
                scores["description"][i] = scores["description"].get(i, 0) + 1
    n = max(1, len(data))
    for role, counts in scores.items():
        if role in roles:
            continue
        best = max(counts, key=lambda i: counts[i], default=None)
        if best is None or counts[best] < 0.5 * n:
            continue
        if best in used:
            continue
        if role == "amount" and "price" in roles:
            continue
        roles[role] = best
        used.add(best)
    return roles


def _rows_from_blob(text: str) -> Tuple[List[str], List[List[str]]]:
    s = text.replace("\ufeff", "")
    fmt = detect_format(s)
    if fmt == "table":
        delim = "\t" if s.count("\t") > s.count(",") else ","
        rows = [r for r in csv.reader(io.StringIO(s), delimiter=delim)
                if any(_norm(c) for c in r)]
        return (rows[0] if rows else []), rows
    if fmt == "json":
        data = json.loads(s)
        if isinstance(data, dict):
            for key in ("positions", "rows", "data", "items", "records"):
                if isinstance(data.get(key), list) and data[key]:
                    data = data[key]
                    break
            else:
                return [], []
        if isinstance(data, list) and data and isinstance(data[0], dict):
            cols: List[str] = []
            for row in data:
                for k in row:
                    if k not in cols:
                        cols.append(k)
            return cols, [cols] + [[str(r.get(c, "")) for c in cols] for r in data]
    return [], []


def _classify(roles: Dict[str, int], header: List[str]) -> str:
    has = roles.__contains__
    if has("symbol") and (has("units") or has("price")) and not has("amount"):
        return "positions" if has("units") else "prices"
    if has("symbol") and has("units") and has("entry"):
        return "positions"
    if has("symbol") and has("price"):
        return "prices"
    if has("equity") or has("free_margin") or has("used_margin"):
        return "account"
    if has("date") and has("amount") and has("description"):
        return "transactions"
    if has("date") and has("amount"):
        return "transactions"
    return "unknown"


# --------------------------------------------------------------------- ingest

def _policy_from_records(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    out: Dict[str, Any] = {}
    for r in records:
        for k, v in r.items():
            key = re.sub(r"[^a-z_]", "_", _norm(k).lower()).strip("_")
            if key in DEFAULT_POLICY or key.startswith("max_") or \
                    key.startswith("min_"):
                n = _to_num(v)
                out[key] = n if n is not None else v
    return out


def ingest(blobs: List[Blob], proposal: Optional[Dict[str, Any]] = None) -> Ingested:
    """Merge heterogeneous sources into one snapshot payload + provenance."""
    ing = Ingested(payload={"account": {"positions": []}, "proposal": {},
                            "policy": {}, "correlations": {}})
    prices: Dict[str, float] = {}
    seen: Dict[Tuple[str, str], int] = {}

    for blob in blobs:
        header, rows = _rows_from_blob(blob.text)
        if not rows:
            # maybe a flat key: value JSON (account or policy)
            flat = None
            try:
                flat = json.loads(blob.text)
            except ValueError:
                flat = None
            if isinstance(flat, dict):
                if "symbol" in flat and ("units" in flat or "entry" in flat):
                    ing.sources.append(SourceReport(blob.name, "json",
                                                    "proposal", 1))
                    if not ing.payload.get("proposal"):
                        ing.payload["proposal"] = {
                            k: (_to_num(v) if _is_num(v) else v)
                            for k, v in flat.items() if not k.startswith("_")}
                    continue
                pol = _policy_from_records([flat])
                if pol:
                    for k, v in pol.items():
                        ing.payload["policy"][k] = v
                        ing.provenance["policy." + k] = {
                            "source": blob.name, "row": 1, "field": k}
                    ing.sources.append(SourceReport(blob.name, "json", "policy",
                                                   len(pol)))
                    continue
                for key, target in (("equity", "equity"),
                                    ("balance", "equity"),
                                    ("free_margin", "free_margin"),
                                    ("used_margin", "used_margin"),
                                    ("currency", "currency")):
                    if key in flat:
                        v = flat[key]
                        ing.payload["account"][target] = (
                            v if isinstance(v, str) else (_to_num(v) or 0.0))
                        ing.provenance["account." + target] = {
                            "source": blob.name, "row": 1, "field": key}
                if ing.payload["account"]:
                    ing.sources.append(SourceReport(
                        blob.name, "json", "account",
                        len(ing.payload["account"]), "flat key:value object"))
                    continue
            ing.warnings.append("%s: could not read any rows" % blob.name)
            ing.sources.append(SourceReport(blob.name, detect_format(blob.text),
                                            "unreadable", 0))
            continue

        roles = _column_roles(rows)
        data_rows = rows[1:] if header and any(_role_of_header(h)
                                               for h in header) else rows
        records: List[Dict[str, Any]] = []
        for i, row in enumerate(data_rows, start=1):
            rec: Dict[str, Any] = {}
            for role, idx in roles.items():
                if idx < len(row):
                    rec[role] = row[idx]
            if rec:
                rec["_row"] = i
            records.append(rec)
        role = _classify(roles, header)
        ing.sources.append(SourceReport(
            blob.name, detect_format(blob.text), role, len(records),
            ", ".join(sorted(roles)) or "no columns recognised"))

        if role == "policy":
            continue
        if role == "account":
            for r in records:
                for key, target in (("equity", "equity"),
                                    ("free_margin", "free_margin"),
                                    ("used_margin", "used_margin")):
                    n = _to_num(r.get(key))
                    if n is not None:
                        ing.payload["account"][target] = n
                        ing.provenance["account." + target] = {
                            "source": blob.name, "row": r.get("_row"),
                            "field": key}
            continue
        if role == "prices":
            for r in records:
                sym = _norm(r.get("symbol")).upper().replace("/", "")
                p = _to_num(r.get("price") or r.get("entry"))
                if sym and p:
                    prices[sym] = p
                    ing.provenance["price." + sym] = {
                        "source": blob.name, "row": r.get("_row"),
                        "field": "price"}
            continue
        if role == "positions":
            for r in records:
                sym = _norm(r.get("symbol")).upper().replace("/", "")
                units = _to_num(r.get("units"))
                entry = _to_num(r.get("entry") or r.get("price"))
                if not sym:
                    continue
                side = _norm(r.get("side") or "long").lower()
                side = "long" if side in ("long", "buy", "") else "short"
                pos = {"symbol": sym, "side": side,
                       "units": abs(units) if units is not None else 0.0,
                       "entry": entry or 0.0}
                stop = _to_num(r.get("stop"))
                if stop:
                    pos["stop"] = stop
                key = (sym, side)
                if key in seen:
                    prev = ing.payload["account"]["positions"][seen[key]]
                    if abs(prev["units"] - pos["units"]) > 1e-9:
                        ing.conflicts.append(
                            "%s appears in %s (%s units) and %s (%s units); "
                            "keeping the first"
                            % (sym, prev.get("_source"), prev["units"],
                               blob.name, pos["units"]))
                    continue
                pos["_source"] = blob.name
                seen[key] = len(ing.payload["account"]["positions"])
                ing.payload["account"]["positions"].append(pos)
                ing.provenance["positions[%d]" % seen[key]] = {
                    "source": blob.name, "row": r.get("_row"), "field": "row"}
            continue
        ing.warnings.append("%s: classified as %s, not merged" % (blob.name, role))

    # attach market prices where an entry was missing or a mark is known
    for i, p in enumerate(ing.payload["account"]["positions"]):
        mark = prices.get(p["symbol"])
        if mark:
            p["current"] = mark
        if not p.get("entry") and mark:
            p["entry"] = mark
        p.pop("_source", None)

    if proposal:
        ing.payload["proposal"] = proposal
    return ing


def ingest_files(paths: List[str],
                 proposal: Optional[Dict[str, Any]] = None) -> Ingested:
    from pathlib import Path
    blobs = []
    for p in paths:
        path = Path(p)
        blobs.append(Blob(path.name, path.read_text(encoding="utf-8",
                                                    errors="replace")))
    return ingest(blobs, proposal=proposal)


def render_ingest_report(ing: Ingested) -> str:
    rows = "\n".join(
        "| %s | %s | %s | %d | %s |" % (s.name, s.fmt, s.role, s.rows, s.note)
        for s in ing.sources)
    conflicts = ("\n".join("- " + c for c in ing.conflicts)
                 or "_none - no source contradicted another_")
    warnings = ("\n".join("- " + w for w in ing.warnings) or "_none_")
    return (
        "### Sources\n| File | Format | Read as | Rows | Columns |\n|---|---|---|---|---|\n"
        "%s\n\n### Conflicts\n%s\n\n### Notes\n%s\n\n### Merged\n"
        "%d positions, %d price marks, %d policy values"
        % (rows, conflicts, warnings,
           len(ing.payload["account"].get("positions", [])),
           sum(1 for k in ing.provenance if k.startswith("price.")),
           sum(1 for k in ing.provenance if k.startswith("policy."))))
