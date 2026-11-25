"""Local Linux failure-path checks; no provider, containers or production data."""
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import backup


class RecoverySafety(unittest.TestCase):
    def test_image_label_after_compose_down_must_match_recorded_active_release(self):
        installed, candidate = "a" * 40, "b" * 40
        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "nube.env"
            config.write_text("MILENIO_BUILD_REVISION=" + installed + "\n")
            cloud = object.__new__(backup.Cloud)
            cloud.env_file = config
            cloud.image = "milenio-taller:" + installed
            with patch.object(backup, "private_file", return_value=config), patch.object(backup, "output") as inspect:
                inspect.return_value = installed
                self.assertEqual(cloud.installed_revision(), installed)
                self.assertEqual(inspect.call_args.args[0][-1], cloud.image)
                inspect.return_value = candidate
                with self.assertRaisesRegex(ValueError, "no coincide"):
                    cloud.installed_revision()
                config.write_text("MILENIO_BUILD_REVISION=uninstalled\n")
                with self.assertRaisesRegex(ValueError, "Falta una revisión"):
                    cloud.installed_revision()

    def test_partial_migration_cannot_replace_last_good_backup(self):
        with tempfile.TemporaryDirectory() as folder:
            cloud, repo = Mock(), Mock()
            cloud.state = Path(folder)
            (cloud.state / ".pending-release").touch()
            with self.assertRaisesRegex(ValueError, "migración"):
                backup.create(cloud, repo, cloud.state)
            repo.snapshots.assert_not_called()
            cloud.writers.assert_not_called()

    def test_insufficient_space_preserves_online_writers(self):
        with tempfile.TemporaryDirectory() as folder:
            cloud, repo = Mock(), Mock()
            cloud.state = cloud.data = Path(folder)
            (cloud.data / "workshop.sqlite3").write_bytes(b"synthetic")
            disk = Mock(f_bavail=1, f_blocks=100000, f_frsize=4096)
            with patch.object(backup.os, "statvfs", return_value=disk), patch.object(backup, "run") as call:
                with self.assertRaisesRegex(ValueError, "Espacio insuficiente"):
                    backup.create(cloud, repo, cloud.state)
            call.assert_not_called()
            cloud.resume.assert_not_called()
            repo.save.assert_not_called()

    def test_restore_checks_space_for_both_copies_before_downloading(self):
        with tempfile.TemporaryDirectory() as folder:
            cloud, repo = Mock(), Mock()
            cloud.state = Path(folder)
            cloud.data = cloud.state / "app"
            cloud.revision.return_value = "b" * 40
            repo.select.return_value = {"id": "a" * 64, "tags": ["git-" + "b" * 40]}
            mib = 1024**2
            disk = Mock(f_bavail=700, f_blocks=2000, f_frsize=mib)
            with patch.object(backup.os, "statvfs", return_value=disk), patch.object(backup, "run") as call, \
                 patch.object(backup, "output", return_value='{"total_size":104857600,"total_file_count":5}'):
                with self.assertRaisesRegex(ValueError, "Espacio insuficiente"):
                    backup.recover(cloud, repo, cloud.state, "latest", False)
            call.assert_not_called()
            self.assertFalse((cloud.state / "download").exists())

    def test_blocked_without_quiescing_unknown_writer(self):
        with tempfile.TemporaryDirectory() as folder:
            cloud = Mock()
            cloud.state = Path(folder)
            cloud.writers.return_value = ["analytics"]
            with self.assertRaisesRegex(ValueError, "Detener"):
                backup.create(cloud, Mock(), cloud.state, before_upgrade=True)
            cloud.job.assert_not_called()

    def test_worker_states_recovered_when_staging_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            stage = Path(directory)
            (stage / "workshop.sqlite3").touch()
            cloud = Mock()
            cloud.state = cloud.data = stage
            cloud.compose = ["docker", "compose"]
            cloud.writers.side_effect = [["app", "capture"], []]
            cloud.job.side_effect = ValueError("simulated snapshot failure")
            repo = Mock()
            with patch.object(backup, "require_capacity"), patch.object(backup.os, "chown"), patch.object(backup, "run") as stop:
                with self.assertRaisesRegex(ValueError, "simulated"):
                    backup.create(cloud, repo, stage)
                stop.assert_called_once_with(["docker", "compose", "stop", "-t", "90", "app", "capture"])
            cloud.resume.assert_called_once_with(["app", "capture"])
            repo.save.assert_not_called()

    def test_restore_refuses_occupied_destination_and_implicit_latest(self):
        with tempfile.TemporaryDirectory() as directory:
            cloud = Mock()
            cloud.data = Path(directory)
            cloud.state = Path(directory)
            (cloud.data / "existing").touch()
            for snapshot in ("latest", "a" * 64):
                with self.assertRaisesRegex(ValueError, "destino|vacío"):
                    backup.recover(cloud, Mock(), Path("/unused"), snapshot, True)
            cloud.job.assert_not_called()

    def test_recovery_replays_only_its_own_promoted_directory(self):
        if os.geteuid() != 0:
            self.skipTest("El recibo de recuperación pertenece a root")
        with tempfile.TemporaryDirectory() as folder:
            cloud = Mock()
            cloud.state = Path(folder)
            cloud.data = cloud.state / "app"
            cloud.data.mkdir()
            (cloud.data / "workshop.sqlite3").touch()
            ident = cloud.data.stat()
            cloud.writers.return_value = []
            cloud.revision.return_value = "b" * 40
            snapshot = "a" * 64
            backup.receipt(cloud.state, ".restic-promocion", {"snapshot": snapshot, "revision": "b" * 40,
                           "directory": [ident.st_dev, ident.st_ino], "completed_unix": 1})
            backup.recover(cloud, Mock(), Path("/unused"), snapshot, True)
            self.assertTrue((cloud.state / "ultima-restauracion.json").is_file())
            self.assertFalse((cloud.state / ".restic-promocion.json").exists())
            cloud.job.assert_not_called()

    def test_second_lock_holder_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "central.lock"
            with backup.exclusive_lock(path):
                with self.assertRaises(BlockingIOError):
                    with backup.exclusive_lock(path):
                        self.fail("bloqueo duplicado")

    def test_offsite_is_required_outside_explicit_fixture(self):
        if os.geteuid() != 0:
            self.skipTest("Comprobación del propietario root de configuración y contraseña")
        with tempfile.TemporaryDirectory() as folder:
            config, key = Path(folder) / "backup.env", Path(folder) / "password"
            key.write_text("synthetic-fixture")
            config.write_text(f"RESTIC_REPOSITORY={folder}/repo\nRESTIC_PASSWORD_FILE={key}\n")
            key.chmod(0o600)
            config.chmod(0o600)
            with self.assertRaisesRegex(ValueError, "bucket B2"):
                backup.restic_environment(config)
            self.assertEqual(backup.restic_environment(config, True)["RESTIC_PASSWORD_FILE"], str(key))
            key.chmod(0o644)
            with self.assertRaisesRegex(ValueError, "permisos"):
                backup.restic_environment(config, True)


if __name__ == "__main__":
    unittest.main()
