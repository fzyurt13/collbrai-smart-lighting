class CCTController:
    def __init__(self, target_cct, tolerance=20.0):
        self.target_cct = float(target_cct)
        self.tolerance = float(tolerance)

    def calculate_error(self, measured_cct):
        return self.target_cct - measured_cct

    def is_target_reached(self, measured_cct):
        return abs(self.calculate_error(measured_cct)) <= self.tolerance

    def get_step(self, error):
        error = abs(error)

        if error > 500:
            return 4.0
        elif error > 250:
            return 2.0
        elif error > 100:
            return 1.0
        elif error > 40:
            return 0.5
        else:
            return 0.2

    def adjust(self, warm, cool, measured_cct):
        error = self.calculate_error(measured_cct)

        if abs(error) <= self.tolerance:
            return round(warm, 1), round(cool, 1)

        step = self.get_step(error)

        if error > 0:
            warm -= step
            cool += step
        else:
            warm += step
            cool -= step

        warm = max(0.0, min(100.0, warm))
        cool = max(0.0, min(100.0, cool))

        return round(warm, 1), round(cool, 1)
