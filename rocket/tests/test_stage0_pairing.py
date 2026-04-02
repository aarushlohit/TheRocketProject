import json
from pathlib import Path
from tempfile import TemporaryDirectory

from agent.stage0.pairing import PairingManager


def test_pairing_manager_reuses_existing_token():
    with TemporaryDirectory() as temp_dir:
        manager = PairingManager(storage_dir=Path(temp_dir), port=8765)
        first = manager.load_or_create()
        second = manager.load_or_create()

        assert first.token == second.token
        saved = json.loads((Path(temp_dir) / "pairing.json").read_text())
        assert saved["token"] == first.token
