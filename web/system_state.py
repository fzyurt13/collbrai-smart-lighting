from threading import Lock
from copy import deepcopy


class SystemState:
    def __init__(self):
        self._lock = Lock()

        self._state = {
            "status": "STANDBY",
            "mode": "AUTO",
            "requested_mode": None,

            "manual_target_cct": None,
            "manual_target_brightness": None,

            "product": None,

            "target_cct": None,
            "measured_cct": None,

            "target_brightness": None,
            "measured_brightness": None,

            "warm_output": 2.0,
            "cool_output": 2.0,

            "health": {
                "jetson": True,
                "esp32": False,
                "as7343": False,
                "camera": False,
            },
        }

    def update(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if key in self._state:
                    self._state[key] = value

    def update_health(self, **kwargs):
        with self._lock:
            for key, value in kwargs.items():
                if key in self._state["health"]:
                    self._state["health"][key] = bool(value)

    def request_manual(self, target_cct, target_brightness):
        with self._lock:
            self._state["requested_mode"] = "MANUAL"
            self._state["manual_target_cct"] = float(target_cct)
            self._state["manual_target_brightness"] = float(
                target_brightness
            )

    def request_auto(self):
        with self._lock:
            self._state["requested_mode"] = "AUTO"

    def get(self):
        with self._lock:
            return deepcopy(self._state)


system_state = SystemState()
