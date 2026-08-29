from ai.base_classifier import ProductClassifier

import cv2
import numpy as np


class IMX219ProductClassifier(ProductClassifier):

    def __init__(self, model_path=None):
        self.model_path = model_path

    def predict(self, frame=None):

        if frame is None:
            raise ValueError("Camera frame is required.")

        h, w = frame.shape[:2]

        # 70% center ROI
        roi_w = int(w * 0.70)
        roi_h = int(h * 0.70)

        x1 = (w - roi_w) // 2
        y1 = (h - roi_h) // 2

        roi = frame[
            y1:y1 + roi_h,
            x1:x1 + roi_w
        ]

        hsv = cv2.cvtColor(
            roi,
            cv2.COLOR_BGR2HSV
        )

        # -------------------------------------------------
        # MVP DEMO COLOR CLASSIFIER
        #
        # MOR   -> gold_like
        # YESIL -> diamond_like
        #
        # Beyaz arka plan düşük saturation nedeniyle
        # bu maskelere dahil edilmez.
        # -------------------------------------------------

        purple_mask = cv2.inRange(
            hsv,
            np.array([125, 60, 40], dtype=np.uint8),
            np.array([175, 255, 255], dtype=np.uint8)
        )

        green_mask = cv2.inRange(
            hsv,
            np.array([35, 60, 40], dtype=np.uint8),
            np.array([90, 255, 255], dtype=np.uint8)
        )

        purple_pixels = int(
            cv2.countNonZero(purple_mask)
        )

        green_pixels = int(
            cv2.countNonZero(green_mask)
        )

        total_pixels = (
            roi.shape[0] *
            roi.shape[1]
        )

        purple_percent = (
            100.0 *
            purple_pixels /
            total_pixels
        )

        green_percent = (
            100.0 *
            green_pixels /
            total_pixels
        )

        min_pixels = 1000

        # Hiçbir demo objesi yok
        if (
            purple_pixels < min_pixels
            and
            green_pixels < min_pixels
        ):
            return {
                "class": "unknown",
                "confidence": 0.20,
                "source": "imx219_color_demo",
                "features": {
                    "purple_pixels": purple_pixels,
                    "green_pixels": green_pixels,
                    "purple_percent": round(
                        purple_percent,
                        2
                    ),
                    "green_percent": round(
                        green_percent,
                        2
                    )
                }
            }

        # Mor baskinsa -> gold_like
        if purple_pixels > green_pixels:

            product_class = "gold_like"
            dominant_pixels = purple_pixels
            other_pixels = green_pixels

        # Yesil baskinsa -> diamond_like
        else:

            product_class = "diamond_like"
            dominant_pixels = green_pixels
            other_pixels = purple_pixels

        dominance = (
            dominant_pixels /
            max(
                dominant_pixels + other_pixels,
                1
            )
        )

        confidence = min(
            0.95,
            0.80 + 0.15 * dominance
        )

        return {
            "class": product_class,

            "confidence": round(
                float(confidence),
                3
            ),

            "source": "imx219_color_demo",

            "features": {
                "purple_pixels": purple_pixels,
                "green_pixels": green_pixels,

                "purple_percent": round(
                    purple_percent,
                    2
                ),

                "green_percent": round(
                    green_percent,
                    2
                ),

                "dominance": round(
                    dominance,
                    3
                )
            }
        }
