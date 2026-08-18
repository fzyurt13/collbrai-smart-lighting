from sensors.base_sensor import LightSensor


class AS7343Sensor(LightSensor):
    def __init__(self):
        self.connected = False

    def connect(self):
        """
        Real ESP32/AS7343 connection will be implemented here.
        """
        raise NotImplementedError(
            "AS7343 hardware is not connected yet."
        )

    def read(self):
        """
        Expected final return format:

        {
            "measured_cct": float,
            "measured_light_percent": float,
            "spectral": {...},
            "source": "as7343"
        }
        """
        raise NotImplementedError(
            "AS7343 hardware read is not implemented yet."
        )
