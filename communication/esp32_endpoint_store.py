import json
import os
import tempfile
from threading import RLock


# MERALED_ESP32_ENDPOINT_STORE_V1

_LOCK = RLock()

_ENDPOINT_FILE = os.path.join(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    ),
    "runtime",
    "esp32_endpoint.json",
)


def load_esp32_endpoint():

    with _LOCK:

        try:
            with open(
                _ENDPOINT_FILE,
                "r",
                encoding="utf-8",
            ) as handle:
                data = json.load(handle)

        except (
            FileNotFoundError,
            json.JSONDecodeError,
            OSError,
        ):
            return None


        host = str(
            data.get("host", "")
        ).strip()

        try:
            tcp_port = int(
                data.get(
                    "tcp_port",
                    5000
                )
            )
        except (
            TypeError,
            ValueError,
        ):
            return None


        if not host:
            return None


        return {
            "host": host,
            "tcp_port": tcp_port,
            "device_id": data.get(
                "device_id"
            ),
        }


def save_esp32_endpoint(
    host,
    tcp_port,
    device_id=None,
):

    host = str(host).strip()
    tcp_port = int(tcp_port)

    if not host:
        raise ValueError(
            "ESP32 endpoint host cannot be empty"
        )


    data = {
        "host": host,
        "tcp_port": tcp_port,
        "device_id": (
            str(device_id)
            if device_id
            else None
        ),
    }


    directory = os.path.dirname(
        _ENDPOINT_FILE
    )

    os.makedirs(
        directory,
        exist_ok=True,
    )


    with _LOCK:

        fd, temp_path = tempfile.mkstemp(
            prefix=".esp32_endpoint_",
            suffix=".json",
            dir=directory,
            text=True,
        )

        try:

            with os.fdopen(
                fd,
                "w",
                encoding="utf-8",
            ) as handle:

                json.dump(
                    data,
                    handle,
                    indent=2,
                    sort_keys=True,
                )

                handle.write("\n")

                handle.flush()
                os.fsync(
                    handle.fileno()
                )


            os.replace(
                temp_path,
                _ENDPOINT_FILE,
            )

        finally:

            if os.path.exists(
                temp_path
            ):
                os.remove(
                    temp_path
                )


    return dict(data)
