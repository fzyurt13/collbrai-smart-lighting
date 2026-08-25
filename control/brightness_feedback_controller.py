class BrightnessFeedbackController:
    """
    Ölçülen parlaklık yüzdesine göre toplam LED seviyesini düzeltir.
    """

    def __init__(
        self,
        gain=0.5,
        tolerance=2.0,
        max_correction=8.0
    ):
        self.gain = float(gain)
        self.tolerance = float(tolerance)
        self.max_correction = float(max_correction)

    def calculate(
        self,
        target_brightness,
        measured_brightness,
        current_brightness
    ):
        error = (
            float(target_brightness)
            - float(measured_brightness)
        )

        if abs(error) <= self.tolerance:
            return {
                "error": error,
                "correction": 0.0,
                "new_brightness": float(current_brightness),
                "locked": True
            }

        correction = error * self.gain

        correction = max(
            -self.max_correction,
            min(
                self.max_correction,
                correction
            )
        )

        new_brightness = (
            float(current_brightness)
            + correction
        )

        new_brightness = max(
            0.0,
            min(100.0, new_brightness)
        )

        return {
            "error": error,
            "correction": correction,
            "new_brightness": new_brightness,
            "locked": False
        }
