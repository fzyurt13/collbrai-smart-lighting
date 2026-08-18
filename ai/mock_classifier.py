from ai.base_classifier import ProductClassifier


class MockAIClassifier(ProductClassifier):

    def __init__(
        self,
        product_class="yellow_gold",
        confidence=1.0,
        sequence=None
    ):
        self.product_class = product_class
        self.confidence = float(confidence)

        self.sequence = sequence or []
        self.sequence_index = 0

    def predict(self, frame=None):

        if self.sequence:
            item = self.sequence[
                self.sequence_index
                % len(self.sequence)
            ]

            self.sequence_index += 1

            if isinstance(item, dict):
                return {
                    "class": item.get(
                        "class",
                        "unknown"
                    ),
                    "confidence": float(
                        item.get(
                            "confidence",
                            self.confidence
                        )
                    ),
                    "source": "mock_ai_sequence"
                }

            return {
                "class": str(item),
                "confidence": self.confidence,
                "source": "mock_ai_sequence"
            }

        return {
            "class": self.product_class,
            "confidence": self.confidence,
            "source": "mock_ai"
        }
