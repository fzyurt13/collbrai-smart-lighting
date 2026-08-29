class BrightnessEstimator:
    """
    AS7343 VIS kanalindan parlaklik tahmini.

    Yeni 18-kanal AS7343 kalibrasyonuna dayanir.

    Her CCT icin olculmus VIS -> brightness noktalarinda
    piecewise-linear interpolasyon kullanilir.

    Ara CCT degerlerinde komsu CCT kalibrasyonlarinin
    tahminleri lineer olarak interpolate edilir.
    """

    CALIBRATION = {
        3500.0: [
            (9611.0, 25.0),
            (16120.7, 50.0),
            (22536.0, 75.0),
            (28939.7, 100.0),
        ],

        4200.0: [
            (8231.7, 25.0),
            (13152.0, 50.0),
            (18049.7, 75.0),
            (22963.0, 100.0),
        ],

        5000.0: [
            (7719.0, 25.0),
            (11875.7, 50.0),
            (16064.7, 75.0),
            (20299.0, 100.0),
        ],

        6000.0: [
            (8936.7, 25.0),
            (15996.0, 50.0),
            (22404.0, 75.0),
            (28811.7, 100.0),
        ],
    }

    def _estimate_at_cct(self, vis, cct):
        points = self.CALIBRATION[cct]
        vis = float(vis)

        # Alt sinir:
        # 0 VIS -> 0% brightness kabul edilir.
        if vis <= points[0][0]:
            if vis <= 0:
                return 0.0

            vis0 = 0.0
            b0 = 0.0
            vis1, b1 = points[0]

            fraction = (
                (vis - vis0)
                /
                (vis1 - vis0)
            )

            return b0 + fraction * (b1 - b0)

        # Olculmus noktalar arasinda interpolasyon.
        for i in range(len(points) - 1):
            vis0, b0 = points[i]
            vis1, b1 = points[i + 1]

            if vis0 <= vis <= vis1:
                fraction = (
                    (vis - vis0)
                    /
                    (vis1 - vis0)
                )

                return b0 + fraction * (b1 - b0)

        # Ust sinir.
        return 100.0

    def estimate(self, vis, cct):
        cct = float(cct)
        vis = float(vis)

        cct_points = sorted(
            self.CALIBRATION.keys()
        )

        if cct <= cct_points[0]:
            brightness = self._estimate_at_cct(
                vis,
                cct_points[0]
            )

        elif cct >= cct_points[-1]:
            brightness = self._estimate_at_cct(
                vis,
                cct_points[-1]
            )

        else:
            brightness = None

            for i in range(len(cct_points) - 1):
                c0 = cct_points[i]
                c1 = cct_points[i + 1]

                if c0 <= cct <= c1:
                    b0 = self._estimate_at_cct(
                        vis,
                        c0
                    )

                    b1 = self._estimate_at_cct(
                        vis,
                        c1
                    )

                    fraction = (
                        (cct - c0)
                        /
                        (c1 - c0)
                    )

                    brightness = (
                        b0
                        + fraction * (b1 - b0)
                    )

                    break

            if brightness is None:
                raise RuntimeError(
                    "Brightness calibration error"
                )

        return max(
            0.0,
            min(100.0, brightness)
        )
