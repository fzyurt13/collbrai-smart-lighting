class CompensationGuard:
    def __init__(
        self,
        warm_limit=97.0,
        cool_limit=97.0,
        error_threshold=100.0
    ):
        self.warm_limit = float(warm_limit)
        self.cool_limit = float(cool_limit)
        self.error_threshold = float(error_threshold)

    def check(self, warm, cool, cct_error):
        abs_error = abs(float(cct_error))

        warm_saturated = warm >= self.warm_limit
        cool_saturated = cool >= self.cool_limit

        if warm_saturated and cct_error < -self.error_threshold:
            return {
                "limited": True,
                "reason": "warm_channel_saturated",
                "message": (
                    "Ambient spectrum is too cool for the LED "
                    "system to fully compensate."
                )
            }

        if cool_saturated and cct_error > self.error_threshold:
            return {
                "limited": True,
                "reason": "cool_channel_saturated",
                "message": (
                    "Ambient spectrum is too warm for the LED "
                    "system to fully compensate."
                )
            }

        return {
            "limited": False,
            "reason": None,
            "message": None
        }
