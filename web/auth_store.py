import json
from pathlib import Path
from threading import Lock

from werkzeug.security import generate_password_hash, check_password_hash


AUTH_FILE = Path(__file__).resolve().parent.parent / "data" / "operator_auth.json"
DEFAULT_PIN = "1234"

_lock = Lock()


def _is_valid_pin(pin):
    return isinstance(pin, str) and len(pin) == 4 and pin.isdigit()


def _ensure_auth_file():
    AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)

    if not AUTH_FILE.exists():
        data = {
            "pin_hash": generate_password_hash(DEFAULT_PIN)
        }
        AUTH_FILE.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )


def verify_pin(pin):
    if not _is_valid_pin(pin):
        return False

    with _lock:
        _ensure_auth_file()

        try:
            data = json.loads(
                AUTH_FILE.read_text(encoding="utf-8")
            )
            pin_hash = data["pin_hash"]
        except (OSError, KeyError, json.JSONDecodeError):
            return False

        return check_password_hash(pin_hash, pin)


def change_pin(new_pin):
    if not _is_valid_pin(new_pin):
        raise ValueError("PIN must contain exactly 4 digits.")

    with _lock:
        AUTH_FILE.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "pin_hash": generate_password_hash(new_pin)
        }

        temp_file = AUTH_FILE.with_suffix(".tmp")

        temp_file.write_text(
            json.dumps(data, indent=2),
            encoding="utf-8"
        )

        temp_file.replace(AUTH_FILE)
