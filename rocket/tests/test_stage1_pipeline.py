from pathlib import Path

from agent.core.intent import Intent
from agent.stage0.pipeline import InferenceCandidate, select_best_result
from agent.stage2.ranker import choose_best_candidate, rank_candidates


def _candidate(
    *,
    action: str,
    confidence: float,
    variant_name: str,
    text: str,
    app: str | None = None,
    valid: bool = True,
) -> InferenceCandidate:
    parameters = {}
    if app is not None:
        parameters["app"] = app
    return InferenceCandidate(
        intent=Intent(action=action, parameters=parameters, confidence=confidence),
        normalized_text=text,
        model="gemini-fast",
        input_image_path=Path("input.png"),
        variant_name=variant_name,
        image_path=Path(f"{variant_name}.png"),
        image_url="https://example.com/image.png",
        raw_model_output="{}",
        message="ok",
        valid=valid,
    )


def test_select_best_result_prefers_stronger_ranked_candidate():
    selected = select_best_result(
        [
            _candidate(
                action="OPEN_APP",
                confidence=0.82,
                variant_name="original",
                text="open chrome",
                app="chrome",
            ),
            _candidate(
                action="OPEN_APP",
                confidence=0.76,
                variant_name="rotated_90",
                text="open vscod",
                app="vscode",
            ),
        ]
    )

    assert selected is not None
    assert selected.variant_name == "original"
    assert selected.ranking_score > 0.6


def test_select_best_result_returns_none_when_all_invalid():
    selected = select_best_result(
        [
            _candidate(
                action="UNKNOWN",
                confidence=0.4,
                variant_name="original",
                text="unclear",
                valid=False,
            ),
            _candidate(
                action="UNKNOWN",
                confidence=0.4,
                variant_name="rotated_90",
                text="???",
                valid=False,
            ),
        ]
    )

    assert selected is None


def test_ranker_uses_context_boost_for_previously_opened_app():
    chrome = _candidate(
        action="OPEN_APP",
        confidence=0.72,
        variant_name="original",
        text="open chrome",
        app="chrome",
    )
    vscode = _candidate(
        action="OPEN_APP",
        confidence=0.74,
        variant_name="rotated_90",
        text="open vscode",
        app="vscode",
    )

    ranked = rank_candidates([vscode, chrome], preferred_app="chrome")

    assert ranked[0].candidate.intent.parameters["app"] == "chrome"
    assert ranked[0].context_boost == 0.1


def test_choose_best_candidate_returns_none_below_threshold():
    unknown = _candidate(
        action="UNKNOWN",
        confidence=0.3,
        variant_name="original",
        text="unclear",
    )

    selected = choose_best_candidate([unknown], threshold=0.6)

    assert selected is None
