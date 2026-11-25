"""Read-only checks for the Ubuntu host that runs Milenio."""
import ipaddress
import json
import math
import os
import re
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backup"))
from backup import HASH, REVISION, copy_footprint, private_file, require_capacity

STATE = Path("/var/lib/milenio-cloud")


def output(*args):
    return subprocess.run(args, check=True, text=True, capture_output=True, timeout=30).stdout


def latest_receipt(path, hours):
    data = json.loads(private_file(path).read_text())
    age = time.time() - float(data["completed_unix"])
    if (not math.isfinite(age) or age < 0 or age > hours * 3600
            or not HASH.fullmatch(str(data.get("snapshot"))) or not REVISION.fullmatch(str(data.get("revision")))):
        raise ValueError(f"Consulta el servicio y un recibo válido de las últimas {hours} horas")
    return f"hace {age / 3600:.1f} h"


def ssh_options():
    values = {}
    for row in output("/usr/sbin/sshd", "-T").splitlines():
        key, value = row.split(" ", 1)
        values.setdefault(key, []).append(value)
    return values


def ssh_keys():
    values = ssh_options()
    if (values["passwordauthentication"] != ["no"] or values["kbdinteractiveauthentication"] != ["no"]
            or values["pubkeyauthentication"] != ["yes"] or values["permitrootlogin"] == ["yes"]):
        raise ValueError("Revisa las opciones globales de autenticación en sshd y prueba la entrada por llave")
    return "opciones globales de acceso por llave"


def loopback(host):
    if host == "*":
        return False
    address = ipaddress.ip_address(host.strip("[]").split("%", 1)[0])
    return address.is_loopback or bool(getattr(address, "ipv4_mapped", None) and address.ipv4_mapped.is_loopback)


def ports():
    allowed = {("tcp", x) for x in [*ssh_options()["port"], "80", "443"]}
    exposed = set()
    for row in output("ss", "-Hlnt").splitlines():
        host, port = row.split()[3].rsplit(":", 1)
        if not loopback(host):
            exposed.add(("tcp", port))
    # Docker may forward using NAT without opening a host socket.
    containers = output("docker", "ps", "-q").split()
    if containers:
        fmt = "{{json .NetworkSettings.Ports}}"
        for line in output("docker", "inspect", "--format", fmt, *containers).splitlines():
            for key, bindings in (json.loads(line) or {}).items():
                for item in bindings or []:
                    if not loopback(item["HostIp"] or "*"):
                        exposed.add((key.rsplit("/", 1)[1], item["HostPort"]))
    unexpected = exposed - allowed
    if unexpected:
        raise ValueError("Revisa los puertos adicionales: " + ", ".join(f"{port}/{proto}" for proto, port in sorted(unexpected)))
    if not {("tcp", "80"), ("tcp", "443")} <= exposed:
        raise ValueError("Confirma que Caddy publica 80 y 443 TCP")
    return "listeners TCP y publicaciones Docker dentro de los puertos previstos"


def active(unit):
    output("systemctl", "is-active", "--quiet", unit)
    return "activo"


def updates():
    active("apt-daily-upgrade.timer")
    for key in ("Update-Package-Lists", "Unattended-Upgrade"):
        setting = output("apt-config", "shell", "value", "APT::Periodic::" + key).strip()
        if not re.fullmatch(r"value='(?:[1-9][0-9]*|always)'", setting):
            raise ValueError("Revisa APT::Periodic::" + key)
    return "temporizador activo y APT periódico habilitado"


def capacity():
    if not (STATE / "app/workshop.sqlite3").is_file():
        raise ValueError("Base operativa ausente")
    free = require_capacity(STATE, copy_footprint(STATE / "app"))
    return f"{free / 1024**3:.1f} GiB disponibles para el taller y su próxima copia"


def main():
    if os.geteuid() != 0:
        sys.exit("Ejecuta con sudo en el VPS del taller.")
    checks = [
        ("Acceso SSH", ssh_keys),
        ("Puertos", ports),
        ("Actualizaciones Ubuntu", updates),
        ("Timer de respaldo", lambda: active("milenio-nube-backup.timer")),
        ("Última copia cifrada", lambda: latest_receipt(STATE / "ultimo-respaldo.json", 26)),
        ("Último simulacro local de restauración", lambda: latest_receipt(STATE / "ultimo-simulacro.json", 35 * 24)),
        ("Disco", capacity),
    ]
    failed = False
    for name, check in checks:
        try:
            print(f"OK · {name} · {check()}")
        except (OSError, ValueError, KeyError, TypeError, IndexError, subprocess.SubprocessError) as error:
            failed = True
            print(f"REVISAR · {name} · {error}", file=sys.stderr)
    return int(failed)


if __name__ == "__main__":
    sys.exit(main())
