import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import operacion


class HostChecks(unittest.TestCase):
    def test_both_host_listeners_and_docker_nat_count(self):
        listeners = "LISTEN 0 4096 0.0.0.0:22 0.0.0.0:*\nLISTEN 0 128 [::1]:9100 [::]:*"
        mapped = {"80/tcp": [{"HostIp": "0.0.0.0", "HostPort": "80"}],
                  "443/tcp": [{"HostIp": "::", "HostPort": "443"}]}

        def run(args):
            if args[0] == "ss":
                return listeners
            if args[:2] == ("docker", "inspect"):
                return json.dumps(mapped)
            self.assertEqual(args, ("docker", "ps", "-q"))
            return "12345"

        with patch.object(operacion, "ssh_options", return_value={"port": ["22"]}), \
             patch.object(operacion, "output", side_effect=lambda *args: run(args)):
            self.assertIn("previstos", operacion.ports())
            mapped["8000/tcp"] = [{"HostIp": "0.0.0.0", "HostPort": "8765"}]
            with self.assertRaisesRegex(ValueError, "8765/tcp"):
                operacion.ports()
            mapped.pop("8000/tcp")
            listeners += "\nLISTEN 0 128 [::]:2375 [::]:*"
            with self.assertRaisesRegex(ValueError, "2375/tcp"):
                operacion.ports()

    def test_aged_future_and_malformed_backup_receipts_fail(self):
        if os.geteuid() != 0:
            self.skipTest("Se requiere root para la configuración privada del ensayo")
        with tempfile.TemporaryDirectory() as directory, patch.object(operacion.time, "time", return_value=100000):
            path = Path(directory) / "receipt.json"
            valid = {"snapshot": "a" * 64, "revision": "b" * 40, "completed_unix": 99900}
            path.write_text(json.dumps(valid))
            path.chmod(0o600)
            self.assertIn("hace", operacion.latest_receipt(path, 26))
            for wrong in ({"completed_unix": 1}, {"completed_unix": 101000}, {"snapshot": "foo"}):
                path.write_text(json.dumps(valid | wrong))
                with self.assertRaises(ValueError):
                    operacion.latest_receipt(path, 26)

    def test_ssh_detects_password_or_keyboard_interactive_enabled(self):
        keys = {"port": ["22"], "passwordauthentication": ["no"], "kbdinteractiveauthentication": ["no"],
                "pubkeyauthentication": ["yes"], "permitrootlogin": ["prohibit-password"]}
        with patch.object(operacion, "ssh_options", return_value=keys):
            self.assertIn("llave", operacion.ssh_keys())
            keys["kbdinteractiveauthentication"] = ["yes"]
            with self.assertRaisesRegex(ValueError, "autenticación"):
                operacion.ssh_keys()


if __name__ == "__main__":
    unittest.main()
