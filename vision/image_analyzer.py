import cv2
import numpy as np


class ImageAnalyzer:

    def analyze(self, image):
        if image is None:
            raise ValueError("Image is None.")

        if len(image.shape) != 3:
            raise ValueError(
                "Expected BGR color image."
            )

        height, width, channels = image.shape

        gray = cv2.cvtColor(
            image,
            cv2.COLOR_BGR2GRAY
        )

        brightness_percent = (
            float(np.mean(gray))
            / 255.0
            * 100.0
        )

        contrast = float(
            np.std(gray)
        )

        mean_bgr = np.mean(
            image.reshape(-1, 3),
            axis=0
        )

        blue = float(mean_bgr[0])
        green = float(mean_bgr[1])
        red = float(mean_bgr[2])

        return {
            "width": int(width),
            "height": int(height),
            "channels": int(channels),
            "brightness_percent": round(
                brightness_percent,
                2
            ),
            "contrast": round(
                contrast,
                2
            ),
            "mean_blue": round(blue, 2),
            "mean_green": round(green, 2),
            "mean_red": round(red, 2)
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
