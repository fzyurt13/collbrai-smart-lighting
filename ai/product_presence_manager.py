class ProductPresenceManager:

    def __init__(self, required_absence_hits=5):
        self.required_absence_hits = int(
            required_absence_hits
        )
        self.absence_hits = 0

    def reset(self):
        self.absence_hits = 0

    def update(self, product_class):

        if product_class in (
            None,
            "",
            "unknown"
        ):
            self.absence_hits += 1

            return {
                "product_present": False,
                "absence_confirmed": (
                    self.absence_hits
                    >= self.required_absence_hits
                ),
                "absence_hits": self.absence_hits
            }

        self.reset()

        return {
            "product_present": True,
            "absence_confirmed": False,
            "absence_hits": 0
        }
