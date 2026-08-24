class SpectralFeedbackController:
    def __init__(
        self,
        gain=0.5,
        tolerance=1.0,
        max_correction=5.0
    ):
        self.gain = float(gain)
        self.tolerance = float(tolerance)
        self.max_correction = float(max_correction)

    def calculate(
        self,
        target_cool,
        measured_cool,
        current_cool
    ):
        error = (
            float(target_cool)
            - float(measured_cool)
        )

        if abs(error) <= self.tolerance:
            return {
                "error": error,
                "correction": 0.0,
                "new_cool": float(current_cool),
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

        new_cool = (
            float(current_cool)
            + correction
        )

        new_cool = max(
            0.0,
            min(100.0, new_cool)
        )

        return {
            "error": error,
            "correction": correction,
            "new_cool": new_cool,
            "locked": False
        }
