class BrightnessEstimator:
    """
    AS7343 VIS kanalindan parlaklik tahmini.

    CCT'ye bagli kalibrasyon kullanir.
    Ara CCT degerlerinde komsu kalibrasyon
    modelleri arasinda lineer interpolasyon yapilir.
    """

    CALIBRATION = {
        3500.0: {
            "slope": 30.7352,
            "intercept": 159.8,
        },
        4200.0: {
            "slope": 29.4664,
            "intercept": 169.0,
        },
        5000.0: {
            "slope": 28.1992,
            "intercept": 171.4,
        },
        6000.0: {
            "slope": 27.0376,
            "intercept": 162.3,
        },
    }

    def _model_for_cct(self, cct):
        cct = float(cct)

        points = sorted(
            self.CALIBRATION.keys()
        )

        if cct <= points[0]:
            return self.CALIBRATION[
                points[0]
            ]

        if cct >= points[-1]:
            return self.CALIBRATION[
                points[-1]
            ]

        for i in range(
            len(points) - 1
        ):
            c0 = points[i]
            c1 = points[i + 1]

            if c0 <= cct <= c1:
                fraction = (
                    (cct - c0)
                    /
                    (c1 - c0)
                )

                m0 = self.CALIBRATION[
                    c0
                ]["slope"]

                m1 = self.CALIBRATION[
                    c1
                ]["slope"]

                b0 = self.CALIBRATION[
                    c0
                ]["intercept"]

                b1 = self.CALIBRATION[
                    c1
                ]["intercept"]

                slope = (
                    m0
                    + fraction
                    * (m1 - m0)
                )

                intercept = (
                    b0
                    + fraction
                    * (b1 - b0)
                )

                return {
                    "slope": slope,
                    "intercept": intercept,
                }

        raise RuntimeError(
            "Brightness calibration error"
        )

    def estimate(
        self,
        vis,
        cct
    ):
        model = self._model_for_cct(
            cct
        )

        brightness = (
            float(vis)
            - model["intercept"]
        ) / model["slope"]

        brightness = max(
            0.0,
            min(
                100.0,
                brightness
            )
        )

        return brightness
