from abc import ABC, abstractmethod


class ProductClassifier(ABC):

    @abstractmethod
    def predict(self, frame=None):
        """
        Expected return:

        {
            "class": str,
            "confidence": float,
            "source": str
        }
        """
        raise NotImplementedError
