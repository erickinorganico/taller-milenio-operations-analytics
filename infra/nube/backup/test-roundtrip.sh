#!/usr/bin/env bash
# Integration test for a disposable Linux runner. No cloud account or network endpoint.
set -euo pipefail
if [[ $EUID -ne 0 || ${MILENIO_DISPOSABLE_LINUX_RUNNER:-} != 1 ]]; then
  echo "Sólo en un runner Linux desechable: sudo env MILENIO_DISPOSABLE_LINUX_RUNNER=1 bash $0" >&2
  exit 2
fi
base=$(cd "$(dirname "$0")/.." && pwd)
python3 -B "$base/backup/test_maintenance.py"
fixture=$(mktemp -d /tmp/milenio-backup-test.XXXXXXXX)
export COMPOSE_PROJECT_NAME="backup-test-${fixture##*.}"
COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME,,}
export MILENIO_NUBE_ENV="$fixture/nube.env" MILENIO_BACKUP_ENV="$fixture/backup.env" MILENIO_BACKUP_LOCAL_TEST=1
export MILENIO_BUILD_REVISION
MILENIO_BUILD_REVISION=$(git -C "$base" rev-parse HEAD)
# An independent state directory, project name, private bucket substitute and disposable keys.
state="$fixture/state"
install -d -m 700 -o 10001 -g 10001 "$state/app" "$state/socket"
umask 077
printf 'MILENIO_STATE_DIR=%s\nMILENIO_CLOUD_HOST=example.invalid\n' "$state" >"$MILENIO_NUBE_ENV"
printf 'RESTIC_REPOSITORY=%s\nRESTIC_PASSWORD_FILE=%s\n' "$fixture/repo" "$fixture/key" >"$MILENIO_BACKUP_ENV"
openssl rand -hex 32 >"$fixture/key"
compose=(docker compose --env-file "$MILENIO_NUBE_ENV" -f "$base/compose.yaml")
bk=(bash "$base/backup/backup.sh")
cleanup() {
  "${compose[@]}" down --remove-orphans --timeout 20 || true
  if [[ "$fixture" == /tmp/milenio-backup-test.* && ! -L "$fixture" ]]; then rm -rf -- "$fixture"; fi
}
trap cleanup EXIT
if ! docker image inspect "milenio-taller:$MILENIO_BUILD_REVISION" >/dev/null 2>&1; then
  "${compose[@]}" build app
fi
"${compose[@]}" run --rm --no-deps -T app python manage.py migrate --noinput
"${compose[@]}" run --rm --no-deps -T app python manage.py shell -c "from django.contrib.auth import get_user_model; from django.contrib.sessions.models import Session; from django.conf import settings; from django.utils.timezone import now; from datetime import timedelta; get_user_model().objects.create_superuser('gerencia-ensayo', password='fake-only-4935'); Session.objects.create(session_key='synthetic',session_data='x',expire_date=now()+timedelta(days=1)); settings.MEDIA_ROOT.mkdir(exist_ok=True); (settings.MEDIA_ROOT/'evidencia.txt').write_text('evidencia de prueba')"
"${compose[@]}" up -d --wait --wait-timeout 120 app analytics capture
"${compose[@]}" stop capture
"${bk[@]}" init
"${bk[@]}" run
snapshot=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["snapshot"])' "$state/ultimo-respaldo.json")
mapfile -t actual < <("${compose[@]}" ps --status running --services | sort)
[[ ${actual[*]} == "analytics app" ]]
if "${bk[@]}" pre-upgrade 2>/dev/null; then echo 'Faltó comprobar el bloqueo' >&2; exit 1; fi
exec 9>>/run/lock/milenio-cloud.lock
flock -x 9
if "${bk[@]}" pre-upgrade 2>/dev/null; then echo 'Faltó detectar escritores' >&2; exit 1; fi
"${compose[@]}" stop app analytics
"${bk[@]}" pre-upgrade
flock -u 9
exec 9>&-
"${bk[@]}" restore-test "$snapshot"
if "${bk[@]}" restore-new "$snapshot" 2>/dev/null; then echo 'Destino ocupado aceptado' >&2; exit 1; fi
"${bk[@]}" check
"${bk[@]}" retention
"${compose[@]}" down
replacement="$fixture/nuevo"
install -d -m 700 "$replacement"
printf 'MILENIO_STATE_DIR=%s\nMILENIO_CLOUD_HOST=example.invalid\n' "$replacement" >"$MILENIO_NUBE_ENV"
"${bk[@]}" restore-new "$snapshot"
python3 - "$state" "$replacement" <<'PY'
import pathlib, sqlite3, sys
old, new = [pathlib.Path(p) / 'app' for p in sys.argv[1:]]
with sqlite3.connect(new/'workshop.sqlite3') as restored:
    assert restored.execute("select count(*) from auth_user where username='gerencia-ensayo'").fetchone()[0] == 1
    assert restored.execute("select count(*) from django_session").fetchone()[0] == 0
with sqlite3.connect(old/'workshop.sqlite3') as original:
    assert original.execute("select count(*) from django_session").fetchone()[0] == 1
assert (new/'media/evidencia.txt').read_text() == 'evidencia de prueba'
assert (new/'.secret_key').read_bytes() != (old/'.secret_key').read_bytes()
assert (new/'.mail-recovery-hold').is_file()
PY
echo "PASS: respaldo restic cifrado, escritores preservados y recuperación limpia sin tocar el origen."
