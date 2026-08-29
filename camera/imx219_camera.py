from camera.base_camera import CameraSource

import cv2


class IMX219Camera(CameraSource):

    def __init__(
        self,
        width=1280,
        height=720,
        fps=30,
        sensor_id=0
    ):
        self.width = int(width)
        self.height = int(height)
        self.fps = int(fps)
        self.sensor_id = int(sensor_id)

        self.connected = False
        self.capture = None

    def _gstreamer_pipeline(self):
        return (
            "nvarguscamerasrc sensor-id={} ! "
            "video/x-raw(memory:NVMM),"
            "width=(int){},"
            "height=(int){},"
            "format=(string)NV12,"
            "framerate=(fraction){}/1 ! "
            "nvvidconv ! "
            "video/x-raw,format=(string)BGRx ! "
            "videoconvert ! "
            "video/x-raw,format=(string)BGR ! "
            "appsink drop=true max-buffers=1 sync=false"
        ).format(
            self.sensor_id,
            self.width,
            self.height,
            self.fps
        )

    def open(self):
        if self.connected:
            return

        pipeline = self._gstreamer_pipeline()

        print("Opening IMX219 camera...")
        print(
            "Resolution: {}x{} @ {} FPS".format(
                self.width,
                self.height,
                self.fps
            )
        )

        self.capture = cv2.VideoCapture(
            pipeline,
            cv2.CAP_GSTREAMER
        )

        if not self.capture.isOpened():
            self.capture = None

            raise RuntimeError(
                "Could not open IMX219 through "
                "NVIDIA Argus/GStreamer."
            )

        self.connected = True

        print("IMX219 CAMERA READY")

    def read(self):
        if not self.connected or self.capture is None:
            raise RuntimeError(
                "IMX219 camera is not open."
            )

        ok, frame = self.capture.read()

        if not ok or frame is None:
            raise RuntimeError(
                "Could not read frame from IMX219."
            )

        return frame

    def close(self):
        if self.capture is not None:
            self.capture.release()

        self.capture = None
        self.connected = False
