"""Curated startup failures retrieved by direct industry and idea-text matches."""
import json
import re
from pathlib import Path

LIBRARY = Path(__file__).resolve().parent.parent / "data" / "cases.json"
STOP = set("this that with from have your will they them their about into more most some what when where which while would could should there these those been being also just like only over such than then very make made using used startup startups company companies business businesses".split())


def load(path: Path = LIBRARY) -> list[dict]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"] if path.exists() else []


def _words(*texts: str | None) -> set[str]:
    return {w for t in texts if t for w in re.findall(r"[a-z][a-z+\-]{3,}", t.lower()) if w not in STOP}


def retrieve(cases: list[dict], tags: list[str], context: dict | None = None, limit: int = 3) -> tuple[list[dict], bool]:
    """Return direct industry/text matches. Do not pad results with generic cases."""
    context = context or {}
    idea = _words(context.get("concept"), context.get("vision"), context.get("customer"), context.get("revenue_model"))
    scored = []
    for c in cases:
        exact = [tag for tag in tags if tag in c["industries"]]
        searchable = set(c["keywords"]) | _words(c["sector"], c["what"], c["how_it_failed"])
        words = sorted(idea & searchable)
        # A single loose word or a broad industry family is not enough to claim similarity.
        if exact or len(words) >= 2:
            # Specific founder notes can outrank an industry-only match.
            score = 3 * len(exact) + 1.5 * min(5, len(words))
            why = [f"Industry: {tag}" for tag in exact]
            if words:
                why.append(f"Idea terms: {', '.join(words[:3])}")
            newest = max((source["published"] for source in c["sources"]), default="")
            scored.append((score, newest, c["id"], c, why))
    scored.sort(key=lambda row: (-row[0], -int(row[1].replace("-", "")) if row[1] else 0, row[2]))
    picks = [(c, why) for _, _, _, c, why in scored[:limit]]
    return [public(c, why) for c, why in picks], bool(scored)


def public(c: dict, why: list[str]) -> dict:
    """What the API shows. The internal keyword list stays private."""
    return {k: c[k] for k in ("id", "name", "years", "sector", "what", "how_it_failed", "reasons", "sources", "verified_on")} | {"matched_on": why}
