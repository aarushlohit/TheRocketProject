import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.core.intent import Intent
from agent.core.nova_stage0 import NovaStageZeroAgent
from agent.core.result import Result
from agent.stage0.pipeline import InferenceResult
from agent.utils.config import Config


class FakePipeline:
    def __init__(self, inference):
        self.inference = inference

    async def process_drawing(self, image_bytes, preferred_app=None):
        return self.inference

    async def close(self):
        return None


class FakeExecutor:
    def __init__(self):
        self.calls = []

    async def execute(self, intent):
        self.calls.append(intent)
        return Result(status="debug", message="Dry run executed")


def test_handle_drawing_image_blocks_unknown_intent():
    with TemporaryDirectory() as temp_dir:
        inference = InferenceResult(
            intent=Intent(action="UNKNOWN", parameters={}, confidence=0.4),
            normalized_text="scribble",
            model="gemini-fast",
            input_image_path=Path(temp_dir) / "input.png",
            variant_name="original",
            image_path=Path(temp_dir) / "input.png",
            image_url="https://media.pollinations.ai/test_img",
            raw_model_output="{}",
            message="Could not determine intent",
            ranking_score=0.2,
            candidates=[],
        )

        agent = NovaStageZeroAgent.__new__(NovaStageZeroAgent)
        agent.config = Config(data_dir=Path(temp_dir))
        agent.trace_mode = False
        agent.last_opened_app = None
        agent.pipeline = FakePipeline(inference)
        agent.executor = FakeExecutor()

        payload = asyncio.run(agent.handle_drawing_image(b"png"))

        assert payload["status"] == "blocked"
        assert payload["reason"] == "uncertain intent"
        assert payload["intent"] == "UNKNOWN"
        assert agent.executor.calls == []
