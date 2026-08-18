import csv
from datetime import datetime
from pathlib import Path


class DataLogger:
    def __init__(self, log_dir="logs"):
        log_dir = Path(log_dir)
        log_dir.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        self.path = log_dir / (
            "lighting_session_{}.csv".format(timestamp)
        )

        self.file = self.path.open("w", newline="")
        self.writer = csv.writer(self.file)

        self.writer.writerow([
            "timestamp",
            "iteration",
            "target_cct",
            "measured_cct",
            "cct_error",
            "target_brightness",
            "measured_brightness",
            "brightness_error",
            "warm_mix_percent",
            "cool_mix_percent",
            "global_brightness_percent",
            "warm_output_percent",
            "cool_output_percent",
            "warm_pwm",
            "cool_pwm"
        ])

        self.file.flush()

    def log(
        self,
        iteration,
        target_cct,
        measured_cct,
        cct_error,
        target_brightness,
        measured_brightness,
        brightness_error,
        warm,
        cool,
        brightness,
        pwm
    ):
        self.writer.writerow([
            datetime.now().isoformat(),
            iteration,
            round(target_cct, 2),
            round(measured_cct, 2),
            round(cct_error, 2),
            round(target_brightness, 2),
            round(measured_brightness, 2),
            round(brightness_error, 2),
            round(warm, 2),
            round(cool, 2),
            round(brightness, 2),
            pwm["warm_percent"],
            pwm["cool_percent"],
            pwm["warm_pwm"],
            pwm["cool_pwm"]
        ])

        self.file.flush()

    def close(self):
        self.file.close()
