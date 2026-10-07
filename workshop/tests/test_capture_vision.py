"""Protocol/validation regressions with mocked CLI; no inference is performed."""
import json
import subprocess
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase
from PIL import Image

from workshop import capture_vision as vision


def extraction():
    return {**{key: None for key in vision.TEXT_FIELDS}, "vehicle_year": None, "odometer": 0,
        "services": [{"description": "Revisar frenos", "kind": "unknown", "quantity": None,
                      "unit_price": None, "unit_cost": None, "part_sku": None}],
        "warnings": ["Placa parcialmente ilegible"]}


class CaptureVisionTests(SimpleTestCase):
    def test_cancellation_stops_real_child_and_never_accepts_a_result(self):
        cancel = threading.Event()
        started = []
        actual_popen = subprocess.Popen

        def launch(*args, **kwargs):
            process = actual_popen(*args, **kwargs)
            started.append(process)
            return process

        timer = threading.Timer(0.2, cancel.set)
        timer.start()
        try:
            with patch.object(vision.subprocess, "Popen", side_effect=launch):
                with self.assertRaisesMessage(ValidationError, "se canceló"):
                    vision._run_cancelable([sys.executable, "-c", "import sys,time; sys.stdin.read(); time.sleep(60)"], "synthetic", cancel)
        finally:
            timer.cancel()
        self.assertEqual(len(started), 1)
        self.assertIsNotNone(started[0].poll())
        self.assertTrue(started[0].stdout.closed)
        self.assertTrue(started[0].stderr.closed)

    def test_timeout_terminates_and_kills_unresponsive_child(self):
        process = Mock()
        process.poll.return_value = None
        process.wait.side_effect = [subprocess.TimeoutExpired("codex", 1), 0]
        with patch.object(vision.subprocess, "Popen", return_value=process), patch.object(vision.time, "monotonic", side_effect=[0, 91]):
            with self.assertRaises(subprocess.TimeoutExpired):
                vision._run_cancelable(["codex"], "synthetic", threading.Event())
        process.terminate.assert_called_once_with()
        process.kill.assert_called_once_with()
        self.assertEqual(process.wait.call_count, 2)
        process.communicate.assert_not_called()

    def test_polling_sends_prompt_once_and_preserves_completed_output(self):
        process = Mock()
        process.returncode = 0
        process.poll.return_value = 0
        process.communicate.side_effect = [subprocess.TimeoutExpired("codex", 0.5), ("completed", "diagnostic")]
        with patch.object(vision.subprocess, "Popen", return_value=process):
            result = vision._run_cancelable(["codex"], "synthetic", threading.Event())
        self.assertEqual([call.kwargs["input"] for call in process.communicate.call_args_list], ["synthetic", None])
        self.assertEqual(result.stdout, "completed")
        process.terminate.assert_not_called()
        cancel = threading.Event()
        cancel.set()
        with patch.object(vision.subprocess, "Popen") as launch:
            with self.assertRaises(ValidationError):
                vision._run_cancelable(["codex"], "synthetic", cancel)
            launch.assert_not_called()

    def test_unknown_values_and_zero_mileage_survive_without_invented_prices(self):
        result = vision.validate_extraction(extraction())
        self.assertEqual(result["data"]["odometer"], "0")
        self.assertEqual(result["data"]["vehicle_year"], "")
        self.assertIsNone(result["service_items"][0]["quantity"])
        self.assertIsNone(result["service_items"][0]["unit_price"])
        self.assertEqual(result["service_items"][0]["kind"], "unknown")

    def test_rejects_wrong_shapes_extra_fields_and_out_of_range_values(self):
        bad_cases = []
        for key, value in [("odometer", True), ("odometer", -1), ("vehicle_year", 1800),
                           ("phone", 123), ("complaint", "a" * 4001), ("warnings", [None]),
                           ("warnings", ["x"] * 21), ("services", [extraction()["services"][0]] * 51)]:
            candidate = extraction()
            candidate[key] = value
            bad_cases.append(candidate)
        candidate = extraction()
        candidate["sql"] = "DROP TABLE"
        bad_cases.append(candidate)
        candidate = extraction()
        del candidate["phone"]
        bad_cases.append(candidate)
        for candidate in bad_cases:
            with self.subTest(candidate=candidate), self.assertRaises(ValidationError):
                vision.validate_extraction(candidate)

    def test_decimal_validation_never_rounds_or_accepts_unknown_as_zero(self):
        for key, values in {"quantity": ["0", "-1", "1.0001", True, "NaN", "1e2"],
                            "unit_price": ["", "1,000", "$10", "0.001", 0, "Infinity", "1e1", "1000000000000"]}.items():
            for value in values:
                candidate = extraction()
                candidate["services"][0][key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ValidationError):
                    vision.validate_extraction(candidate)
        candidate = extraction()
        candidate["services"][0].update(quantity="1.250", unit_price="0.00", unit_cost="12.30")
        result = vision.validate_extraction(candidate)
        self.assertEqual(result["service_items"][0]["unit_price"], "0.00")
        candidate["services"][0]["kind"] = []
        with self.assertRaises(ValidationError):
            vision.validate_extraction(candidate)

    def test_requires_completion_rejects_tools_errors_and_duplicate_json_keys(self):
        for events in [[], [{"type": "turn.failed"}], [{"type": "error"}, {"type": "turn.completed"}],
                       [{"type": "item.completed", "item": {"type": "command_execution"}}, {"type": "turn.completed"}],
                       [{"type": "item.completed", "item": {"type": "mcp_tool_call"}}]]:
            with self.subTest(events=events), self.assertRaises(ValidationError):
                vision._events("\n".join(json.dumps(event) for event in events))
        with self.assertRaises(ValidationError):
            vision._strict_json('{"services":[],"services":[]}')
        with self.assertRaises(ValidationError):
            vision._events('{"type":"turn.completed","model":"different-model"}', expected_model="gpt-6-luna")
        result = vision._events('diagnostic without JSON\n{"type":"turn.completed","usage":{"input_tokens":4,"secret":"omit"}}')
        self.assertEqual(result["usage"], {"input_tokens": 4})

    def test_only_exact_nonfatal_skill_budget_warning_is_recorded_after_completion(self):
        warning = "Exceeded skills context budget. All skill descriptions were removed and 261 additional skills were not included in the model-visible skills list."
        event = {"type": "item.completed", "item": {"id": "item_0", "type": "error", "message": warning}}
        line = json.dumps(event)
        result = vision._events(line + '\n{"type":"turn.completed"}')
        self.assertEqual(result["cli_warnings"], [warning])
        self.assertTrue(result["completion_observed"])
        with self.assertRaises(ValidationError):
            vision._events(line)
        for message in ["prefix " + warning, warning + " Provider failed.", warning.replace("261", "10001"),
                        warning.replace("261", "999999"), "Authentication failed", "Under-development features enabled: skip_host_skill_discovery"]:
            event["item"]["message"] = message
            with self.subTest(message=message), self.assertRaises(ValidationError):
                vision._events(json.dumps(event) + '\n{"type":"turn.completed"}')
        with self.assertRaises(ValidationError):
            vision._events(json.dumps({"type": "error", "message": warning}) + '\n{"type":"turn.completed"}')

    @patch.object(vision, "_resolve_codex_binary", return_value="codex.exe")
    @patch.object(vision.subprocess, "run")
    def test_availability_requires_successful_login_and_never_exposes_output(self, run, resolve):
        run.return_value = SimpleNamespace(returncode=1, stdout="private-token", stderr="private-token")
        result = vision.provider_status()
        self.assertFalse(result["available"])
        self.assertNotIn("private-token", str(result))
        self.assertEqual(run.call_args.args[0], ["codex.exe", "login", "status"])
        run.return_value.returncode = 0
        self.assertTrue(vision.provider_status()["available"])
        run.reset_mock()
        self.assertFalse(vision.provider_status("opencode")["available"])
        run.assert_not_called()

    @patch.object(vision, "_resolve_codex_binary", return_value="codex.exe")
    @patch.object(vision, "_native_subprocess_env", return_value={"TEST": "isolated"})
    def test_protocol_attaches_normalized_image_and_accepts_valid_output(self, env, resolve):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.png"
            Image.new("RGB", (30, 40), "white").save(source)
            seen = {}

            def fake_cli(command, **kwargs):
                image = Path(command[command.index("--image") + 1])
                output = Path(command[command.index("--output-last-message") + 1])
                schema = json.loads(Path(command[command.index("--output-schema") + 1]).read_text())
                self.assertTrue(image.is_file())
                self.assertEqual(Image.open(image).format, "JPEG")
                self.assertEqual(set(schema["required"]), set(extraction()))
                self.assertFalse(schema["additionalProperties"])
                self.assertEqual(kwargs["timeout"], 90)
                self.assertFalse(kwargs["shell"])
                self.assertEqual(kwargs["env"], {"TEST": "isolated"})
                self.assertIn("--ignore-user-config", command)
                self.assertIn("--ephemeral", command)
                self.assertNotIn("skip_host_skill_discovery", command)
                self.assertEqual(command[command.index("--sandbox") + 1], "read-only")
                self.assertEqual(command[command.index("--model") + 1], "gpt-6-luna")
                for feature in vision.DISABLED_FEATURES:
                    self.assertEqual(command[command.index(feature) - 1], "--disable")
                seen["folder"] = image.parent
                output.write_text(json.dumps(extraction()), encoding="utf-8")
                return SimpleNamespace(returncode=0, stdout='{"type":"turn.completed","usage":{"input_tokens":8}}', stderr="private diagnostic")

            with patch.object(vision.subprocess, "run", side_effect=fake_cli):
                result = vision.extract_photo(source)
            self.assertTrue(result["receipt"]["completion_observed"])
            self.assertEqual(result["receipt"]["provider"], "codex")
            self.assertNotIn("private diagnostic", str(result))
            self.assertFalse(seen["folder"].exists())

    @patch.object(vision, "_resolve_codex_binary", return_value="codex.exe")
    def test_failures_do_not_fallback_retry_or_return_accepted_output(self, resolve):
        with tempfile.TemporaryDirectory() as folder:
            source = Path(folder) / "source.png"
            Image.new("RGB", (20, 20), "white").save(source)
            for result in [SimpleNamespace(returncode=1, stdout="", stderr="secret"),
                           SimpleNamespace(returncode=0, stdout='{"type":"turn.completed"}', stderr="")]:
                with patch.object(vision.subprocess, "run", return_value=result) as run:
                    with self.assertRaises(ValidationError):
                        vision.extract_photo(source)
                    self.assertEqual(run.call_count, 1)
            with patch.object(vision.subprocess, "run", side_effect=subprocess.TimeoutExpired("codex", 90)) as run:
                with self.assertRaisesMessage(ValidationError, "90 segundos"):
                    vision.extract_photo(source)
                self.assertEqual(run.call_count, 1)
            with patch.object(vision.subprocess, "run") as run:
                with self.assertRaises(ValidationError):
                    vision.extract_photo(source, provider="opencode")
                with self.assertRaises(ValidationError):
                    vision.extract_photo(source, model="unverified-model")
                run.assert_not_called()
