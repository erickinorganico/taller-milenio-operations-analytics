import importlib.util
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('infra_doctor', ROOT/'scripts/infra_doctor.py')
doctor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(doctor)


class InfrastructureTests(unittest.TestCase):
    def config(self, **changes):
        return {'schema_version':1,'role':'client','instance_id':'synthetic-instance',
                'expected_hostname':doctor.platform.node(),'central_url':'https://crm.example.test',
                'expected_release_sha':'a'*40,'data_dir':None,'backup_dir':None,
                'mail_worker_allowed':False, **changes}

    def test_client_config_valid_does_not_attest_runtime(self):
        result = doctor.diagnose(self.config())
        self.assertTrue(result['configuration_checks_passed'])
        self.assertFalse(result['operational_readiness_verified'])

    def test_wrong_host(self):
        self.assertIn('wrong_machine',doctor.configuration_issues(self.config(expected_hostname='another-host')))

    def test_client_cannot_run_worker(self):
        self.assertIn('client_cannot_host_live_data_or_worker',doctor.configuration_issues(self.config(mail_worker_allowed=True)))

    def test_client_cannot_inspect_database(self):
        with patch.object(doctor,'inspect_database') as inspect:
            result = doctor.diagnose(self.config(),local_db=True)
        inspect.assert_not_called()
        self.assertIn('local_database_inspection_refused',result['issues'])

    def test_invalid_and_credential_urls_never_probed(self):
        for url in ['http://crm.example.test','https://user:secret@crm.example.test','https://crm.example.test/?token=x','https://crm.example.test/#secret','https://crm.example.test:bad']:
            with self.subTest(url=url),patch.object(doctor,'probe') as probe:
                doctor.diagnose(self.config(central_url=url),network=True)
                probe.assert_not_called()

    def test_no_network_by_default(self):
        with patch.object(doctor,'probe') as probe:
            doctor.diagnose(self.config())
            probe.assert_not_called()

    def test_missing_database_never_created(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertFalse(doctor.inspect_database(folder)['available'])
            self.assertFalse((Path(folder)/'workshop.sqlite3').exists())

    def test_only_aggregate_database_data_returned_without_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            db = Path(folder)/'workshop.sqlite3'
            with closing(sqlite3.connect(db)) as conn:
                conn.execute('CREATE TABLE commercial_mailmessage(status TEXT, body TEXT)')
                conn.execute("INSERT INTO commercial_mailmessage VALUES ('queued','PRIVATE-BODY')")
                conn.commit()
            before = db.read_bytes()
            result = doctor.inspect_database(folder)
            self.assertEqual(result['mail_status_counts'],{'queued':1})
            self.assertNotIn('PRIVATE-BODY',json.dumps(result))
            self.assertEqual(before,db.read_bytes())

    def test_templates_are_unassigned_not_production_ready(self):
        for name in ['host.example.json','client.example.json']:
            self.assertTrue(doctor.configuration_issues(json.loads((ROOT/'infra'/name).read_text())))

    def test_backup_inside_data_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            issues = doctor.configuration_issues(self.config(role='server',data_dir=folder,backup_dir=str(Path(folder)/'backups')))
            self.assertIn('backup_inside_data_directory',issues)

    def test_no_redirect_following(self):
        self.assertIsNone(doctor.NoRedirect().redirect_request(None,None,302,'redirect',{},'https://other.example.test'))

    def test_unreachable_probe_never_reports_ready(self):
        with patch.object(doctor,'probe',return_value={'reachable':False,'reason':'TimeoutError'}):
            result = doctor.diagnose(self.config(),network=True)
        self.assertFalse(result['configuration_checks_passed'])

    def test_missing_config_exit_two(self):
        with tempfile.TemporaryDirectory() as folder,patch('builtins.print'):
            self.assertEqual(doctor.main(['--config',str(Path(folder)/'absent.json')]),2)

    def test_readme_relative_links_exist(self):
        import re
        for path in [ROOT/'AGENTS.md',*ROOT.glob('infra/*.md')]:
            for link in re.findall(r'\]\(([^)]+)\)',path.read_text(encoding='utf-8')):
                if not link.startswith(('https://','http://','#')):
                    self.assertTrue((path.parent/link.split('#')[0]).exists(),f'{path}: {link}')


if __name__ == '__main__': unittest.main()
