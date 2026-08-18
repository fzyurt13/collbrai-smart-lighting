import cv2
import numpy as np


class MaterialAnalyzer:

    def analyze(self, image):
        if image is None:
            raise ValueError("Image is None.")

        hsv = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2HSV
        )

        total_pixels = float(
            image.shape[0] * image.shape[1]
        )

        # Yellow / gold-like regions
        yellow_mask = cv2.inRange(
            hsv,
            np.array([15, 60, 60]),
            np.array([40, 255, 255])
        )

        # White / silver-like regions:
        # low saturation + medium/high brightness
        white_mask = cv2.inRange(
            hsv,
            np.array([0, 0, 120]),
            np.array([179, 70, 255])
        )

        # Very bright / specular highlights
        bright_mask = cv2.inRange(
            hsv,
            np.array([0, 0, 220]),
            np.array([179, 255, 255])
        )

        # Dark / background-like regions
        dark_mask = cv2.inRange(
            hsv,
            np.array([0, 0, 0]),
            np.array([179, 255, 60])
        )

        yellow_ratio = (
            cv2.countNonZero(yellow_mask)
            / total_pixels
            * 100.0
        )

        white_ratio = (
            cv2.countNonZero(white_mask)
            / total_pixels
            * 100.0
        )

        bright_ratio = (
            cv2.countNonZero(bright_mask)
            / total_pixels
            * 100.0
        )

        dark_ratio = (
            cv2.countNonZero(dark_mask)
            / total_pixels
            * 100.0
        )

        return {
            "yellow_like_percent": round(
                yellow_ratio,
                2
            ),
            "white_metal_like_percent": round(
                white_ratio,
                2
            ),
            "bright_specular_percent": round(
                bright_ratio,
                2
            ),
            "dark_background_percent": round(
                dark_ratio,
                2
            )
        }

    def analyze_file(self, image_path):
        image = cv2.imread(
            str(image_path),
            cv2.IMREAD_COLOR
        )

        if image is None:
            raise ValueError(
                "Could not read image: {}".format(
                    image_path
                )
            )

        return self.analyze(image)
