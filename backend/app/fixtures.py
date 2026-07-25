import json
import re
from datetime import datetime, timedelta, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any

FIXTURE_DIR = Path(__file__).resolve().parents[2] / "contracts" / "fixtures"
TIME_TOKEN = re.compile(r"^\$(now|today)(?:-(\d+)([mhd]))?$")
TIME_UNITS = {"m": "minutes", "h": "hours", "d": "days"}


def _resolve_time_token(value: str) -> str:
    match = TIME_TOKEN.match(value)
    if match is None:
        return value

    kind, amount, unit = match.groups()
    delta = timedelta(**{TIME_UNITS[unit]: int(amount)}) if amount and unit else timedelta()
    moment = datetime.now(timezone.utc) - delta

    if kind == "today":
        return moment.date().isoformat()
    return moment.replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _resolve_tokens(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _resolve_tokens(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve_tokens(item) for item in value]
    if isinstance(value, str):
        return _resolve_time_token(value)
    return value


@lru_cache
def _read_fixture(name: str) -> str:
    path = FIXTURE_DIR / name
    if not path.is_file():
        raise FileNotFoundError(f"Contract fixture does not exist: {path}")
    return path.read_text(encoding="utf-8")


def load_fixture(name: str) -> Any:
    return _resolve_tokens(json.loads(_read_fixture(name)))

