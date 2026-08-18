class LightingController:
    def __init__(self):
        self.warm = 0.0
        self.cool = 0.0
        self.brightness = 0.0

    def set_target(self, warm, cool, brightness=100):
        self.warm = round(max(0.0, min(100.0, float(warm))), 1)
        self.cool = round(max(0.0, min(100.0, float(cool))), 1)
        self.brightness = round(
            max(0.0, min(100.0, float(brightness))),
            1
        )

    def get_state(self):
        return {
            "warm": self.warm,
            "cool": self.cool,
            "brightness": self.brightness
        }
