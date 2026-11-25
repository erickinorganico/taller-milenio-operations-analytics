#!/usr/bin/env bash
# Prerequisites for the chosen fresh Ubuntu VPS. Does not configure DNS or firewall.
set -euo pipefail
if [[ $EUID != 0 || ! -f /etc/os-release || ! -d /run/systemd/system ]]; then
    echo 'Ejecuta con sudo en el VPS Ubuntu con systemd.' >&2
    exit 1
fi
. /etc/os-release
if [[ $ID != ubuntu || $VERSION_ID != 24.04 ]]; then
    echo 'La preparación automática requiere Ubuntu 24.04. Para otro sistema usa la guía oficial de instalación.' >&2
    exit 1
fi
apt-get update
apt-get install -y --no-install-recommends git curl ca-certificates restic openssl python3 util-linux unattended-upgrades
if ! command -v docker >/dev/null; then
    apt-get install -y --no-install-recommends docker.io docker-compose-v2
elif ! docker compose version >/dev/null 2>&1; then
    echo 'Ya existe Docker. Instala el complemento Compose v2 del mismo distribuidor y repite.' >&2
    exit 1
fi
systemctl enable --now docker
docker info --format 'Docker {{.ServerVersion}}'
docker compose version
restic version
echo 'Host preparado. Comprueba la llave SSH y las reglas del proveedor antes de publicar el DNS.'
