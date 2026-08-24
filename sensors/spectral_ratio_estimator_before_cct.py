class SpectralRatioEstimator:
    """
    AS7343 spektral verisinden Warm/Cool LED karisim oranini
    tahmin eder.

    Kalibrasyon:
        LED ve AS7343 ayni yone bakiyor.
        Sabit fiziksel geometri.
        0/25/50/75/100 % Cool kalibrasyon noktalari.
    """

    COOL_POINTS = [0.0, 25.0, 50.0, 75.0, 100.0]

    R1_POINTS = [
        0.101,
        0.149,
        0.208,
        0.279,
        0.392
    ]

    R2_POINTS = [
        0.159,
        0.233,
        0.327,
        0.447,
        0.639
    ]

    def _interpolate(self, value, x_points):
        if value <= x_points[0]:
            return self.COOL_POINTS[0]

        if value >= x_points[-1]:
            return self.COOL_POINTS[-1]

        for i in range(len(x_points) - 1):
            x0 = x_points[i]
            x1 = x_points[i + 1]

            if x0 <= value <= x1:
                y0 = self.COOL_POINTS[i]
                y1 = self.COOL_POINTS[i + 1]

                fraction = (
                    (value - x0)
                    /
                    (x1 - x0)
                )

                return y0 + fraction * (y1 - y0)

        return 0.0

    def estimate(self, spectral):
        fz450 = float(spectral["FZ_450"])
        f6640 = float(spectral["F6_640"])
        f3475 = float(spectral["F3_475"])
        f7690 = float(spectral["F7_690"])

        if f6640 <= 0 or f7690 <= 0:
            raise ValueError(
                "Invalid spectral measurement"
            )

        r1 = fz450 / f6640
        r2 = f3475 / f7690

        cool_r1 = self._interpolate(
            r1,
            self.R1_POINTS
        )

        cool_r2 = self._interpolate(
            r2,
            self.R2_POINTS
        )

        # Ilk versiyon:
        # iki spektral gostergenin esit agirlikli ortalamasi
        cool_percent = (
            cool_r1 + cool_r2
        ) / 2.0

        cool_percent = max(
            0.0,
            min(100.0, cool_percent)
        )

        warm_percent = (
            100.0 - cool_percent
        )

        return {
            "warm_percent": warm_percent,
            "cool_percent": cool_percent,

            "ratio_450_640": r1,
            "ratio_475_690": r2,

            "cool_from_r1": cool_r1,
            "cool_from_r2": cool_r2
        }
