class AIDecisionManager:

    def __init__(self, confidence_threshold=0.80):
        self.confidence_threshold = float(
            confidence_threshold
        )

    def evaluate(self, prediction):
        if not prediction:
            return {
                "accepted": False,
                "product_class": "unknown",
                "confidence": 0.0,
                "reason": "empty_prediction"
            }

        product_class = prediction.get(
            "class",
            "unknown"
        )

        confidence = float(
            prediction.get("confidence", 0.0)
        )

        if confidence < self.confidence_threshold:
            return {
                "accepted": False,
                "product_class": "unknown",
                "confidence": confidence,
                "reason": "low_confidence"
            }

        if product_class in (
            None,
            "",
            "unknown"
        ):
            return {
                "accepted": False,
                "product_class": "unknown",
                "confidence": confidence,
                "reason": "unknown_product"
            }

        return {
            "accepted": True,
            "product_class": product_class,
            "confidence": confidence,
            "reason": "accepted"
        }
