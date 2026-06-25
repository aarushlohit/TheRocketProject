"""Rocket benchmark harness.

Runs the Rocket task suite (100 browser, 100 desktop, 50 install, 50
accessibility, 50 reading = 350) through a pluggable executor and scores each
task against the *real* :class:`VerifierSuite`. It records latency, retries,
recovery, verifier accuracy, false positives, and timeouts, and writes
``benchmark.json``.

What is real vs simulated:

* The verifier, the recovery engine, and all metric/false-positive computation
  are the production components.
* The execution layer (OpenCode + desktop) is pluggable. For CI a deterministic
  in-process executor is used and the report is tagged ``"mode": "simulated"``.
  Point :func:`run_benchmark` at a live executor for a real run.

A false positive is the metric that matters most: the executor reported success
but the verifier proves reality did not match. The target for a live run is 95%+
success with zero false positives; this harness measures it, it does not assert
a fabricated number.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from agent.runtime.browser_state import BrowserState, compile_browser_mission, mission_to_task
from agent.runtime.recovery import RecoveryEngine
from agent.runtime.verifier import APP_PROCESSES, RealityProbe, VerifierSuite, _is_install_request

CATEGORIES = ("browser", "desktop", "install", "accessibility", "reading")
MODALITIES = ("voice", "braille", "drawing", "text")


@dataclass(frozen=True)
class BenchmarkTask:
    id: str
    category: str
    modality: str
    prompt: str
    mission: dict[str, Any]
    reality: dict[str, Any]
    expected_success: bool


@dataclass
class ExecOutcome:
    """What the (real or simulated) execution layer reported."""

    reported_success: bool
    reality: dict[str, Any]
    message: str = ""
    retries: int = 0
    recovered: bool = False
    timed_out: bool = False
    latency_ms: float = 0.0


@dataclass
class BenchmarkResult:
    task_id: str
    category: str
    modality: str
    reported_success: bool
    verified_success: bool
    expected_success: bool
    verifiable: bool
    false_positive: bool
    latency_ms: float
    retries: int
    recovered: bool
    timed_out: bool

    def to_dict(self) -> dict[str, Any]:
        return self.__dict__.copy()


class _ScenarioProbe(RealityProbe):
    """A reality probe answered from a task's ground-truth reality dict."""

    def __init__(self, reality: dict[str, Any]) -> None:
        self._r = reality or {}

    def running_processes(self):
        value = self._r.get("processes")
        return set(value) if value is not None else None

    def find_executable(self, executables, search_paths):
        return self._r.get("executable")

    def bluetooth_enabled(self):
        return self._r.get("bluetooth")

    def wifi_connected(self):
        return self._r.get("wifi")

    def browser_state(self):
        return self._r.get("browser")

    def path_exists(self, path):
        return self._r.get("path_exists")


def _satisfying_reality(mission: dict[str, Any]) -> dict[str, Any]:
    """Ground-truth reality that a genuinely capable executor would produce.

    Derived from how the VerifierSuite routes the mission, so an honest executor
    that truly achieves the goal passes verification (zero false positives by
    construction). Unverifiable missions return an empty reality.
    """

    intent = str(mission.get("intent", "")).upper()
    context = str(mission.get("context", "")).strip().lower()
    lower = str(mission.get("mission", "")).lower()

    if _is_install_request(intent, lower):
        return {"executable": r"C:\installed\binary.exe"}
    if "bluetooth" in lower:
        return {"bluetooth": "turn off" not in lower and "disable" not in lower}
    if "wifi" in lower or "wi-fi" in lower:
        return {"wifi": "turn off" not in lower and "disable" not in lower}
    browser_sites = {"youtube.com", "spotify.com", "gmail.com", "github.com", "google.com", "reddit.com", "browser"}
    if intent in {"SEARCH", "PLAY", "PAUSE", "RESUME", "OPEN"} and context in browser_sites:
        state: dict[str, Any] = {"browser_open": True}
        if context != "browser":
            state["current_site"] = context
        if intent in {"PLAY", "RESUME"}:
            state["video_playing"] = True
        if intent == "PAUSE":
            state["video_playing"] = False
        return {"browser": state}
    if intent == "OPEN_APP" and context in APP_PROCESSES:
        return {"processes": [APP_PROCESSES[context][0]]}
    return {}


def _make_browser_tasks() -> list[BenchmarkTask]:
    sites = ["youtube", "spotify", "google", "github", "reddit"]
    queries = ["cats", "lofi music", "python tutorial", "news", "weather", "guitar", "recipes", "space", "art", "sports"]
    prompts: list[str] = []
    for site in sites:
        for query in queries:
            prompts.append(f"Search {query} on {site}")  # 50
    for query in queries[:5]:
        prompts.append(f"Play {query} on youtube")
        prompts.append(f"Pause {query} on youtube")  # +10 -> 60
    for site in sites:
        prompts.append(f"Open {site}")  # +5 -> 65
    for query in queries:
        prompts.append(f"Resume {query} on youtube")  # +10 -> 75
        prompts.append(f"Search {query} on youtube")  # +10 -> 85
    for site in sites:
        for query in queries[:3]:
            prompts.append(f"Search {query} on {site}")  # +15 -> 100
    return [_browser_task(i, prompt) for i, prompt in enumerate(prompts[:100])]


def _browser_task(index: int, prompt: str) -> BenchmarkTask:
    domain = next((d for n, d in (
        ("youtube", "youtube.com"), ("spotify", "spotify.com"), ("google", "google.com"),
        ("github", "github.com"), ("reddit", "reddit.com")) if n in prompt.lower()), "youtube.com")
    state = BrowserState(current_site=domain, browser_open=True)
    mission = compile_browser_mission(prompt, state)
    return _task("browser", index, prompt, mission, _satisfying_reality(mission), True)


def _make_desktop_tasks() -> list[BenchmarkTask]:
    apps = ["calculator", "notepad", "chrome", "explorer", "whatsapp", "settings"]
    tasks: list[BenchmarkTask] = []
    index = 0
    while len(tasks) < 100:
        app = apps[index % len(apps)]
        prompt = f"Open {app}"
        mission = compile_browser_mission(prompt, BrowserState())
        tasks.append(_task("desktop", index, prompt, mission, _satisfying_reality(mission), True))
        index += 1
    return tasks


def _make_install_tasks() -> list[BenchmarkTask]:
    labels = ["VSCode", "Git", "VLC", "Python"]
    tasks: list[BenchmarkTask] = []
    index = 0
    while len(tasks) < 50:
        prompt = f"Install {labels[index % len(labels)]}"
        mission = compile_browser_mission(prompt, BrowserState())
        tasks.append(_task("install", index, prompt, mission, _satisfying_reality(mission), True))
        index += 1
    return tasks


def _make_accessibility_tasks() -> list[BenchmarkTask]:
    specs = ["Turn on Bluetooth", "Turn on Wifi", "Open settings"]
    tasks: list[BenchmarkTask] = []
    index = 0
    while len(tasks) < 50:
        prompt = specs[index % len(specs)]
        mission = compile_browser_mission(prompt, BrowserState())
        tasks.append(_task("accessibility", index, prompt, mission, _satisfying_reality(mission), True))
        index += 1
    return tasks


def _make_reading_tasks() -> list[BenchmarkTask]:
    # Reading tasks deliver speech; the verifier has no reality probe for them,
    # so they are deferred to the executor (verifiable=False).
    prompts = ["Read Gmail", "Read the PDF", "Read clipboard", "Read latest email", "Read the document"]
    tasks: list[BenchmarkTask] = []
    index = 0
    while len(tasks) < 50:
        prompt = prompts[index % len(prompts)]
        mission = compile_browser_mission(prompt, BrowserState())
        tasks.append(_task("reading", index, prompt, mission, {}, True))
        index += 1
    return tasks


def _task(category: str, index: int, prompt: str, mission: dict[str, Any], reality: dict[str, Any], expected: bool) -> BenchmarkTask:
    modality = MODALITIES[index % len(MODALITIES)]
    return BenchmarkTask(
        id=f"{category}-{index:03d}",
        category=category,
        modality=modality,
        prompt=prompt,
        mission=mission,
        reality=reality,
        expected_success=expected,
    )


def generate_default_suite() -> list[BenchmarkTask]:
    """The full 350-task suite."""

    suite = (
        _make_browser_tasks()
        + _make_desktop_tasks()
        + _make_install_tasks()
        + _make_accessibility_tasks()
        + _make_reading_tasks()
    )
    return suite


def simulated_executor(task: BenchmarkTask) -> ExecOutcome:
    """Deterministic honest executor: reports the true reality outcome.

    Every 7th task simulates one transient failure that recovery heals, while
    still ending in the true reality state (never a false positive).
    """

    seq = int(task.id.rsplit("-", 1)[1])
    recovered = (seq % 7) == 0
    latency = 120.0 + (seq % 5) * 40.0 + {"browser": 60, "desktop": 30, "install": 200, "accessibility": 50, "reading": 90}[task.category]
    return ExecOutcome(
        reported_success=task.expected_success,
        reality=task.reality,
        message="done",
        retries=1 if recovered else 0,
        recovered=recovered,
        timed_out=False,
        latency_ms=latency,
    )


@dataclass
class CategorySummary:
    total: int = 0
    succeeded: int = 0
    false_positives: int = 0
    timeouts: int = 0
    retries: int = 0
    recovered: int = 0
    latency_ms_total: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "total": self.total,
            "succeeded": self.succeeded,
            "success_rate": round(self.succeeded / self.total, 4) if self.total else 0.0,
            "false_positives": self.false_positives,
            "timeouts": self.timeouts,
            "retries": self.retries,
            "recovered": self.recovered,
            "avg_latency_ms": round(self.latency_ms_total / self.total, 2) if self.total else 0.0,
        }


@dataclass
class BenchmarkReport:
    mode: str
    results: list[BenchmarkResult] = field(default_factory=list)

    def by_category(self) -> dict[str, CategorySummary]:
        summaries: dict[str, CategorySummary] = {category: CategorySummary() for category in CATEGORIES}
        for result in self.results:
            summary = summaries.setdefault(result.category, CategorySummary())
            summary.total += 1
            summary.succeeded += int(result.verified_success)
            summary.false_positives += int(result.false_positive)
            summary.timeouts += int(result.timed_out)
            summary.retries += result.retries
            summary.recovered += int(result.recovered)
            summary.latency_ms_total += result.latency_ms
        return summaries

    def overall(self) -> dict[str, Any]:
        total = len(self.results)
        succeeded = sum(r.verified_success for r in self.results)
        false_positives = sum(r.false_positive for r in self.results)
        latency = sum(r.latency_ms for r in self.results)
        return {
            "total": total,
            "succeeded": succeeded,
            "success_rate": round(succeeded / total, 4) if total else 0.0,
            "false_positives": false_positives,
            "timeouts": sum(r.timed_out for r in self.results),
            "retries": sum(r.retries for r in self.results),
            "recovered": sum(r.recovered for r in self.results),
            "avg_latency_ms": round(latency / total, 2) if total else 0.0,
            "verifiable_tasks": sum(r.verifiable for r in self.results),
        }

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "targets": {"success_rate": 0.95, "false_positives": 0},
            "overall": self.overall(),
            "by_category": {name: summary.to_dict() for name, summary in self.by_category().items()},
            "by_modality": self._by_modality(),
            "results": [result.to_dict() for result in self.results],
        }

    def _by_modality(self) -> dict[str, int]:
        counts: dict[str, int] = {modality: 0 for modality in MODALITIES}
        for result in self.results:
            counts[result.modality] = counts.get(result.modality, 0) + 1
        return counts

    def write(self, path: Path) -> Path:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
        return path


def run_benchmark(
    tasks: list[BenchmarkTask] | None = None,
    executor: Callable[[BenchmarkTask], ExecOutcome] | None = None,
    *,
    mode: str | None = None,
    clock: Callable[[], float] = time.perf_counter,
) -> BenchmarkReport:
    """Run the suite through ``executor`` and score against the real verifier."""

    tasks = tasks if tasks is not None else generate_default_suite()
    is_simulated = executor is None
    executor = executor or simulated_executor
    report = BenchmarkReport(mode=mode or ("simulated" if is_simulated else "live"))

    for task in tasks:
        start = clock()
        outcome = executor(task)
        measured_ms = (clock() - start) * 1000.0
        latency = outcome.latency_ms or measured_ms

        suite = VerifierSuite(_ScenarioProbe(outcome.reality))
        verifiable = suite.can_verify(task.mission)
        if verifiable:
            verified = suite.verify_mission(task.mission).passed
        else:
            verified = outcome.reported_success and not outcome.timed_out

        false_positive = bool(outcome.reported_success and verifiable and not verified)

        if not verified and not outcome.recovered:
            engine = RecoveryEngine()
            engine.begin(outcome.message or "verifier failed")
            engine.next_strategy()

        report.results.append(
            BenchmarkResult(
                task_id=task.id,
                category=task.category,
                modality=task.modality,
                reported_success=outcome.reported_success,
                verified_success=verified,
                expected_success=task.expected_success,
                verifiable=verifiable,
                false_positive=false_positive,
                latency_ms=latency,
                retries=outcome.retries,
                recovered=outcome.recovered,
                timed_out=outcome.timed_out,
            )
        )
    return report


def main() -> None:
    report = run_benchmark()
    output = Path("benchmark.json")
    report.write(output)
    overall = report.overall()
    print(f"[benchmark] mode={report.mode} tasks={overall['total']} "
          f"success_rate={overall['success_rate']} false_positives={overall['false_positives']} "
          f"-> {output}")


if __name__ == "__main__":
    main()
