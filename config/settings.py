MODE = "real"

# -------------------------------------------------
# ESP32 PRODUCT CONNECTION
# -------------------------------------------------
# Normal product operation uses Wi-Fi.
# ESP32 is connected to the same local network as Jetson.
ESP32_TRANSPORT = "wifi"
ESP32_HOST = "192.168.1.32"
ESP32_TCP_PORT = 5000
ESP32_TIMEOUT = 2.0

TARGET_CCT = 5000.0
CCT_TOLERANCE = 20.0
CONTROL_STEP = 2.0

START_WARM = 70.0
START_COOL = 30.0
BRIGHTNESS = 80.0

TARGET_BRIGHTNESS = 70.0
BRIGHTNESS_TOLERANCE = 1.0
START_BRIGHTNESS = 40.0
