#!/usr/bin/env bash
# Execute on the selected Linux host. See infra/nube/README.md.
set -Eeuo pipefail
umask 077
fail() { printf '%s\n' "$*" >&2; exit 1; }
usage() { fail "Uso: deploy.sh init DOMINIO | apply | import-windows CARPETA SHA256_MANIFIESTO RELEASE_WINDOWS | activate-restored | manager USUARIO | status | verify-url"; }
[[ $EUID == 0 ]] || fail "Ejecuta con sudo en el servidor que elegiste."
action=${1:-}
case "$action:$#" in init:2|apply:1|import-windows:4|activate-restored:1|manager:2|status:1|verify-url:1) ;; *) usage ;; esac
here=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)
repo=$(cd "$here/../.." && pwd -P)
config=/etc/milenio/nube.env
state=/var/lib/milenio-cloud
pending_file=$state/.pending-release
lock=/run/lock/milenio-cloud.lock

valid_host() {
    local host=$1 label
    local -a labels
    [[ ${#host} -le 253 && $host == *.* && $host != *. && $host != *..* && $host != *[^a-z0-9.-]* ]] || return 1
    [[ ! $host =~ ^[0-9.]+$ ]] || return 1
    IFS=. read -r -a labels <<< "$host"
    for label in "${labels[@]}"; do
        [[ $label =~ ^[a-z0-9]([a-z0-9-]{0,61}[a-z0-9])?$ ]] || return 1
    done
}

exec 9>>"$lock"
flock -x -w 60 9 || fail "Hay un respaldo o mantenimiento en curso. Espera a que termine."

write_config() {
    local temp
    temp=$(mktemp "${config}.XXXXXX")
    printf 'MILENIO_CLOUD_HOST=%s\nMILENIO_STATE_DIR=%s\nMILENIO_BUILD_REVISION=%s\n' "$MILENIO_CLOUD_HOST" "$state" "$1" >"$temp"
    mv -f -- "$temp" "$config"
}

if [[ $action == init ]]; then
    valid_host "$2" || fail "Escribe un dominio DNS completo en minúsculas, sin puerto ni https://."
    if [[ ! -e $config && ! -L $config ]]; then
        [[ ! -e $state/app/workshop.sqlite3 && ! -e $pending_file ]] || fail "Ya existen datos sin la configuración de esta central. Recupera la configuración antes de continuar."
        install -d -m 0700 /etc/milenio
        MILENIO_CLOUD_HOST=$2
        write_config uninstalled
    fi
fi
[[ -f $config && ! -L $config && $(stat -c '%u:%a' "$config") == 0:600 ]] || fail "Falta $config con propietario root y modo 0600. Usa init para la primera instalación."
# Only literal values from this script's format are accepted. Never execute the configuration.
stored_host= stored_state= active_revision=
while IFS='=' read -r key value; do
    case "$key" in
        MILENIO_CLOUD_HOST) stored_host=$value ;;
        MILENIO_STATE_DIR) stored_state=$value ;;
        MILENIO_BUILD_REVISION) active_revision=$value ;;
        *) fail "Clave desconocida en $config." ;;
    esac
done <"$config"
valid_host "$stored_host" && [[ $stored_state == "$state" ]] || fail "Revisa el dominio y el almacenamiento en $config."
[[ $active_revision == uninstalled || $active_revision =~ ^[a-f0-9]{40}$ ]] || fail "Revisión guardada inválida."
export MILENIO_CLOUD_HOST=$stored_host MILENIO_STATE_DIR=$state MILENIO_BUILD_REVISION=$active_revision
dc() { docker compose --project-name milenio-nube --env-file "$config" -f "$here/compose.yaml" "$@"; }

if [[ $action == init ]]; then
    [[ $stored_host == "$2" ]] || fail "Esta central tiene otro dominio. Conserva su configuración."
    for directory in "$state" "$state/app" "$state/socket" "$state/caddy-data" "$state/caddy-config"; do
        [[ ! -L $directory ]] || fail "El almacenamiento permanente debe estar en disco local, sin enlaces simbólicos."
    done
    install -d -m 0700 "$state"
    install -d -m 0700 -o 10001 -g 10001 "$state/app"
    install -d -m 0750 -o 10001 -g 10001 "$state/socket"
    install -d -m 0700 -o 10002 -g 10001 "$state/caddy-data" "$state/caddy-config"
    printf 'Dominio %s preparado. Ejecuta apply desde la revisión elegida.\n' "$stored_host"
    exit 0
fi

if [[ $action == status ]]; then
    dc ps --all
    [[ ! -e $pending_file ]] || fail "Hay una migración pendiente. Revisa su respaldo y ejecuta apply con la misma revisión."
    for service in app analytics capture caddy; do
        [[ -n $(dc ps -q --status running "$service") ]] || fail "El servicio $service está detenido. Revisa su estado y sus registros."
    done
    dc exec -T app python scripts/cloud_app.py healthcheck
    exit
fi
if [[ $action == verify-url ]]; then
    # Use the public DNS path and OS trust store, as a phone would. Run after creating Gerencia.
    command -v curl >/dev/null || fail "Instala curl para comprobar HTTPS."
    code=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --max-time 20 "https://$stored_host/login/")
    [[ $code == 200 ]] || fail "El inicio de sesión público respondió $code. Comprueba DNS, certificado y la primera cuenta de Gerencia."
    code=$(curl --silent --show-error --output /dev/null --write-out '%{http_code}' --max-time 20 "https://$stored_host/setup/")
    [[ $code == 404 ]] || fail "Revisa el bloqueo de la ruta de alta inicial antes de abrir el acceso."
    printf 'DNS, certificado y acceso HTTPS verificados para %s.\n' "$stored_host"
    exit 0
fi
if [[ $action == manager ]]; then
    [[ ! -e $pending_file ]] || fail "Termina el mantenimiento en curso."
    [[ $2 != -* && -n $2 ]] || fail "Escribe el nombre de usuario."
    dc exec app python manage.py cloud_manager "$2"
    exit
fi

# Refuse to label an unreviewed source tree as a Git revision. Private state lives outside the checkout.
revision=$(git -C "$repo" rev-parse --verify 'HEAD^{commit}')
[[ $revision =~ ^[a-f0-9]{40}$ ]] || fail "Falta una revisión de Git válida."
[[ -z $(git -C "$repo" status --porcelain --untracked-files=all) ]] || fail "El checkout tiene cambios. Usa una copia limpia de la revisión que vas a instalar."
[[ -d $state/app && -d $state/socket && -d $state/caddy-data && -d $state/caddy-config ]] || fail "Ejecuta init antes de instalar."
if [[ $active_revision != uninstalled && ! -s $state/app/workshop.sqlite3 ]]; then
    fail "Falta la base de la central instalada. Recupera su respaldo antes de iniciar."
fi
if [[ $action == import-windows ]]; then
    [[ $active_revision == uninstalled && ! -e $pending_file && -d $state/app && -z $(ls -A "$state/app") ]] || fail "La importación requiere una central nueva y vacía. El origen y el destino se conservan."
    [[ -z $(dc ps -q --status running) ]] || fail "Hay servicios activos en el destino."
elif [[ $action == activate-restored ]]; then
    [[ $active_revision == uninstalled && ! -e $pending_file && -s $state/app/workshop.sqlite3 ]] || fail "La activación requiere una central nueva con la restauración ya terminada."
    receipt=$state/ultima-restauracion.json
    if [[ -f $state/ultima-importacion-windows.json ]]; then
        [[ ! -e $receipt ]] || fail "Existen dos fuentes de recuperación. Revisa el destino."
        receipt=$state/ultima-importacion-windows.json
    fi
    [[ -f $receipt && ! -L $receipt && $(stat -c '%u:%a' "$receipt") == 0:600 ]] || fail "Falta el recibo privado de recuperación o importación."
    python3 - "$receipt" "$revision" <<'PY' || fail "La restauración requiere la revisión exacta del respaldo y un recibo válido."
import json, re, sys
from pathlib import Path
path = Path(sys.argv[1])
receipt = json.loads(path.read_text())
if path.name == "ultima-importacion-windows.json":
    valid = (receipt.get("kind") == "windows-portable" and all(re.fullmatch(r"[a-f0-9]{64}", str(receipt.get(k, "")))
             for k in ("source_manifest_sha256", "source_release_reported")) and isinstance(receipt.get("business"), dict))
else:
    valid = re.fullmatch(r"[a-f0-9]{64}", str(receipt.get("snapshot", "")))
if (receipt.get("revision") != sys.argv[2] or not valid
        or not isinstance(receipt.get("completed_unix"), (int, float)) or receipt["completed_unix"] <= 0):
    sys.exit(1)
PY
elif [[ -f $pending_file ]]; then
    [[ $(cat "$pending_file") == "$revision" ]] || fail "Hay otro cambio incompleto. Retoma esa revisión o restaura código y datos juntos."
elif [[ $active_revision == uninstalled && -e $state/app/workshop.sqlite3 ]]; then
    fail "Se encontró una base ajena a una primera instalación. Usa el procedimiento de migración o recuperación."
fi
export MILENIO_BUILD_REVISION=$revision
dc config --quiet
image="milenio-taller:$revision"
if ! docker image inspect "$image" >/dev/null 2>&1; then dc build app; fi
image_revision=$(docker image inspect -f '{{ index .Config.Labels "org.opencontainers.image.revision" }}' "$image")
[[ $image_revision == "$revision" ]] || fail "La etiqueta de la imagen no coincide con la revisión."
if [[ $action == import-windows ]]; then
    python3 "$here/import_windows.py" install "$2" "$state" "${3,,}" "${4,,}" "$revision"
    exit
fi
dc pull caddy

if [[ $action == activate-restored ]]; then
    if ! dc run --rm --no-deps -T app python manage.py migrate --check ||
       ! dc run --rm --no-deps -T app python manage.py check --deploy --fail-level WARNING ||
       ! dc up -d --no-build --wait --wait-timeout 120 ||
       ! dc exec -T app python scripts/cloud_app.py healthcheck; then
        dc stop app analytics capture
        fail "La central restaurada sigue detenida. Revisa el esquema, el código y la disponibilidad."
    fi
    write_config "$revision"
    printf 'Respaldo recuperado con su revisión %s. Comprueba verify-url y una orden conocida.\n' "$revision"
    exit 0
fi
if [[ $active_revision == "$revision" && ! -e $pending_file ]]; then
    dc run --rm --no-deps -T app python manage.py migrate --check
    dc up -d --no-build --wait --wait-timeout 120
    dc exec -T app python scripts/cloud_app.py healthcheck
    printf 'Central verificada para %s.\n' "$revision"
    exit 0
fi
writers=(app analytics capture)
running_before=()
for writer in "${writers[@]}"; do
    if [[ -n $(dc ps -q --status running "$writer") ]]; then running_before+=("$writer"); fi
done
dc stop "${writers[@]}"
if [[ $active_revision != uninstalled && ! -e $pending_file ]]; then
    # The database still belongs to the installed release, including after compose down.
    if ! MILENIO_BUILD_REVISION="$active_revision" bash "$here/backup/backup.sh" pre-upgrade; then
        # No migration has occurred. Resume the exact old containers, not the candidate image.
        if (( ${#running_before[@]} )); then dc start "${running_before[@]}"; fi
        fail "El respaldo externo previo falló. Se conservó la versión anterior."
    fi
fi
pending_tmp=$(mktemp "${pending_file}.XXXXXX")
printf '%s\n' "$revision" >"$pending_tmp"
mv -f -- "$pending_tmp" "$pending_file"
# Once schema changes begin, never automatically start old code on a partially migrated database.
if ! dc run --rm --no-deps -T app python manage.py migrate --noinput ||
   ! dc run --rm --no-deps -T app python manage.py check --deploy --fail-level WARNING ||
   ! dc up -d --no-build --wait --wait-timeout 120 ||
   ! dc exec -T app python scripts/cloud_app.py healthcheck; then
    dc stop "${writers[@]}"
    fail "No se pudo verificar la nueva versión. El taller queda detenido. Corrige y repite apply con la misma revisión o restaura el respaldo compatible."
fi
write_config "$revision"
rm -- "$pending_file"
printf 'Versión %s verificada. Dirección del taller: https://%s\n' "$revision" "$stored_host"
