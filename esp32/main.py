from machine import Pin, I2C
from as7343 import AS7343
from device_config_manager import (
    load_runtime_config,
    get_or_create_setup_pin,
    save_wifi_config
)
from ble_provisioning import MeraledBLEProvisioning
import sys
import time
import json
import network
import socket
import select


runtime_config = load_runtime_config()

DEVICE_ID = runtime_config["device_id"]
PROVISIONED = runtime_config["provisioned"]
WIFI_SSID = runtime_config["wifi_ssid"]
WIFI_PASSWORD = runtime_config["wifi_password"]
TCP_PORT = runtime_config["tcp_port"]
CONFIG_SOURCE = runtime_config["source"]

SETUP_PIN = get_or_create_setup_pin()

ble_provisioning = None

try:
    ble_provisioning = MeraledBLEProvisioning(
        device_id=DEVICE_ID,
        setup_pin=SETUP_PIN,
        provisioned=PROVISIONED
    )

    ble_provisioning.start()

except Exception as exc:
    print(
        "BLE PROVISIONING ERROR:",
        repr(exc)
    )


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
    if not WIFI_SSID or WIFI_PASSWORD is None:
        raise RuntimeError(
            "WIFI NOT CONFIGURED"
        )

    print("DEVICE ID:", DEVICE_ID)
    print("CONFIG SOURCE:", CONFIG_SOURCE)

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


def try_provision_wifi(
    ssid,
    password,
    timeout_ms=15000
):
    if not ssid:
        raise ValueError(
            "WIFI SSID EMPTY"
        )

    if password is None:
        raise ValueError(
            "WIFI PASSWORD NONE"
        )

    candidate_wlan = network.WLAN(
        network.STA_IF
    )

    candidate_wlan.active(True)

    try:
        candidate_wlan.disconnect()
    except Exception:
        pass

    time.sleep_ms(250)

    print(
        "PROVISION WIFI CONNECTING:",
        ssid
    )

    candidate_wlan.connect(
        ssid,
        password
    )

    start = time.ticks_ms()

    while not candidate_wlan.isconnected():
        if (
            time.ticks_diff(
                time.ticks_ms(),
                start
            )
            > timeout_ms
        ):
            try:
                candidate_wlan.disconnect()
            except Exception:
                pass

            raise RuntimeError(
                "WIFI PROVISION TIMEOUT"
            )

        time.sleep_ms(250)

    ip_address = candidate_wlan.ifconfig()[0]

    print(
        "PROVISION WIFI CONNECTED:",
        ip_address
    )

    # Yalnızca gerçek bağlantı başarılı olduktan sonra
    # kimlik bilgilerini kalıcı olarak kaydet.
    save_wifi_config(
        ssid,
        password,
        TCP_PORT
    )

    return (
        candidate_wlan,
        ip_address
    )


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

        elif line.upper() == "DEVICE_INFO":
            return (
                "DEVICE_INFO ID={} PROVISIONED={} SOURCE={} PORT={}".format(
                    DEVICE_ID,
                    1 if PROVISIONED else 0,
                    CONFIG_SOURCE,
                    TCP_PORT
                )
            )

        elif line.upper() == "CAPABILITIES":
            try:
                import bluetooth
                ble_ok = 1
            except Exception:
                ble_ok = 0

            return (
                "CAPABILITIES WIFI=1 BLE={} TCP=1".format(
                    ble_ok
                )
            )

        elif line.upper() == "HEALTH":
            devices = i2c.scan()

            pca_ok = 0x40 in devices
            as7343_ok = 0x39 in devices

            return (
                "HEALTH ESP32=1 PCA9685={} AS7343={}".format(
                    1 if pca_ok else 0,
                    1 if as7343_ok else 0
                )
            )

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

wlan = None
tcp_server = None

try:
    wlan = connect_wifi()

    if wlan is not None and wlan.isconnected():
        tcp_server = create_tcp_server()

except Exception as exc:
    print(
        "WIFI STARTUP SKIPPED:",
        repr(exc)
    )

    wlan = None
    tcp_server = None

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
        # BLE uzerinden yeni Wi-Fi kurulum istegi geldiyse
        # GATT IRQ icinde bloklamadan burada isle.
        if ble_provisioning is not None:
            wifi_request = (
                ble_provisioning
                    .take_wifi_connect_request()
            )

            if wifi_request is not None:
                conn_handle = wifi_request[
                    "conn_handle"
                ]

                new_ssid = wifi_request[
                    "ssid"
                ]

                new_password = wifi_request[
                    "password"
                ]

                ble_provisioning.set_wifi_status(
                    conn_handle,
                    "WIFI_CONNECTING"
                )

                # Eski TCP baglantisini temizle.
                if client_socket is not None:
                    try:
                        client_socket.close()
                    except Exception:
                        pass

                    client_socket = None
                    client_buffer = b""

                if tcp_server is not None:
                    try:
                        tcp_server.close()
                    except Exception:
                        pass

                    tcp_server = None

                try:
                    (
                        wlan,
                        wifi_ip
                    ) = try_provision_wifi(
                        new_ssid,
                        new_password
                    )

                    tcp_server = (
                        create_tcp_server()
                    )

                    PROVISIONED = True
                    CONFIG_SOURCE = (
                        "device_config"
                    )

                    ble_provisioning.mark_provisioned(
                        conn_handle
                    )

                    ble_provisioning.set_wifi_status(
                        conn_handle,
                        "WIFI_CONNECTED={}".format(
                            wifi_ip
                        )
                    )

                    print(
                        "BLE WIFI PROVISION SUCCESS",
                        wifi_ip
                    )

                except Exception as exc:
                    ble_provisioning.set_wifi_status(
                        conn_handle,
                        "WIFI_FAILED"
                    )

                    print(
                        "BLE WIFI PROVISION FAILED:",
                        repr(exc)
                    )

        # USB Serial komutlari calismaya devam eder,
        # ancak Wi-Fi/TCP dongusunu bloklamaz.
        if stdin_poll.poll(0):
            line = sys.stdin.readline()

            if line:
                response = process_command(line)

                if response:
                    print(response)

        # Yeni TCP istemcisi kabul et.
        # Wi-Fi henuz provision edilmediyse TCP sunucusu olmayabilir.
        if (
            tcp_server is not None
            and client_socket is None
        ):
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
