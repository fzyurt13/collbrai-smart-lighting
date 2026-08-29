from machine import Pin, I2C
from as7343 import AS7343
from wifi_config import WIFI_SSID, WIFI_PASSWORD, TCP_PORT
import sys
import time
import json
import network
import socket
import select


PCA_ADDR = 0x40

CH_WARM = 0
CH_COOL = 1

SDA_PIN = 8
SCL_PIN = 9


i2c = I2C(
    0,
    scl=Pin(SCL_PIN),
    sda=Pin(SDA_PIN),
    freq=100000
)

sensor = AS7343(i2c)


def pca_init():
    devices = i2c.scan()

    print("I2C:", devices)

    if PCA_ADDR not in devices:
        raise RuntimeError(
            "PCA9685 not found at 0x40"
        )

    i2c.writeto_mem(
        PCA_ADDR,
        0x00,
        b'\x10'
    )

    i2c.writeto_mem(
        PCA_ADDR,
        0xFE,
        b'\x0e'
    )

    i2c.writeto_mem(
        PCA_ADDR,
        0x01,
        b'\x04'
    )

    i2c.writeto_mem(
        PCA_ADDR,
        0x00,
        b'\x20'
    )

    time.sleep_ms(2)


def sensor_init():
    sensor.begin()
    print("AS7343 READY 0x39")


def channel_register(channel):
    return 0x06 + (4 * channel)


def set_channel(channel, percent):
    percent = max(
        0.0,
        min(100.0, float(percent))
    )

    reg = channel_register(channel)

    if percent <= 0:
        data = b'\x00\x00\x00\x10'

    elif percent >= 100:
        data = b'\x00\x10\x00\x00'

    else:
        value = int(
            4095 * percent / 100.0
        )

        data = bytes([
            0,
            0,
            value & 0xFF,
            (value >> 8) & 0x0F
        ])

    i2c.writeto_mem(
        PCA_ADDR,
        reg,
        data
    )


def set_warm_cool(
    warm_percent,
    cool_percent
):
    set_channel(
        CH_WARM,
        warm_percent
    )

    set_channel(
        CH_COOL,
        cool_percent
    )

    print(
        "OK WARM={:.1f} COOL={:.1f}".format(
            float(warm_percent),
            float(cool_percent)
        )
    )


def all_off():
    set_warm_cool(0, 0)


def read_spectral():
    data = sensor.read_channels()

    print(
        "SPECTRAL " +
        json.dumps(data)
    )



def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)

    if wlan.isconnected():
        print("WIFI ALREADY CONNECTED")
        print("WIFI IP:", wlan.ifconfig()[0])
        return wlan

    print("WIFI CONNECTING...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    timeout_ms = 15000
    start = time.ticks_ms()

    while not wlan.isconnected():
        if time.ticks_diff(time.ticks_ms(), start) > timeout_ms:
            raise RuntimeError("WIFI CONNECTION TIMEOUT")

        time.sleep_ms(250)

    print("WIFI CONNECTED")
    print("WIFI IP:", wlan.ifconfig()[0])

    return wlan


def create_tcp_server():
    addr = socket.getaddrinfo(
        "0.0.0.0",
        TCP_PORT
    )[0][-1]

    server = socket.socket()

    try:
        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )
    except Exception:
        pass

    server.bind(addr)
    server.listen(1)
    server.settimeout(0.05)

    print(
        "TCP SERVER READY PORT={}".format(
            TCP_PORT
        )
    )

    return server


def process_command(line):
    line = line.strip()

    if not line:
        return None

    parts = line.split()

    try:
        if (
            len(parts) == 4
            and parts[0].upper() == "WARM"
            and parts[2].upper() == "COOL"
        ):
            warm = float(parts[1])
            cool = float(parts[3])

            set_channel(CH_WARM, warm)
            set_channel(CH_COOL, cool)

            return "OK WARM={:.1f} COOL={:.1f}".format(
                warm,
                cool
            )

        elif line.upper() == "OFF":
            set_channel(CH_WARM, 0)
            set_channel(CH_COOL, 0)

            return "OK WARM=0.0 COOL=0.0"

        elif line.upper() == "STATUS":
            return "STATUS READY PCA=0x40 AS7343=0x39"

        elif line.upper() == "SPECTRAL":
            data = sensor.read_channels()

            return (
                "SPECTRAL " +
                json.dumps(data)
            )

        else:
            return "ERROR COMMAND"

    except Exception as exc:
        return "ERROR {}".format(exc)


pca_init()
sensor_init()
all_off()

print(
    "COLLBRAI ESP32 LIGHT CONTROLLER READY"
)

wlan = connect_wifi()
tcp_server = create_tcp_server()

client_socket = None
client_buffer = b""

# USB seri portu bloklamadan kontrol et
stdin_poll = select.poll()
stdin_poll.register(
    sys.stdin,
    select.POLLIN
)

while True:
    try:
        # USB Serial komutlari calismaya devam eder,
        # ancak Wi-Fi/TCP dongusunu bloklamaz.
        if stdin_poll.poll(0):
            line = sys.stdin.readline()

            if line:
                response = process_command(line)

                if response:
                    print(response)

        # Yeni TCP istemcisi kabul et
        if client_socket is None:
            try:
                client_socket, client_addr = tcp_server.accept()
                client_socket.settimeout(0.05)
                client_buffer = b""

                print(
                    "TCP CLIENT CONNECTED",
                    client_addr
                )

            except OSError:
                pass

        # TCP komutlarini oku
        if client_socket is not None:
            try:
                data = client_socket.recv(256)

                if not data:
                    client_socket.close()
                    client_socket = None
                    client_buffer = b""
                    print("TCP CLIENT DISCONNECTED")

                else:
                    client_buffer += data

                    while b"\n" in client_buffer:
                        raw_line, client_buffer = client_buffer.split(
                            b"\n",
                            1
                        )

                        command = raw_line.decode(
                            "utf-8"
                        ).strip()

                        if command:
                            print(
                                "TCP COMMAND:",
                                command
                            )

                            response = process_command(
                                command
                            )

                            if response:
                                client_socket.send(
                                    (
                                        response + "\n"
                                    ).encode("utf-8")
                                )

            except OSError:
                pass

    except Exception as exc:
        print(
            "LOOP ERROR",
            exc
        )
        time.sleep_ms(100)
