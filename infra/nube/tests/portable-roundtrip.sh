#!/usr/bin/env bash
# On a disposable Linux runner with Docker. The source/target data and test keys stay local.
set -Eeuo pipefail
[[ $EUID -eq 0 && ${MILENIO_DISPOSABLE_LINUX_RUNNER:-} == 1 ]] || exit 2
here=$(cd "$(dirname "$0")/.." && pwd)
repo=$(cd "$here/../.." && pwd)
revision=$(git -C "$repo" rev-parse HEAD)
export MILENIO_BUILD_REVISION=$revision MILENIO_CLOUD_HOST=prueba.example.invalid
image=milenio-taller:$revision
if ! docker image inspect "$image" >/dev/null 2>&1; then docker compose -f "$here/compose.yaml" build app; fi
fixture=$(mktemp -d /tmp/milenio-portable-test.XXXXXXXX)
trap '[[ -d $fixture && ! -L $fixture && $fixture == /tmp/milenio-portable-test.* ]] && rm -rf -- "$fixture"' EXIT
install -d -m 700 -o 10001 -g 10001 "$fixture/output" "$fixture/state/app"
docker run --rm --network none --read-only --tmpfs /tmp:rw,nosuid,nodev,mode=1777 \
    --mount "type=bind,src=$fixture/output,dst=/out" \
    --mount "type=bind,src=$here/tests/windows_portable.py,dst=/app/infra/nube/tests/windows_portable.py,readonly" \
    "$image" python /app/infra/nube/tests/windows_portable.py /out/portable
source_dir=$fixture/output/portable
hash=$(sha256sum "$source_dir/manifest.json" | cut -d' ' -f1)
win_release=$(printf '1%.0s' {1..64})
exec 9>>/run/lock/milenio-cloud.lock
flock -x -w 60 9
cmd=(python3 "$here/import_windows.py" install "$source_dir" "$fixture/state")
if "${cmd[@]}" "$win_release" "$win_release" "$revision" 2>/dev/null; then exit 3; fi
"${cmd[@]}" "$hash" "$win_release" "$revision"
if "${cmd[@]}" "$hash" "$win_release" "$revision" 2>/dev/null; then echo 'Destino ocupado aceptado.' >&2; exit 4; fi
python3 - "$fixture/state" <<'PY'
from pathlib import Path
import json, sqlite3, sys
state = Path(sys.argv[1])
receipt = json.loads((state/"ultima-importacion-windows.json").read_text())
assert receipt["business"]["invoice"]["total"] == "116" and receipt["business"]["payment"]["total"] == "50"
assert all(v["count"] == 1 for v in receipt["business"].values())
assert receipt["media_files"] == 1 and "workshop.0008_reception_receipt" in receipt["migrated_forward"]
with sqlite3.connect(state/"app/workshop.sqlite3") as db:
    assert db.execute("SELECT number FROM workshop_workorder").fetchone()[0] == "WO-PRUEBA"
    assert db.execute("SELECT count(*) FROM django_session").fetchone()[0] == 0
assert (state/"app/.mail-recovery-hold").is_file()
PY
printf 'PASS: manifiesto, migración histórica, folio, factura, pago, foto y rechazo de sobrescritura.\n'
