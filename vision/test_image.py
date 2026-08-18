import argparse

from vision.image_analyzer import ImageAnalyzer


def parse_args():
    parser = argparse.ArgumentParser(
        description=(
            "Collbrai Jewelry Vision "
            "Image Analyzer"
        )
    )

    parser.add_argument(
        "image",
        help="Input image path"
    )

    return parser.parse_args()


def main():
    args = parse_args()

    analyzer = ImageAnalyzer()

    result = analyzer.analyze_file(
        args.image
    )

    print("=" * 60)
    print("COLLBRAI JEWELRY VISION")
    print("=" * 60)

    print("Image      :", args.image)

    print(
        "Resolution : {} x {}".format(
            result["width"],
            result["height"]
        )
    )

    print(
        "Brightness : {:.2f}%".format(
            result["brightness_percent"]
        )
    )

    print(
        "Contrast   : {:.2f}".format(
            result["contrast"]
        )
    )

    print(
        "Mean BGR   : {:.1f} / {:.1f} / {:.1f}".format(
            result["mean_blue"],
            result["mean_green"],
            result["mean_red"]
        )
    )


if __name__ == "__main__":
    main()
