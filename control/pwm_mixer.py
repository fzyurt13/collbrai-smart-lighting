class PWMMixer:
    def __init__(self, pwm_max=4095):
        self.pwm_max = int(pwm_max)

    def clamp(self, value, minimum=0.0, maximum=100.0):
        return max(minimum, min(maximum, float(value)))

    def percentage_to_pwm(self, percentage):
        percentage = self.clamp(percentage)

        pwm = round(
            (percentage / 100.0) * self.pwm_max
        )

        return int(pwm)

    def mix(self, warm, cool, brightness):
        warm = self.clamp(warm)
        cool = self.clamp(cool)
        brightness = self.clamp(brightness)

        brightness_factor = brightness / 100.0

        warm_output = warm * brightness_factor
        cool_output = cool * brightness_factor

        return {
            "warm_percent": round(warm_output, 2),
            "cool_percent": round(cool_output, 2),

            "warm_pwm": self.percentage_to_pwm(
                warm_output
            ),

            "cool_pwm": self.percentage_to_pwm(
                cool_output
            )
        }
