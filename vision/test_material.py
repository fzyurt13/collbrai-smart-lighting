import argparse

from vision.material_analyzer import MaterialAnalyzer


def main():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "image"
    )

    args = parser.parse_args()

    analyzer = MaterialAnalyzer()

    result = analyzer.analyze_file(
        args.image
    )

    print("=" * 60)
    print("COLLBRAI MATERIAL PRE-ANALYSIS")
    print("=" * 60)

    print("Image :", args.image)

    print(
        "Yellow-like       : {:.2f}%".format(
            result["yellow_like_percent"]
        )
    )

    print(
        "White-metal-like  : {:.2f}%".format(
            result["white_metal_like_percent"]
        )
    )

    print(
        "Bright/specular   : {:.2f}%".format(
            result["bright_specular_percent"]
        )
    )

    print(
        "Dark/background   : {:.2f}%".format(
            result["dark_background_percent"]
        )
    )


if __name__ == "__main__":
    main()
