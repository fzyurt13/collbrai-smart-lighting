from camera.imx219_camera import IMX219Camera


def create_camera(camera_type="mock"):
    camera_type = str(camera_type).lower()

    if camera_type == "mock":
        return None

    if camera_type == "imx219":
        return IMX219Camera()

    raise ValueError(
        "Unsupported camera type: {}".format(camera_type)
    )
