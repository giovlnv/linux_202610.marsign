import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from apple import data_dir


def _file():
    return data_dir() / "apps.json"


def load():
    path = _file()
    return json.loads(path.read_text()) if path.exists() else {}


def _save(apps):
    _file().write_text(json.dumps(apps, indent=2))


def ipa_path(entry):
    stored = Path(entry["ipa"])
    if not stored.is_absolute():
        return data_dir() / stored
    return stored if stored.is_file() else data_dir() / "ipas" / stored.name


def record(ipa, app, signed_bundle_id, expires):
    folder = data_dir() / "ipas"
    folder.mkdir(exist_ok=True)
    stored = folder / f"{app['bundle_id']}.ipa"
    if Path(ipa).resolve() != stored.resolve():
        shutil.copyfile(ipa, stored)
    apps = load()
    apps[signed_bundle_id] = {
        "name": app["name"],
        "version": app["version"],
        "ipa": f"ipas/{stored.name}",
        "expires": expires.replace(tzinfo=expires.tzinfo or timezone.utc).isoformat(),
    }
    _save(apps)


def forget(signed_bundle_id):
    apps = load()
    entry = apps.pop(signed_bundle_id, None)
    _save(apps)
    return entry


def days_left(entry, now=None):
    expires = datetime.fromisoformat(entry["expires"])
    return (expires - (now or datetime.now(timezone.utc))).total_seconds() / 86400
