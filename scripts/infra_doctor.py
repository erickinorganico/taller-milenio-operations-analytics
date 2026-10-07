"""Read-only Milenio inventory checks. No Django import, credential reads or writes."""
import argparse
import json
import platform
import re
import sqlite3
import subprocess
from contextlib import closing
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

ROOT = Path(__file__).resolve().parents[1]


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def configuration_issues(config, hostname=None):
    issues = []
    if config.get('schema_version') != 1: issues.append('unsupported_config_version')
    role = config.get('role')
    if role not in ('server', 'client', 'development'): issues.append('role_unassigned')
    if not config.get('instance_id'): issues.append('instance_not_assigned')
    if not config.get('expected_hostname'): issues.append('hostname_not_assigned')
    elif str(config['expected_hostname']).casefold() != (hostname or platform.node()).casefold():
        issues.append('wrong_machine')
    release = config.get('expected_release_sha')
    if not isinstance(release, str) or not re.fullmatch('[0-9a-f]{40}', release): issues.append('release_not_assigned')
    url = config.get('central_url')
    try:
        parsed = urlsplit(url or '')
        if (parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password
                or parsed.query or parsed.fragment or parsed.path not in ('', '/')):
            issues.append('central_https_url_missing_or_invalid')
        _ = parsed.port
    except (ValueError, TypeError): issues.append('central_https_url_missing_or_invalid')
    if role == 'client' and (config.get('data_dir') or config.get('mail_worker_allowed')):
        issues.append('client_cannot_host_live_data_or_worker')
    if role == 'server':
        if not config.get('data_dir'): issues.append('server_data_dir_missing')
        if not config.get('backup_dir'): issues.append('backup_destination_missing')
        if config.get('data_dir') and config.get('backup_dir'):
            data, backup = Path(config['data_dir']).resolve(), Path(config['backup_dir']).resolve()
            if data == backup or backup.is_relative_to(data): issues.append('backup_inside_data_directory')
    return sorted(set(issues))


def git_state(root=ROOT):
    def run(*args):
        return subprocess.run(['git', '-C', str(root), *args], capture_output=True, text=True, timeout=10, check=True).stdout.strip()
    try:
        return {'checkout_sha':run('rev-parse','HEAD'), 'dirty':bool(run('status','--porcelain')), 'available':True}
    except (OSError, subprocess.SubprocessError):
        return {'available':False}


def probe(url):
    # No secrets or cookies are attached; OS trust store remains enabled.
    try:
        request = Request(url.rstrip('/')+'/health/', headers={'Accept':'application/json'})
        with build_opener(NoRedirect()).open(request, timeout=5) as response:
            body = response.read(65537)
            if len(body) > 65536: return {'reachable':False, 'reason':'oversized_response'}
            data = json.loads(body)
        matched = data.get('application') == 'milenio-operations' and data.get('mode') == 'live' and data.get('status') == 'ok'
        return {'reachable':True, 'application_and_mode_match':matched,
                'persistent_instance_verified':False, 'deployed_release_verified':False,
                'note':'Current health endpoint does not attest persistent identity, release or mail worker.'}
    except Exception as exc:
        return {'reachable':False, 'reason':type(exc).__name__}


def inspect_database(data_dir):
    path = Path(data_dir).resolve()/'workshop.sqlite3'
    if not path.is_file(): return {'available':False, 'reason':'database_missing'}
    try:
        with closing(sqlite3.connect(path.as_uri()+'?mode=ro', uri=True, timeout=2)) as conn:
            conn.execute('PRAGMA query_only=ON')
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            result = {'available':True, 'commercial_schema_present':'commercial_mailmessage' in tables}
            if 'django_migrations' in tables:
                result['commercial_migrations'] = [r[0] for r in conn.execute("SELECT name FROM django_migrations WHERE app='commercial' ORDER BY name")]
            if 'commercial_mailmessage' in tables:
                result['mail_status_counts'] = dict(conn.execute('SELECT status, COUNT(*) FROM commercial_mailmessage GROUP BY status'))
            if 'commercial_mailbox' in tables:
                row = conn.execute('SELECT connected,enabled,last_sync,last_tick FROM commercial_mailbox WHERE id=1').fetchone()
                result['mailbox'] = dict(zip(('connected','enabled','last_sync','last_tick'),row)) if row else None
            return result
    except sqlite3.Error as exc:
        return {'available':False, 'reason':type(exc).__name__}


def diagnose(config, network=False, local_db=False):
    issues = configuration_issues(config)
    result = {'mode':'read_only', 'role':config.get('role','unassigned'), 'issues':issues,
              'git':git_state(), 'operational_readiness_verified':False}
    if (config.get('role') == 'server' and config.get('expected_release_sha') and result['git'].get('checkout_sha')
            and config['expected_release_sha'] != result['git']['checkout_sha']):
        issues.append('server_checkout_differs_from_expected_release')
    if network:
        if 'central_https_url_missing_or_invalid' in issues:
            result['network'] = {'skipped':True, 'reason':'invalid_url'}
        else:
            result['network'] = probe(config['central_url'])
            if not result['network'].get('reachable') or not result['network'].get('application_and_mode_match'):
                issues.append('central_health_not_confirmed')
    if local_db:
        allowed = config.get('role') == 'server' and not set(issues).intersection({'wrong_machine','hostname_not_assigned','server_data_dir_missing','instance_not_assigned'})
        if allowed:
            result['database'] = inspect_database(config['data_dir'])
            if not result['database']['available']: issues.append('database_not_readable')
        else:
            result['database'] = {'skipped':True, 'reason':'not_verified_server'}
            issues.append('local_database_inspection_refused')
    result['configuration_checks_passed'] = not issues
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=ROOT/'private/infra.local.json')
    parser.add_argument('--probe', action='store_true', help='Contact only the configured central HTTPS health endpoint')
    parser.add_argument('--inspect-local-db', action='store_true', help='Read aggregate status on the assigned server only')
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text(encoding='utf-8-sig'))
        if not isinstance(config,dict): raise ValueError('Expected object')
        result = diagnose(config,args.probe,args.inspect_local_db)
    except (OSError, ValueError, TypeError):
        result = {'mode':'read_only','configuration_checks_passed':False,'operational_readiness_verified':False,
                  'issues':['configuration_missing_or_invalid']}
    print(json.dumps(result,ensure_ascii=False,indent=2))
    return 0 if result['configuration_checks_passed'] else 2


if __name__ == '__main__':
    raise SystemExit(main())
