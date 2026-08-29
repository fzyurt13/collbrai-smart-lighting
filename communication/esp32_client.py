import json
import socket
import time

import serial


class ESP32Client:

    def __init__(
        self,
        port="/dev/ttyACM0",
        baudrate=115200,
        timeout=0.3,
        startup_delay=1.0,
        transport="serial",
        host=None,
        tcp_port=5000,
        wifi_timeout=5.0
    ):
        self.port = port
        self.baudrate = int(baudrate)
        self.timeout = float(timeout)
        self.startup_delay = float(startup_delay)

        self.transport = str(
            transport
        ).lower()

        self.host = host
        self.tcp_port = int(
            tcp_port
        )

        self.wifi_timeout = float(
            wifi_timeout
        )

        self.serial = None

        if self.transport not in (
            "serial",
            "wifi"
        ):
            raise ValueError(
                "transport must be 'serial' or 'wifi'"
            )

        if (
            self.transport == "wifi"
            and not self.host
        ):
            raise ValueError(
                "host is required for Wi-Fi transport"
            )

    def connect(self):
        if self.transport == "wifi":
            # Wi-Fi bağlantısı komut başına açılır.
            return

        if (
            self.serial is not None
            and self.serial.is_open
        ):
            return

        self.serial = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout
        )

        time.sleep(
            self.startup_delay
        )

        self.serial.reset_input_buffer()

    def close(self):
        if self.serial is not None:
            if self.serial.is_open:
                self.serial.close()

        self.serial = None

    def _send_command_serial(
        self,
        command,
        wait_response=0.15
    ):
        self.connect()

        message = (
            str(command).strip()
            + "\n"
        )

        self.serial.write(
            message.encode("utf-8")
        )

        self.serial.flush()

        time.sleep(
            wait_response
        )

        responses = []

        while self.serial.in_waiting:
            line = self.serial.readline().decode(
                "utf-8",
                errors="replace"
            ).strip()

            if line:
                responses.append(
                    line
                )

        return responses

    def _send_command_wifi(
        self,
        command,
        wait_response=0.15
    ):
        # wait_response seri haberleşme ile API
        # uyumluluğu için korunuyor.
        del wait_response

        message = (
            str(command).strip()
            + "\n"
        ).encode("utf-8")

        with socket.create_connection(
            (
                self.host,
                self.tcp_port
            ),
            timeout=self.wifi_timeout
        ) as sock:

            sock.settimeout(
                self.wifi_timeout
            )

            sock.sendall(
                message
            )

            data = b""

            while b"\n" not in data:
                chunk = sock.recv(
                    4096
                )

                if not chunk:
                    break

                data += chunk

        responses = []

        for raw_line in data.splitlines():
            line = raw_line.decode(
                "utf-8",
                errors="replace"
            ).strip()

            if line:
                responses.append(
                    line
                )

        return responses

    def _send_command(
        self,
        command,
        wait_response=0.15
    ):
        if self.transport == "wifi":
            return self._send_command_wifi(
                command,
                wait_response=wait_response
            )

        return self._send_command_serial(
            command,
            wait_response=wait_response
        )

    def set_warm_cool(
        self,
        warm_percent,
        cool_percent
    ):
        warm_percent = max(
            0.0,
            min(
                100.0,
                float(warm_percent)
            )
        )

        cool_percent = max(
            0.0,
            min(
                100.0,
                float(cool_percent)
            )
        )

        command = (
            "WARM {:.1f} COOL {:.1f}".format(
                warm_percent,
                cool_percent
            )
        )

        return self._send_command(
            command
        )

    def off(self):
        return self._send_command(
            "OFF"
        )

    def status(self):
        return self._send_command(
            "STATUS"
        )

    def send_led_command(
        self,
        warm,
        cool,
        brightness
    ):
        warm = float(warm)
        cool = float(cool)

        brightness = max(
            0.0,
            min(
                100.0,
                float(brightness)
            )
        )

        total = warm + cool

        if total <= 0:
            return self.off()

        warm_ratio = (
            warm / total
        )

        cool_ratio = (
            cool / total
        )

        warm_percent = (
            warm_ratio
            * brightness
        )

        cool_percent = (
            cool_ratio
            * brightness
        )

        return self.set_warm_cool(
            warm_percent,
            cool_percent
        )

    def send_pwm_command(
        self,
        warm_pwm,
        cool_pwm
    ):
        warm_pwm = max(
            0,
            min(
                4095,
                int(warm_pwm)
            )
        )

        cool_pwm = max(
            0,
            min(
                4095,
                int(cool_pwm)
            )
        )

        warm_percent = (
            warm_pwm
            / 4095.0
            * 100.0
        )

        cool_percent = (
            cool_pwm
            / 4095.0
            * 100.0
        )

        return self.set_warm_cool(
            warm_percent,
            cool_percent
        )

    def read_spectral(self):
        responses = self._send_command(
            "SPECTRAL",
            wait_response=2.0
        )

        for line in responses:
            if line.startswith(
                "SPECTRAL "
            ):
                payload = line[
                    len("SPECTRAL "):
                ]

                return json.loads(
                    payload
                )

        raise RuntimeError(
            "No spectral response received from ESP32"
        )

    def health(self):
        responses = self.status()

        result = {
            "connected": True,
            "transport": self.transport,
            "responses": responses
        }

        if self.transport == "wifi":
            result["host"] = self.host
            result["tcp_port"] = self.tcp_port

        else:
            result["port"] = self.port

        return result
