import random


class MockLightingEnvironment:
    def __init__(self):
        self.warm = 50.0
        self.cool = 50.0

        # LED sürme seviyesi
        self.led_drive_percent = 100.0

        # Ortam ışığı
        self.ambient_light_percent = 15.0
        self.ambient_cct = 5500.0

    def apply_led_state(self, warm, cool, brightness):
        self.warm = float(warm)
        self.cool = float(cool)
        self.led_drive_percent = float(brightness)

    def set_ambient_light(self, value):
        self.ambient_light_percent = max(
            0.0,
            min(100.0, float(value))
        )

    def set_ambient_cct(self, value):
        self.ambient_cct = max(
            2000.0,
            min(10000.0, float(value))
        )

    def simulate_ambient_step(self, iteration):
        if iteration < 10:
            self.ambient_light_percent = 5.0
            self.ambient_cct = 3200.0

        elif iteration < 20:
            self.ambient_light_percent = 20.0
            self.ambient_cct = 4500.0

        elif iteration < 30:
            self.ambient_light_percent = 40.0
            self.ambient_cct = 6500.0

        else:
            self.ambient_light_percent = 10.0
            self.ambient_cct = 3800.0

        return {
            "ambient_light_percent": self.ambient_light_percent,
            "ambient_cct": self.ambient_cct
        }

    def get_led_cct(self):
        total = self.warm + self.cool

        if total <= 0:
            return 0.0

        cool_ratio = self.cool / total

        return 3000.0 + (3500.0 * cool_ratio)

    def get_measured_cct(self):
        led_cct = self.get_led_cct()

        led_weight = max(
            0.0,
            self.led_drive_percent
        )

        ambient_weight = max(
            0.0,
            self.ambient_light_percent
        )

        total_weight = led_weight + ambient_weight

        if total_weight <= 0:
            return 0.0

        mixed_cct = (
            (led_cct * led_weight)
            + (self.ambient_cct * ambient_weight)
        ) / total_weight

        noise = random.uniform(-15.0, 15.0)

        return mixed_cct + noise

    def get_measured_light_percent(self):
        total_light = (
            self.led_drive_percent
            + self.ambient_light_percent
        )

        noise = random.uniform(-0.8, 0.8)

        total_light += noise

        return max(
            0.0,
            min(100.0, total_light)
        )

    def read(self):
        return {
            "measured_cct": self.get_measured_cct(),
            "measured_light_percent": self.get_measured_light_percent(),
            "led_drive_percent": self.led_drive_percent,
            "ambient_light_percent": self.ambient_light_percent,
            "ambient_cct": self.ambient_cct
        }
