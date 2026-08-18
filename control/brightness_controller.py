class BrightnessController:
    def __init__(self, target_brightness, tolerance=1.0):
        self.target_brightness = float(target_brightness)
        self.tolerance = float(tolerance)

    def calculate_error(self, measured_brightness):
        return self.target_brightness - measured_brightness

    def is_target_reached(self, measured_brightness):
        return abs(
            self.calculate_error(measured_brightness)
        ) <= self.tolerance

    def get_step(self, error):
        error = abs(error)

        if error > 30:
            return 5.0
        elif error > 15:
            return 3.0
        elif error > 5:
            return 1.0
        elif error > 2:
            return 0.5
        else:
            return 0.2

    def adjust(self, brightness, measured_brightness):
        error = self.calculate_error(measured_brightness)

        if abs(error) <= self.tolerance:
            return brightness

        step = self.get_step(error)

        if error > 0:
            brightness += step
        else:
            brightness -= step

        return round(
            max(0.0, min(100.0, brightness)),
            1
        )
