#!/usr/bin/env bash
# Run ONLY inside a fresh Linux test container, as root, with this directory mounted read-only at /fixture.
# Exercises the operator script with a simulated Docker CLI, including failure/retry around a migration.
set -Eeuo pipefail
[[ $EUID == 0 && -f /.dockerenv && ${MILENIO_TEST_DEPLOY:-} == isolated &&
   -f /fixture/deploy.sh && ! -e /etc/milenio && ! -e /var/lib/milenio-cloud && ! -S /var/run/docker.sock ]] || exit 2
dst=/tmp/operator-fixture
mkdir -p "$dst/repo/infra/nube/backup" "$dst/bin"
cp /fixture/deploy.sh "$dst/repo/infra/nube/"
cd "$dst/repo"
export PATH="$dst/bin:$PATH" TEST_LOG="$dst/commands"
export TEST_REVISION=1111111111111111111111111111111111111111
cat > "$dst/bin/git" <<'GIT'
#!/bin/sh
case " $* " in *" rev-parse "*) echo "$TEST_REVISION" ;; *" status "*) : ;; *) exit 9 ;; esac
GIT
cat > "$dst/bin/docker" <<'DOCKER'
#!/bin/bash
set -eu
printf '%s\n' "$*" >> "$TEST_LOG"
case "$1 $2" in
    'image inspect') if [[ $3 == -f ]]; then echo "$MILENIO_BUILD_REVISION"; fi; exit 0 ;;
esac
[[ $1 == compose ]] || exit 7
shift 7
case "$1" in
    config|pull|build|exec) ;;
    ps) if [[ -e /tmp/operator-fixture/running ]]; then echo simulated; fi ;;
    stop) rm -f -- /tmp/operator-fixture/running ;;
    start|up) touch /tmp/operator-fixture/running ;;
    run)
        if [[ " $* " == *" migrate --noinput "* ]]; then
            if [[ ${TEST_FAIL_MIGRATE:-} == yes ]]; then exit 33; fi
            printf 'fake SQLite fixture\n' > /var/lib/milenio-cloud/app/workshop.sqlite3
        fi ;;
    *) exit 8 ;;
esac
DOCKER
cat > "$dst/repo/infra/nube/backup/backup.sh" <<'BACKUP'
#!/bin/bash
set -eu
[[ $1 == pre-upgrade && /proc/$$/fd/9 -ef /run/lock/milenio-cloud.lock && ! -e /tmp/operator-fixture/running ]]
flock -n 9
echo 'pre-upgrade' >> "$TEST_LOG"
[[ ${TEST_FAIL_BACKUP:-} != yes ]]
BACKUP
chmod 700 "$dst/bin/"*
run() { bash "$dst/repo/infra/nube/deploy.sh" "$@"; }
reject() { if run "$@"; then echo "Debió rechazar $*" >&2; exit 8; fi; }
state=/var/lib/milenio-cloud
reject init 'bad.example/other'
run init taller.example.test
run init taller.example.test
reject init otro.example.test
[[ $(stat -c '%a' /etc/milenio/nube.env) == 600 && $(stat -c '%u:%g:%a' "$state/socket") == 10001:10001:750 ]]
run apply
run apply
reject import-windows /tmp/fixture aa bb
[[ $(grep -c 'migrate --noinput' "$TEST_LOG") == 1 ]]
export TEST_REVISION=2222222222222222222222222222222222222222 TEST_FAIL_BACKUP=yes
reject apply
[[ -e "$dst/running" && ! -e $state/.pending-release ]]
unset TEST_FAIL_BACKUP
export TEST_FAIL_MIGRATE=yes
reject apply
[[ ! -e "$dst/running" && $(cat "$state/.pending-release") == "$TEST_REVISION" ]]
unset TEST_FAIL_MIGRATE
run apply
[[ ! -e $state/.pending-release && -e "$dst/running" && $(grep -c '^pre-upgrade$' "$TEST_LOG") == 2 ]]
mv "$state/app/workshop.sqlite3" "$state/app/fixture-copy"
reject apply
mv "$state/app/fixture-copy" "$state/app/workshop.sqlite3"
sed -i 's/^MILENIO_BUILD_REVISION=.*/MILENIO_BUILD_REVISION=uninstalled/' /etc/milenio/nube.env
reject apply
reject activate-restored
receipt="$state/ultima-restauracion.json"
printf '{"snapshot":"%064d","revision":"incorrecta","completed_unix":1}\n' 0 > "$receipt"
chmod 600 "$receipt"
reject activate-restored
printf '{"snapshot":"%064d","revision":"%s","completed_unix":1}\n' 0 "$TEST_REVISION" > "$receipt"
before=$(grep -c 'migrate --noinput' "$TEST_LOG")
run activate-restored
[[ $(grep -c 'migrate --noinput' "$TEST_LOG") == "$before" && -e "$dst/running" ]]
sed -i 's/^MILENIO_BUILD_REVISION=.*/MILENIO_BUILD_REVISION=uninstalled/' /etc/milenio/nube.env
mv "$receipt" "$dst/restic-fixture.json"
printf '{"kind":"windows-portable","source_manifest_sha256":"%064d","source_release_reported":"%064d","business":{},"revision":"%s","completed_unix":1}\n' 0 0 "$TEST_REVISION" > "$state/ultima-importacion-windows.json"
chmod 600 "$state/ultima-importacion-windows.json"
run activate-restored
[[ $(grep -c 'migrate --noinput' "$TEST_LOG") == "$before" ]]
printf 'PASS: inicialización, revisión repetida, respaldo fallido, migración fallida, recuperación, base ausente y activación del respaldo compatible.\n'
