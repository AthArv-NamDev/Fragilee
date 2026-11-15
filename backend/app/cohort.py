"""Real numbers from the training data for startups like yours.

Aggregates only. The data has no company names, and nothing here changes the risk band: it is context
that lets a founder see how many similar startups there are and how many of them closed.
"""
import math
from pathlib import Path

import numpy as np
import pandas as pd

MIN_N = 30   # below this a percentage says more about luck than about startups, so we show only the count

COUNTRY_NAMES = {
    "USA": "the United States", "GBR": "the United Kingdom", "CAN": "Canada", "ISR": "Israel", "RUS": "Russia",
    "FRA": "France", "DEU": "Germany", "CHN": "China", "IND": "India", "ESP": "Spain", "AUS": "Australia",
    "SWE": "Sweden", "BRA": "Brazil", "NLD": "the Netherlands", "IRL": "Ireland",
}


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    """95% range for a share. Wide when n is small, which is the honest thing to show."""
    if n == 0:
        return 0.0, 1.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


class CohortIndex:
    def __init__(self, csv_path: Path, countries: list[str]):
        df = pd.read_csv(csv_path, usecols=["failed", "country", "state", "tags", "founded_year"])
        self.countries = set(countries)
        self.failed = df["failed"].astype(int).to_numpy()
        self.country = df["country"].fillna("").to_numpy()
        self.state = df["state"].fillna("").to_numpy()
        tagsets = df["tags"].fillna("").map(lambda s: frozenset(s.split("|")) if s else frozenset())
        self.tagsets = tagsets.to_numpy()
        self.n = len(df)
        self.closed = int(self.failed.sum())
        self.years = (int(df["founded_year"].min()), int(df["founded_year"].max()))

    # -- masks ---------------------------------------------------------------------
    def _place(self, country: str, state: str | None) -> tuple[np.ndarray, str]:
        known = country in self.countries
        mask = (self.country == country) if known else ~np.isin(self.country, list(self.countries))
        name = COUNTRY_NAMES.get(country, "other countries") if known else "other countries"
        if country == "USA" and state:
            by_state = mask & (self.state == state.upper())
            if by_state.sum() >= MIN_N:
                return by_state, f"based in {state.upper()}, USA"
        return mask, f"based in {name}"

    def _industry(self, tags: list[str]) -> tuple[np.ndarray, str]:
        wanted = set(tags)
        mask = np.fromiter((bool(ts & wanted) for ts in self.tagsets), dtype=bool, count=self.n)
        phrase = f"in {tags[0]}" if len(tags) == 1 else "in at least one of your industries"
        return mask, phrase

    def _slice(self, key: str, label: str, detail: str, mask: np.ndarray) -> dict:
        n = int(mask.sum())
        k = int(self.failed[mask].sum())
        out = {"key": key, "label": label, "detail": detail, "n": n, "enough": n >= MIN_N,
               "closed_share": None, "low": None, "high": None}
        if n >= MIN_N:
            lo, hi = wilson(k, n)
            out.update(closed_share=round(k / n, 3), low=round(lo, 3), high=round(hi, 3))
        return out

    def describe(self, country: str, state: str | None, tags: list[str]) -> dict:
        place, place_txt = self._place(country, state)
        industry, ind_txt = self._industry(tags)
        slices = [
            self._slice("place_industry", "Same place and industry", f"Startups {place_txt}, {ind_txt}", place & industry),
            self._slice("place", "Same place, any industry", f"Startups {place_txt}", place),
            self._slice("industry", "Same industry, anywhere", f"Startups {ind_txt}", industry),
        ]
        return {
            "basis": f"{self.n:,} startups in the data, founded {self.years[0]} to {self.years[1]}, "
                     "each with a known final outcome (closed, or acquired and similar).",
            "overall": {"n": self.n, "closed_share": round(self.closed / self.n, 3)},
            "slices": slices,
            "note": "Descriptive counts from old data. They show what happened to similar startups, "
                    "not what will happen to yours, and they do not change your risk band.",
        }


def load(path: Path, countries: list[str]) -> "CohortIndex | None":
    return CohortIndex(path, countries) if path.exists() else None
