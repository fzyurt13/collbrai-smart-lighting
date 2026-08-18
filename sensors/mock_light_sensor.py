from sensors.base_sensor import LightSensor


class MockLightSensor(LightSensor):
    def __init__(self, environment):
        self.environment = environment

    def read(self):
        measurement = self.environment.read()

        return {
            "measured_cct": measurement["measured_cct"],
            "measured_light_percent": measurement[
                "measured_light_percent"
            ],
            "ambient_light_percent": measurement[
                "ambient_light_percent"
            ],
            "ambient_cct": measurement["ambient_cct"],
            "source": "mock_sensor"
        }
