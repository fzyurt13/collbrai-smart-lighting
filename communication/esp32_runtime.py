from threading import RLock


# MERALED_ESP32_RUNTIME_REGISTRY_V1

_lock = RLock()
_client = None


def register_esp32_client(client):
    global _client

    with _lock:
        _client = client


def clear_esp32_client(client=None):
    global _client

    with _lock:

        if (
            client is None
            or _client is client
        ):
            _client = None


def get_esp32_client():
    with _lock:
        return _client
