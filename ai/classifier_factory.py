from ai.mock_classifier import MockAIClassifier
from ai.imx219_classifier import IMX219ProductClassifier


def create_classifier(
    classifier_type="mock",
    product_class="yellow_gold",
    model_path=None,
    confidence=1.0
):
    classifier_type = str(classifier_type).lower()

    if classifier_type == "mock":
        return MockAIClassifier(
            product_class=product_class,
            confidence=confidence
        )

    if classifier_type == "imx219":
        return IMX219ProductClassifier(
            model_path=model_path
        )

    raise ValueError(
        "Unsupported classifier type: {}".format(
            classifier_type
        )
    )
