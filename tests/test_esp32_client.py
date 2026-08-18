from communication.esp32_client import ESP32Client


client = ESP32Client(
    host="192.168.4.1",
    timeout=1.0
)

try:
    result = client.health()
    print("ESP32 ONLINE")
    print(result)

except RuntimeError as exc:
    print("ESP32 currently unavailable.")
    print(exc)
