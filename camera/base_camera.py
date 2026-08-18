from abc import ABC, abstractmethod


class CameraSource(ABC):

    @abstractmethod
    def open(self):
        """
        Initialize camera.
        Returns True when camera is ready.
        """
        raise NotImplementedError

    @abstractmethod
    def read(self):
        """
        Return a camera frame.

        Real IMX219 implementation will return
        an OpenCV/numpy image later.
        """
        raise NotImplementedError

    @abstractmethod
    def close(self):
        """
        Release camera resources.
        """
        raise NotImplementedError
