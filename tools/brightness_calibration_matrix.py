import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from communication.esp32_client import ESP32Client
import time
import csv
from datetime import datetime


PORT = "/dev/ttyACM0"

CCT_POINTS = [
    3500,
    4200,
    5000,
    6000,
]

BRIGHTNESS_POINTS = [
    25,
    50,
    75,
    100,
]

MIN_CCT = 3000.0
MAX_CCT = 6500.0

STABILIZATION_TIME = 1.5
SAMPLE_COUNT = 5
SAMPLE_DELAY = 0.25


def cct_to_mix(cct):
    cool_ratio = (
        float(cct) - MIN_CCT
    ) / (
        MAX_CCT - MIN_CCT
    )

    cool_ratio = max(
        0.0,
        min(1.0, cool_ratio)
    )

    cool = cool_ratio * 100.0
    warm = 100.0 - cool

    return warm, cool


def main():
    esp32 = ESP32Client(
        port=PORT,
        baudrate=115200,
        timeout=0.3,
        startup_delay=1.0
    )

    timestamp = datetime.now().strftime(
        "%Y%m%d_%H%M%S"
    )

    output_file = (
        "logs/"
        "brightness_calibration_"
        + timestamp
        + ".csv"
    )

    results = []

    print("=" * 72)
    print("COLLBRAI AS7343 BRIGHTNESS CALIBRATION MATRIX")
    print("=" * 72)

    try:
        print()
        print("ESP32 HEALTH:")
        print(esp32.health())

        for cct in CCT_POINTS:

            mix_warm, mix_cool = cct_to_mix(cct)

            print()
            print("=" * 72)
            print(
                "CCT: {} K | MIX WARM {:.2f}% / COOL {:.2f}%".format(
                    cct,
                    mix_warm,
                    mix_cool
                )
            )
            print("=" * 72)

            for brightness in BRIGHTNESS_POINTS:

                warm_output = (
                    mix_warm
                    * brightness
                    / 100.0
                )

                cool_output = (
                    mix_cool
                    * brightness
                    / 100.0
                )

                print()
                print(
                    "TARGET {} K / {}%".format(
                        cct,
                        brightness
                    )
                )

                print(
                    "COMMAND WARM {:.2f}% / COOL {:.2f}%".format(
                        warm_output,
                        cool_output
                    )
                )

                esp32.set_warm_cool(
                    warm_output,
                    cool_output
                )

                time.sleep(
                    STABILIZATION_TIME
                )

                # İlk spektral okuma stale olabildiği için at.
                esp32.read_spectral()

                vis_samples = []

                for sample_number in range(
                    1,
                    SAMPLE_COUNT + 1
                ):
                    spectrum = (
                        esp32.read_spectral()
                    )

                    vis = spectrum["VIS"]

                    vis_samples.append(
                        vis
                    )

                    print(
                        "  Sample {}: VIS={}".format(
                            sample_number,
                            vis
                        )
                    )

                    time.sleep(
                        SAMPLE_DELAY
                    )

                average_vis = (
                    sum(vis_samples)
                    / len(vis_samples)
                )

                min_vis = min(
                    vis_samples
                )

                max_vis = max(
                    vis_samples
                )

                print(
                    "  AVG VIS : {:.1f}".format(
                        average_vis
                    )
                )

                results.append({
                    "cct": cct,
                    "brightness": brightness,
                    "warm_mix": mix_warm,
                    "cool_mix": mix_cool,
                    "warm_output": warm_output,
                    "cool_output": cool_output,
                    "vis_average": average_vis,
                    "vis_min": min_vis,
                    "vis_max": max_vis,
                })

        print()
        print("=" * 72)
        print("CALIBRATION MATRIX")
        print("=" * 72)

        print(
            "{:<8} {:>8} {:>12}".format(
                "CCT",
                "BRIGHT",
                "AVG VIS"
            )
        )

        for row in results:
            print(
                "{:<8} {:>7.0f}% {:>12.1f}".format(
                    row["cct"],
                    row["brightness"],
                    row["vis_average"]
                )
            )

        with open(
            output_file,
            "w",
            newline=""
        ) as file:
            writer = csv.DictWriter(
                file,
                fieldnames=[
                    "cct",
                    "brightness",
                    "warm_mix",
                    "cool_mix",
                    "warm_output",
                    "cool_output",
                    "vis_average",
                    "vis_min",
                    "vis_max",
                ]
            )

            writer.writeheader()
            writer.writerows(
                results
            )

        print()
        print(
            "CSV SAVED:",
            output_file
        )

    finally:
        try:
            esp32.set_warm_cool(
                0,
                0
            )
            print()
            print("LED OFF")

        finally:
            esp32.close()


if __name__ == "__main__":
    main()
