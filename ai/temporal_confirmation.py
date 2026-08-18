class TemporalConfirmation:

    def __init__(self, required_hits=3):
        self.required_hits = int(required_hits)

        self.last_class = None
        self.hit_count = 0
        self.confirmed_class = None

    def reset(self):
        self.last_class = None
        self.hit_count = 0
        self.confirmed_class = None

    def update(self, product_class):
        if product_class in (
            None,
            "",
            "unknown"
        ):
            self.reset()

            return {
                "confirmed": False,
                "product_class": "unknown",
                "hits": 0
            }

        if product_class == self.last_class:
            self.hit_count += 1
        else:
            self.last_class = product_class
            self.hit_count = 1

        if self.hit_count >= self.required_hits:
            self.confirmed_class = product_class

            return {
                "confirmed": True,
                "product_class": product_class,
                "hits": self.hit_count
            }

        return {
            "confirmed": False,
            "product_class": product_class,
            "hits": self.hit_count
        }
