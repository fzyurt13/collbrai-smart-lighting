from camera.base_camera import CameraSource


class IMX219Camera(CameraSource):

    def __init__(
        self,
        width=1280,
        height=720,
        fps=30
    ):
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)

        self.connected = False
        self.capture = None

    def open(self):
        raise NotImplementedError(
            "IMX219 camera is not connected yet."
        )

    def read(self):
        if not self.connected:
            raise RuntimeError(
                "IMX219 camera is not open."
            )

        raise NotImplementedError(
            "IMX219 frame capture is not implemented yet."
        )

    def close(self):
        self.capture = None
        self.connected = False
