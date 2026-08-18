from ai.base_classifier import ProductClassifier


class IMX219ProductClassifier(ProductClassifier):

    def __init__(self, model_path=None):
        self.model_path = model_path
        self.model = None

    def load_model(self):
        raise NotImplementedError(
            "Real AI model is not available yet."
        )

    def predict(self, frame=None):

        if frame is None:
            raise ValueError(
                "Camera frame is required."
            )

        if self.model is None:
            raise RuntimeError(
                "AI model is not loaded."
            )

        raise NotImplementedError(
            "Real IMX219 inference is not implemented yet."
        )
