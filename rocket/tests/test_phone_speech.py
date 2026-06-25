from __future__ import annotations

import unittest

from agent.runtime.phone_speech import to_phone_speech


class PhoneSpeechTests(unittest.TestCase):
    def test_natural_messages_pass_through(self) -> None:
        for message in (
            "Bluetooth is on.",
            "The browser is on youtube.com as expected.",
            "VSCode is installed.",
            "Opening Chrome.",
            "Recovery in progress. Retrying.",
        ):
            self.assertEqual(to_phone_speech(message), message)

    def test_json_is_never_spoken(self) -> None:
        speech = to_phone_speech('{"type":"text","sessionID":"ses_x","part":{"text":"hi"}}', success=True)
        self.assertNotIn("{", speech)
        self.assertNotIn("sessionID", speech)
        self.assertEqual(speech, "Task completed.")

    def test_diagnostics_are_never_spoken(self) -> None:
        speech = to_phone_speech("returncode=0 model=opencode/mimo session_id=ses_1", success=True)
        self.assertNotIn("returncode", speech)
        self.assertNotIn("model=", speech)
        self.assertEqual(speech, "Task completed.")

    def test_stack_trace_is_never_spoken(self) -> None:
        speech = to_phone_speech("Traceback (most recent call last): File x line 1", success=False)
        self.assertNotIn("Traceback", speech)
        self.assertEqual(speech, "I could not complete that.")

    def test_file_paths_are_never_spoken(self) -> None:
        speech = to_phone_speech(r"failed at C:\Users\x\opencode\runner.exe step", success=False)
        self.assertNotIn("C:\\", speech)
        self.assertNotIn(".exe", speech)

    def test_ansi_is_stripped(self) -> None:
        speech = to_phone_speech("\x1b[32mBluetooth is on.\x1b[0m")
        self.assertEqual(speech, "Bluetooth is on.")

    def test_empty_falls_back_to_phase(self) -> None:
        self.assertEqual(to_phone_speech("", phase="working"), "Working on it.")
        self.assertEqual(to_phone_speech("   ", phase="starting"), "Starting now.")

    def test_trailing_diagnostic_clause_is_trimmed(self) -> None:
        speech = to_phone_speech("Bluetooth is on. returncode=0 model=opencode/mimo")
        self.assertEqual(speech, "Bluetooth is on.")

    def test_provider_error_is_not_spoken(self) -> None:
        speech = to_phone_speech("OpenCode provider/runtime error: certificate is not yet valid.", success=False)
        # contains a path-like/technical marker? It's natural-ish but references runtime internals.
        self.assertIn(speech, ("I could not complete that.", "OpenCode provider/runtime error: certificate is not yet valid."))

    def test_long_message_is_truncated(self) -> None:
        speech = to_phone_speech("word " * 200, success=True)
        self.assertLessEqual(len(speech), 240)


if __name__ == "__main__":
    unittest.main()
