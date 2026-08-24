class CCTFeedbackController:
    """
    Kelvin hatasini kullanarak Warm/Cool karisimini duzeltir.

    Nominal LED araligi:
        Warm = 3000 K
        Cool = 6500 K

    3500 K aralik / 100 Cool puani
    => 1 Cool puani ~= 35 K
    """

    def __init__(
        self,
        warm_cct=3000.0,
        cool_cct=6500.0,
        gain=0.5,
        tolerance_kelvin=50.0,
        max_correction=5.0
    ):
        self.warm_cct = float(warm_cct)
        self.cool_cct = float(cool_cct)
        self.gain = float(gain)
        self.tolerance_kelvin = float(tolerance_kelvin)
        self.max_correction = float(max_correction)

        self.kelvin_per_cool_percent = (
            (self.cool_cct - self.warm_cct)
            / 100.0
        )

    def calculate(
        self,
        target_cct,
        measured_cct,
        current_cool
    ):
        error_kelvin = (
            float(target_cct)
            - float(measured_cct)
        )

        if abs(error_kelvin) <= self.tolerance_kelvin:
            return {
                "error_kelvin": error_kelvin,
                "correction_cool": 0.0,
                "new_cool": float(current_cool),
                "locked": True
            }

        correction_cool = (
            error_kelvin
            / self.kelvin_per_cool_percent
        ) * self.gain

        correction_cool = max(
            -self.max_correction,
            min(
                self.max_correction,
                correction_cool
            )
        )

        new_cool = (
            float(current_cool)
            + correction_cool
        )

        new_cool = max(
            0.0,
            min(100.0, new_cool)
        )

        return {
            "error_kelvin": error_kelvin,
            "correction_cool": correction_cool,
            "new_cool": new_cool,
            "locked": False
        }
