import getpass
import json
import os
import socket
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch
from milenio_web.deployment import guard_server,read_config
from scripts.deploy import initialize, wait_ready
from scripts.agent_client import NoRedirect


class DeploymentTests(unittest.TestCase):
    def setUp(self):
        self.temporary=tempfile.TemporaryDirectory();self.addCleanup(self.temporary.cleanup)
        self.root=Path(self.temporary.name)
        self.config=self.root/'private/infra.local.json'
        self.env=patch.dict(os.environ,{'MILENIO_DEPLOYMENT_CONFIG':str(self.config)})
        self.env.start();self.addCleanup(self.env.stop)
        self.saved_data=os.environ.pop('MILENIO_DATA_DIR',None)
        self.addCleanup(self.restore_data)

    def restore_data(self):
        if self.saved_data is not None:os.environ['MILENIO_DATA_DIR']=self.saved_data

    def values(self):
        return dict(schema_version=2,role='server',expected_hostname=socket.gethostname(),windows_user=getpass.getuser(),instance_id=str(uuid.uuid4()),data_dir=str(self.root/'live'))

    def test_missing_identity_never_creates_database(self):
        with self.assertRaises(RuntimeError):guard_server()
        self.assertFalse((self.root/'live').exists())

    def test_client_rejected(self):
        data=self.values();data['role']='client'
        with self.assertRaises(RuntimeError):guard_server(data)

    def test_copied_host_or_identity_rejected(self):
        for field in ('expected_hostname','windows_user'):
            data=self.values();data[field]='different'
            with self.assertRaises(RuntimeError):guard_server(data)

    def test_different_database_rejected(self):
        with patch.dict(os.environ,{'MILENIO_DATA_DIR':str(self.root/'other/live')}):
            with self.assertRaises(RuntimeError):guard_server(self.values())

    def test_onedrive_rejected(self):
        data=self.values();data['data_dir']=str(self.root/'OneDrive/live')
        with self.assertRaises(RuntimeError):guard_server(data)

    @patch('scripts.deploy.release_id',return_value='synthetic-sha')
    def test_init_idempotent_without_overwriting_identity(self,_):
        first=initialize(self.root/'live',self.root/'backups',8770)
        second=initialize(self.root/'live',self.root/'backups',8770)
        self.assertEqual(first,second)
        self.assertFalse(first['mail_worker_allowed'])
        self.assertFalse((self.root/'live/workshop.sqlite3').exists())

    def test_existing_data_never_adopted_silently(self):
        (self.root/'live').mkdir();(self.root/'live/important.txt').write_text('preserve')
        with self.assertRaises(RuntimeError):initialize(self.root/'live',self.root/'backups',8770)
        self.assertEqual((self.root/'live/important.txt').read_text(),'preserve')

    def test_overlapping_backup_rejected(self):
        with self.assertRaises(RuntimeError):initialize(self.root/'live',self.root/'live/backup',8770)

    def test_agent_never_follows_redirect_with_token(self):
        with self.assertRaises(ValueError):NoRedirect().redirect_request(None,None,302,None,None,None)

    def test_startup_accepts_only_the_installed_instance_and_release(self):
        config = {'central_url': 'http://127.0.0.1:8770', 'instance_id': 'fixture', 'release_id': 'build-a'}
        healthy = {'application_and_mode_match': True, 'reachable': True, 'supervisor_recent': True,
                   'instance_id': 'fixture', 'release_id': 'build-a'}
        with patch('scripts.infra_doctor.probe', return_value=healthy):
            wait_ready(config)
        for change in ({'instance_id': 'other'}, {'release_id': 'older'}, {'application_and_mode_match': False}):
            with self.subTest(change=change), patch('scripts.infra_doctor.probe', return_value={**healthy, **change}):
                with self.assertRaisesRegex(RuntimeError, 'otra instancia o version'):
                    wait_ready(config)
