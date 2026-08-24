import json
import urllib.request
import urllib.error


class ESP32Client:
    def __init__(self, host="192.168.4.1", timeout=2.0):
        self.base_url = "http://{}".format(host)
        self.timeout = timeout

    def send_led_command(self, warm, cool, brightness):
        url = self.base_url + "/led"

        payload = {
            "warm": float(warm),
            "cool": float(cool),
            "brightness": float(brightness)
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout
            ) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "ESP32 connection failed: {}".format(exc)
            )

    def send_pwm_command(self, warm_pwm, cool_pwm):
        url = self.base_url + "/pwm"

        payload = {
            "warm_pwm": int(warm_pwm),
            "cool_pwm": int(cool_pwm)
        }

        data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout
            ) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "ESP32 PWM command failed: {}".format(exc)
            )

    def read_spectral(self):
        url = self.base_url + "/spectral"

        try:
            with urllib.request.urlopen(
                url,
                timeout=self.timeout
            ) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "ESP32 spectral read failed: {}".format(exc)
            )

    def health(self):
        url = self.base_url + "/health"

        try:
            with urllib.request.urlopen(
                url,
                timeout=self.timeout
            ) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)

        except urllib.error.URLError as exc:
            raise RuntimeError(
                "ESP32 health check failed: {}".format(exc)
            )
