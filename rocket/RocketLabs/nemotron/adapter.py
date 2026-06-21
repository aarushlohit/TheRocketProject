"""Isolated adapter entry for RocketLabs."""

from agent.adapters.nemotron import NemotronAdapter
from agent.adapters.pollinations import PollinationsAdapter


def build_adapter() -> NemotronAdapter:
    return NemotronAdapter(fallback=PollinationsAdapter(model="mistral-small-3.2"))
