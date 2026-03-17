import json
import os
from collections.abc import Mapping
from functools import lru_cache
from importlib.resources import files

from jsonschema import validate


@lru_cache(maxsize=1)
def _load_session_schema():
    schema_path = files("flowerapp").joinpath("schemas", "session.schema.json")
    with schema_path.open("r", encoding="utf-8-sig") as handle:
        return json.load(handle)


def _normalize_project(data):
    if not isinstance(data, Mapping):
        return data

    normalized = dict(data)
    normalized.setdefault("app_version", "1.0.0")
    normalized.setdefault("session_schema_version", 1)

    metadata = normalized.get("metadata")
    if isinstance(metadata, dict):
        normalized["metadata"] = dict(metadata)

    intake = normalized.get("intake")
    if intake is None:
        normalized["intake"] = {}
    elif isinstance(intake, dict):
        normalized["intake"] = dict(intake)

    scoring = normalized.get("scoring")
    if scoring is None:
        normalized["scoring"] = {"agency_total": 0, "subscores": {}}
    elif isinstance(scoring, dict):
        scoring_data = dict(scoring)
        scoring_data.setdefault("agency_total", 0)
        scoring_data.setdefault("subscores", {})
        normalized["scoring"] = scoring_data

    return normalized


def _validate_project(data):
    normalized = _normalize_project(data)
    validate(instance=normalized, schema=_load_session_schema())
    return normalized


def save_project(data, path):
    normalized = _validate_project(data)
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "session.json"), "w", encoding="utf-8") as handle:
        json.dump(normalized, handle, indent=4)


def load_project(path):
    fpath = os.path.join(path, "session.json")
    if not os.path.exists(fpath):
        return None
    with open(fpath, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    return _validate_project(data)
