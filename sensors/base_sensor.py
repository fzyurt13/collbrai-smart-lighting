from abc import ABC, abstractmethod


class LightSensor(ABC):
    @abstractmethod
    def read(self):
        """
        Returns a dictionary containing at least:

        {
            "measured_cct": float,
            "measured_light_percent": float
        }
        """
        raise NotImplementedError
