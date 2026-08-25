class BrightnessEstimator:
    """
    AS7343 VIS kanalindan LED parlaklik yuzdesi tahmini.

    Kalibrasyon geometrisi:
        Warm/Cool mix ~= 65.7 / 34.3
        Sabit LED + AS7343 + hedef yuzey konumu

    Stabil kalibrasyon noktalarindan:
        VIS ~= 29.2202 * brightness + 170.05
    """

    SLOPE = 29.2202
    INTERCEPT = 170.05

    def estimate(self, vis):
        vis = float(vis)

        brightness = (
            vis - self.INTERCEPT
        ) / self.SLOPE

        brightness = max(
            0.0,
            min(100.0, brightness)
        )

        return brightness
