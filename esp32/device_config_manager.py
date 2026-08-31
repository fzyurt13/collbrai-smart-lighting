import json
import machine
import ubinascii

CONFIG_FILE = "device_config.json"
DEFAULT_TCP_PORT = 5000
SETUP_FILE = "setup_identity.json"


def _generate_setup_pin():
    try:
        import os
        raw = os.urandom(4)

        value = int.from_bytes(
            raw,
            "big"
        )

    except Exception:
        import machine
        import time

        seed = (
            int.from_bytes(
                machine.unique_id(),
                "big"
            )
            ^ time.ticks_ms()
        )

        value = seed

    # 8 haneli, 10000000 - 99999999 arası PIN.
    return str(
        10000000
        + (value % 90000000)
    )


def get_or_create_setup_pin():
    try:
        with open(SETUP_FILE, "r") as file:
            data = json.load(file)

        pin = str(
            data.get(
                "setup_pin",
                ""
            )
        )

        if (
            len(pin) == 8
            and pin.isdigit()
        ):
            return pin

    except (OSError, ValueError):
        pass

    pin = _generate_setup_pin()

    data = {
        "device_id": get_device_id(),
        "setup_pin": pin
    }

    temp_file = SETUP_FILE + ".tmp"

    with open(temp_file, "w") as file:
        json.dump(data, file)

    try:
        import os

        try:
            os.remove(SETUP_FILE)
        except OSError:
            pass

        os.rename(
            temp_file,
            SETUP_FILE
        )

    except Exception:
        with open(SETUP_FILE, "w") as file:
            json.dump(data, file)

        try:
            import os
            os.remove(temp_file)
        except Exception:
            pass

    return pin


def get_device_id():
    raw_id = machine.unique_id()
    hex_id = ubinascii.hexlify(raw_id).decode().upper()

    # Son 6 karakter cihazı ayırt etmek için yeterli.
    short_id = hex_id[-6:]

    return "MERALED-" + short_id


def _read_json_config():
    try:
        with open(CONFIG_FILE, "r") as file:
            data = json.load(file)

        if not isinstance(data, dict):
            return None

        return data

    except (OSError, ValueError):
        return None


def load_runtime_config():
    device_id = get_device_id()
    stored = _read_json_config()

    if stored:
        ssid = stored.get("wifi_ssid")
        password = stored.get("wifi_password")
        tcp_port = stored.get(
            "tcp_port",
            DEFAULT_TCP_PORT
        )

        if ssid and password:
            return {
                "device_id": device_id,
                "provisioned": True,
                "wifi_ssid": ssid,
                "wifi_password": password,
                "tcp_port": int(tcp_port),
                "source": "device_config"
            }

    # Gecis donemi:
    # Mevcut prototip ayarlari ile calismaya devam et.
    try:
        from wifi_config import (
            WIFI_SSID,
            WIFI_PASSWORD,
            TCP_PORT
        )

        return {
            "device_id": device_id,
            "provisioned": False,
            "wifi_ssid": WIFI_SSID,
            "wifi_password": WIFI_PASSWORD,
            "tcp_port": int(TCP_PORT),
            "source": "legacy_wifi_config"
        }

    except Exception:
        return {
            "device_id": device_id,
            "provisioned": False,
            "wifi_ssid": None,
            "wifi_password": None,
            "tcp_port": DEFAULT_TCP_PORT,
            "source": "none"
        }


def save_wifi_config(ssid, password, tcp_port=DEFAULT_TCP_PORT):
    if not ssid:
        raise ValueError("Wi-Fi SSID cannot be empty")

    if password is None:
        raise ValueError("Wi-Fi password cannot be None")

    data = {
        "device_id": get_device_id(),
        "wifi_ssid": str(ssid),
        "wifi_password": str(password),
        "tcp_port": int(tcp_port)
    }

    temp_file = CONFIG_FILE + ".tmp"

    with open(temp_file, "w") as file:
        json.dump(data, file)

    try:
        import os

        try:
            os.remove(CONFIG_FILE)
        except OSError:
            pass

        os.rename(
            temp_file,
            CONFIG_FILE
        )

    except Exception:
        # Çok eski MicroPython dosya sistemleri için fallback.
        with open(CONFIG_FILE, "w") as file:
            json.dump(data, file)

        try:
            import os
            os.remove(temp_file)
        except Exception:
            pass

    return True


def clear_wifi_config():
    try:
        import os
        os.remove(CONFIG_FILE)
        return True

    except OSError:
        return False
