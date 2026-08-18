class SystemStateManager:

    STANDBY = "STANDBY"
    PRODUCT_DETECTED = "PRODUCT_DETECTED"
    PRODUCT_CONFIRMED = "PRODUCT_CONFIRMED"
    TRANSITIONING = "TRANSITIONING"
    TRACKING = "TRACKING"

    def __init__(self):
        self.state = self.STANDBY
        self.active_product = None

    def _change_state(self, new_state):
        old_state = self.state
        changed = old_state != new_state

        self.state = new_state

        return {
            "changed": changed,
            "old_state": old_state,
            "new_state": new_state,
            "active_product": self.active_product
        }

    def product_detected(self, product_class):
        if product_class in (
            None,
            "",
            "unknown"
        ):
            return {
                "changed": False,
                "old_state": self.state,
                "new_state": self.state,
                "active_product": self.active_product
            }

        if self.active_product == product_class:
            return {
                "changed": False,
                "old_state": self.state,
                "new_state": self.state,
                "active_product": self.active_product
            }

        return self._change_state(
            self.PRODUCT_DETECTED
        )

    def confirm_product(self, product_class):
        self.active_product = product_class

        return self._change_state(
            self.PRODUCT_CONFIRMED
        )

    def start_transition(self):
        return self._change_state(
            self.TRANSITIONING
        )

    def transition_completed(self):
        return self._change_state(
            self.TRACKING
        )

    def clear_product(self):
        self.active_product = None

        return self._change_state(
            self.STANDBY
        )

    def get_state(self):
        return {
            "state": self.state,
            "active_product": self.active_product
        }
