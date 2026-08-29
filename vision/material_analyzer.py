import cv2
import numpy as np


class MaterialAnalyzer:

    def _center_roi(
        self,
        image,
        width_ratio=0.70,
        height_ratio=0.70
    ):
        height, width = image.shape[:2]

        roi_width = int(
            width * float(width_ratio)
        )

        roi_height = int(
            height * float(height_ratio)
        )

        x1 = max(
            0,
            (width - roi_width) // 2
        )

        y1 = max(
            0,
            (height - roi_height) // 2
        )

        x2 = min(
            width,
            x1 + roi_width
        )

        y2 = min(
            height,
            y1 + roi_height
        )

        roi = image[
            y1:y2,
            x1:x2
        ]

        return roi, {
            "x1": x1,
            "y1": y1,
            "x2": x2,
            "y2": y2
        }

    def analyze(
        self,
        image,
        use_roi=True,
        roi_width_ratio=0.70,
        roi_height_ratio=0.70,
        object_gray_threshold=100
    ):
        if image is None:
            raise ValueError(
                "Image is None."
            )

        if use_roi:
            analysis_image, roi = (
                self._center_roi(
                    image,
                    width_ratio=roi_width_ratio,
                    height_ratio=roi_height_ratio
                )
            )
        else:
            analysis_image = image
            roi = {
                "x1": 0,
                "y1": 0,
                "x2": image.shape[1],
                "y2": image.shape[0]
            }

        gray = cv2.cvtColor(
            analysis_image,
            cv2.COLOR_BGR2GRAY
        )

        object_mask = cv2.inRange(
            gray,
            0,
            int(object_gray_threshold)
        )

        object_pixels = cv2.countNonZero(
            object_mask
        )

        total_roi_pixels = float(
            analysis_image.shape[0]
            * analysis_image.shape[1]
        )

        object_percent = (
            object_pixels
            / total_roi_pixels
            * 100.0
        )

        if object_pixels == 0:
            return {
                "yellow_like_percent": 0.0,
                "white_metal_like_percent": 0.0,
                "bright_specular_percent": 0.0,
                "dark_background_percent": 0.0,
                "object_percent": 0.0,
                "object_pixels": 0,
                "roi": roi,
                "roi_width": analysis_image.shape[1],
                "roi_height": analysis_image.shape[0]
            }

        hsv = cv2.cvtColor(
            analysis_image,
            cv2.COLOR_BGR2HSV
        )

        yellow_mask = cv2.inRange(
            hsv,
            np.array([15, 60, 60]),
            np.array([40, 255, 255])
        )

        white_mask = cv2.inRange(
            hsv,
            np.array([0, 0, 120]),
            np.array([179, 70, 255])
        )

        bright_mask = cv2.inRange(
            hsv,
            np.array([0, 0, 220]),
            np.array([179, 255, 255])
        )

        dark_mask = cv2.inRange(
            hsv,
            np.array([0, 0, 0]),
            np.array([179, 255, 60])
        )

        yellow_mask = cv2.bitwise_and(
            yellow_mask,
            object_mask
        )

        white_mask = cv2.bitwise_and(
            white_mask,
            object_mask
        )

        bright_mask = cv2.bitwise_and(
            bright_mask,
            object_mask
        )

        dark_mask = cv2.bitwise_and(
            dark_mask,
            object_mask
        )

        yellow_ratio = (
            cv2.countNonZero(
                yellow_mask
            )
            / float(object_pixels)
            * 100.0
        )

        white_ratio = (
            cv2.countNonZero(
                white_mask
            )
            / float(object_pixels)
            * 100.0
        )

        bright_ratio = (
            cv2.countNonZero(
                bright_mask
            )
            / float(object_pixels)
            * 100.0
        )

        dark_ratio = (
            cv2.countNonZero(
                dark_mask
            )
            / float(object_pixels)
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
            ),
            "object_percent": round(
                object_percent,
                2
            ),
            "object_pixels": int(
                object_pixels
            ),
            "roi": roi,
            "roi_width": analysis_image.shape[1],
            "roi_height": analysis_image.shape[0]
        }

    def analyze_file(
        self,
        image_path,
        use_roi=True
    ):
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

        return self.analyze(
            image,
            use_roi=use_roi
        )
