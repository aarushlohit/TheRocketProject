"""Candidate ranking for Stage 2 multi-interpretation inference."""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from typing import Any

from agent.stage0.validation import KNOWN_APPS
from agent.utils.app_map import canonicalize_app_name


RANKING_THRESHOLD = 0.6
KEYWORDS = {"open", "close", "minimize", "minimise", "maximize", "maximise", "screenshot"}


@dataclass
class RankedCandidate:
    """A candidate plus its ranking metadata."""

    candidate: Any
    score: float
    text_score: float
    app_match: float
    confidence_score: float
    context_boost: float


def rank_candidates(
    candidates: list[Any],
    *,
    preferred_app: str | None = None,
) -> list[RankedCandidate]:
    """Rank inference candidates from strongest to weakest."""
    ranked: list[RankedCandidate] = []
    canonical_preferred = (
        canonicalize_app_name(preferred_app) if isinstance(preferred_app, str) and preferred_app else None
    )

    for candidate in candidates:
        if getattr(candidate, "valid", True) is False:
            continue
        text_score = _score_text_quality(candidate.normalized_text)
        app_match = _score_app_match(candidate)
        confidence_score = float(candidate.intent.confidence)
        context_boost = _score_context_boost(candidate, canonical_preferred)
        score = text_score + app_match + confidence_score + context_boost
        ranked.append(
            RankedCandidate(
                candidate=candidate,
                score=score,
                text_score=text_score,
                app_match=app_match,
                confidence_score=confidence_score,
                context_boost=context_boost,
            )
        )

    ranked.sort(key=lambda item: item.score, reverse=True)
    return ranked


def choose_best_candidate(
    candidates: list[Any],
    *,
    preferred_app: str | None = None,
    threshold: float = RANKING_THRESHOLD,
) -> RankedCandidate | None:
    """Return the best candidate above threshold, else None."""
    ranked = rank_candidates(candidates, preferred_app=preferred_app)
    if not ranked:
        return None
    if ranked[0].score <= threshold:
        return None
    return ranked[0]


def _score_text_quality(text: str) -> float:
    if not isinstance(text, str) or not text.strip():
        return 0.0

    cleaned = text.lower().strip()
    if "?" in cleaned or "unclear" in cleaned or "illegible" in cleaned:
        return 0.0
    if any(keyword in cleaned.split() for keyword in KEYWORDS):
        return 0.4
    return 0.0


def _score_app_match(candidate: Any) -> float:
    app_name = candidate.intent.parameters.get("app")
    if not isinstance(app_name, str) or not app_name:
        return 0.0

    canonical_app = canonicalize_app_name(app_name)
    if canonical_app in KNOWN_APPS:
        return 0.4

    fuzzy = difflib.get_close_matches(canonical_app, KNOWN_APPS, n=1, cutoff=0.6)
    if fuzzy:
        return 0.4

    return 0.0


def _score_context_boost(candidate: Any, preferred_app: str | None) -> float:
    if not preferred_app:
        return 0.0

    app_name = candidate.intent.parameters.get("app")
    if not isinstance(app_name, str):
        return 0.0

    return 0.1 if canonicalize_app_name(app_name) == preferred_app else 0.0
