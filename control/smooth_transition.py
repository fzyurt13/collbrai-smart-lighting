class SmoothTransition:

    def __init__(
        self,
        cct_step=100.0,
        brightness_step=2.0
    ):
        self.cct_step = float(cct_step)
        self.brightness_step = float(
            brightness_step
        )

    def _move_towards(
        self,
        current,
        target,
        step
    ):
        current = float(current)
        target = float(target)

        if abs(target - current) <= step:
            return target

        if target > current:
            return current + step

        return current - step

    def update(
        self,
        current_cct,
        target_cct,
        current_brightness,
        target_brightness
    ):
        next_cct = self._move_towards(
            current=current_cct,
            target=target_cct,
            step=self.cct_step
        )

        next_brightness = self._move_towards(
            current=current_brightness,
            target=target_brightness,
            step=self.brightness_step
        )

        return {
            "target_cct": round(next_cct, 1),
            "target_brightness": round(
                next_brightness,
                1
            )
        }
