from flask import Flask, jsonify, render_template, request, redirect
import subprocess
import os
import tempfile
import ipaddress

from communication.esp32_client import ESP32Client
from communication.esp32_runtime import get_esp32_client
from communication.esp32_endpoint_store import (
    save_esp32_endpoint,
)

try:
    from web.system_state import system_state
except ModuleNotFoundError:
    from system_state import system_state


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/splash")
def splash():
    return render_template("splash.html")


# MERALED_NO_CLASSIC_LOGIN_V1
@app.route("/login")
def login():
    return redirect("/")


@app.route("/setup")
def setup():
    return render_template("setup.html")


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/profile")
def profile():
    return redirect("/settings")


@app.route("/api/login", methods=["POST"])
def api_login_disabled():
    return jsonify({
        "ok": False,
        "error": "Classic login is disabled"
    }), 410


@app.route("/api/change-pin", methods=["POST"])
def api_change_pin_disabled():
    return jsonify({
        "ok": False,
        "error": "PIN authentication is disabled"
    }), 410



# MERALED_WIFI_SCAN_API_V2
WIFI_TRANSITION_INTERFACE = "wlP1p1s0"


def _split_nmcli_terse_line(line):
    parts = []
    current = []
    escaped = False

    for char in line:
        if escaped:
            current.append(char)
            escaped = False
            continue

        if char == "\\":
            escaped = True
            continue

        if char == ":":
            parts.append("".join(current))
            current = []
            continue

        current.append(char)

    parts.append("".join(current))
    return parts


def _get_wifi_scan_interfaces():
    try:
        result = subprocess.run(
            [
                "nmcli",
                "-t",
                "-f",
                "DEVICE,TYPE",
                "device",
                "status",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )

    except Exception:
        return [
            WIFI_TRANSITION_INTERFACE
        ]

    interfaces = []

    for raw_line in result.stdout.splitlines():
        parts = _split_nmcli_terse_line(
            raw_line
        )

        if len(parts) != 2:
            continue

        device = parts[0].strip()
        device_type = parts[1].strip()

        if (
            device_type == "wifi"
            and device
            and not device.startswith("p2p-")
        ):
            interfaces.append(device)

    # Geçiş adaptörünü ilk sırada tut.
    if WIFI_TRANSITION_INTERFACE in interfaces:
        interfaces.remove(
            WIFI_TRANSITION_INTERFACE
        )

        interfaces.insert(
            0,
            WIFI_TRANSITION_INTERFACE
        )

    return interfaces


@app.route("/api/wifi/scan")
def api_wifi_scan():

    scan_interfaces = (
        _get_wifi_scan_interfaces()
    )

    networks_by_ssid = {}
    successful_interfaces = []
    scan_errors = []


    for interface in scan_interfaces:

        try:
            subprocess.run(
                [
                    "nmcli",
                    "device",
                    "wifi",
                    "rescan",
                    "ifname",
                    interface,
                ],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=6,
                check=False,
            )

            result = subprocess.run(
                [
                    "nmcli",
                    "-t",
                    "-f",
                    (
                        "IN-USE,SSID,BSSID,"
                        "CHAN,FREQ,SIGNAL,SECURITY"
                    ),
                    "device",
                    "wifi",
                    "list",
                    "ifname",
                    interface,
                ],
                capture_output=True,
                text=True,
                timeout=6,
                check=True,
            )

            successful_interfaces.append(
                interface
            )

        except Exception as exc:
            scan_errors.append({
                "interface": interface,
                "error": str(exc),
            })

            continue


        for raw_line in result.stdout.splitlines():

            if not raw_line.strip():
                continue

            parts = _split_nmcli_terse_line(
                raw_line
            )

            if len(parts) != 7:
                continue

            (
                in_use,
                ssid,
                bssid,
                channel,
                frequency,
                signal,
                security,
            ) = parts

            ssid = ssid.strip()

            if not ssid or ssid == "--":
                continue


            try:
                signal_value = int(
                    signal
                )
            except (TypeError, ValueError):
                signal_value = 0


            try:
                channel_value = int(
                    channel
                )
            except (TypeError, ValueError):
                channel_value = None


            try:
                frequency_value = int(
                    frequency
                    .replace(" MHz", "")
                    .strip()
                )
            except (TypeError, ValueError):
                frequency_value = None


            connected = (
                in_use.strip() == "*"
            )


            # MERALED_WIFI_TRANSITION_VISIBILITY_V1
            transition_visible = (
                interface
                == WIFI_TRANSITION_INTERFACE
            )

            network = {
                "ssid": ssid,
                "bssid": bssid,
                "signal": signal_value,
                "security": (
                    security.strip()
                    or "OPEN"
                ),
                "channel": channel_value,
                "frequency_mhz": (
                    frequency_value
                ),
                "connected": connected,
                "source_interface": interface,
                "transition_visible": (
                    transition_visible
                ),
                "transition_signal": (
                    signal_value
                    if transition_visible
                    else None
                ),
            }


            previous = (
                networks_by_ssid.get(
                    ssid
                )
            )


            if (
                previous is not None
                and transition_visible
            ):
                previous[
                    "transition_visible"
                ] = True

                old_transition_signal = (
                    previous.get(
                        "transition_signal"
                    )
                )

                if (
                    old_transition_signal is None
                    or signal_value
                    > old_transition_signal
                ):
                    previous[
                        "transition_signal"
                    ] = signal_value


            use_new = False

            if previous is None:
                use_new = True

            elif (
                connected
                and not previous["connected"]
            ):
                use_new = True

            elif (
                connected
                == previous["connected"]
                and signal_value
                > previous["signal"]
            ):
                use_new = True


            if use_new:

                if previous is not None:

                    network[
                        "transition_visible"
                    ] = bool(
                        transition_visible
                        or previous.get(
                            "transition_visible",
                            False
                        )
                    )

                    previous_transition_signal = (
                        previous.get(
                            "transition_signal"
                        )
                    )

                    if (
                        network[
                            "transition_signal"
                        ]
                        is None
                    ):
                        network[
                            "transition_signal"
                        ] = (
                            previous_transition_signal
                        )

                    elif (
                        previous_transition_signal
                        is not None
                        and previous_transition_signal
                        > network[
                            "transition_signal"
                        ]
                    ):
                        network[
                            "transition_signal"
                        ] = (
                            previous_transition_signal
                        )

                networks_by_ssid[
                    ssid
                ] = network


    if (
        not successful_interfaces
        and scan_errors
    ):
        return jsonify({
            "ok": False,
            "error": "Wi-Fi scan failed",
            "interfaces": scan_interfaces,
            "details": scan_errors,
        }), 500


    networks = sorted(
        networks_by_ssid.values(),
        key=lambda item: (
            not item["connected"],
            -item["signal"],
        ),
    )


    return jsonify({
        "ok": True,
        "count": len(networks),
        "networks": networks,
        "scan_interfaces": (
            successful_interfaces
        ),
        "transition_interface": (
            WIFI_TRANSITION_INTERFACE
        ),
    })



# MERALED_WIFI_TEST_CONNECT_API_V1
WIFI_TRANSITION_PROFILE = "MERALED-TRANSITION-TEST"


def _cleanup_wifi_transition():
    subprocess.run(
        [
            "nmcli",
            "device",
            "disconnect",
            WIFI_TRANSITION_INTERFACE,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=False,
    )

    subprocess.run(
        [
            "nmcli",
            "connection",
            "delete",
            WIFI_TRANSITION_PROFILE,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=5,
        check=False,
    )


def _find_transition_wifi(ssid):
    subprocess.run(
        [
            "nmcli",
            "device",
            "wifi",
            "rescan",
            "ifname",
            WIFI_TRANSITION_INTERFACE,
        ],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        timeout=6,
        check=False,
    )

    result = subprocess.run(
        [
            "nmcli",
            "-t",
            "-f",
            "SSID,SIGNAL,SECURITY",
            "device",
            "wifi",
            "list",
            "ifname",
            WIFI_TRANSITION_INTERFACE,
        ],
        capture_output=True,
        text=True,
        timeout=6,
        check=True,
    )

    best = None

    for raw_line in result.stdout.splitlines():
        parts = _split_nmcli_terse_line(
            raw_line
        )

        if len(parts) != 3:
            continue

        found_ssid, signal, security = parts

        if found_ssid.strip() != ssid:
            continue

        try:
            signal_value = int(signal)
        except (TypeError, ValueError):
            signal_value = 0

        candidate = {
            "ssid": found_ssid.strip(),
            "signal": signal_value,
            "security": security.strip(),
        }

        if (
            best is None
            or signal_value > best["signal"]
        ):
            best = candidate

    return best


@app.route(
    "/api/wifi/test-connect",
    methods=["POST"]
)
def api_wifi_test_connect():

    data = request.get_json(
        silent=True
    ) or {}

    ssid = str(
        data.get("ssid", "")
    ).strip()

    password = str(
        data.get("password", "")
    )


    if not ssid:
        return jsonify({
            "ok": False,
            "error": "SSID gerekli",
        }), 400


    if (
        "\n" in password
        or "\r" in password
    ):
        return jsonify({
            "ok": False,
            "error": "Geçersiz Wi-Fi şifresi",
        }), 400


    try:
        network = _find_transition_wifi(
            ssid
        )

    except Exception:
        return jsonify({
            "ok": False,
            "error": (
                "Servis Wi-Fi radyosu "
                "ağları tarayamadı"
            ),
        }), 500


    if network is None:
        return jsonify({
            "ok": False,
            "error": (
                "Bu ağ servis Wi-Fi "
                "radyosu tarafından "
                "görülemiyor"
            ),
        }), 409


    security = (
        network.get(
            "security",
            ""
        )
        .strip()
        .upper()
    )

    is_open = (
        not security
        or security == "--"
        or security == "OPEN"
    )


    if not is_open:

        # İlk ürün sürümünde PSK tabanlı
        # WPA/WPA2 ağlarını destekliyoruz.
        if (
            "WPA" not in security
            and "SAE" not in security
        ):
            return jsonify({
                "ok": False,
                "error": (
                    "Bu Wi-Fi güvenlik "
                    "türü henüz desteklenmiyor"
                ),
                "security": security,
            }), 400


        if len(password) < 8:
            return jsonify({
                "ok": False,
                "error": (
                    "Wi-Fi şifresi en az "
                    "8 karakter olmalı"
                ),
            }), 400


    # Önce önceki geçici testi temizle.
    _cleanup_wifi_transition()


    try:

        subprocess.run(
            [
                "nmcli",
                "connection",
                "add",
                "type",
                "wifi",
                "ifname",
                WIFI_TRANSITION_INTERFACE,
                "con-name",
                WIFI_TRANSITION_PROFILE,
                "ssid",
                ssid,
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        )


        subprocess.run(
            [
                "nmcli",
                "connection",
                "modify",
                WIFI_TRANSITION_PROFILE,
                "connection.autoconnect",
                "no",
                "ipv4.never-default",
                "yes",
                "ipv6.never-default",
                "yes",
                "ipv4.route-metric",
                "900",
                "ipv6.route-metric",
                "900",
            ],
            capture_output=True,
            text=True,
            timeout=8,
            check=True,
        )


        password_file = None

        if not is_open:

            subprocess.run(
                [
                    "nmcli",
                    "connection",
                    "modify",
                    WIFI_TRANSITION_PROFILE,
                    "802-11-wireless-security.key-mgmt",
                    "wpa-psk",
                ],
                capture_output=True,
                text=True,
                timeout=8,
                check=True,
            )


            with tempfile.NamedTemporaryFile(
                mode="w",
                prefix="meraled_wifi_",
                suffix=".passwd",
                dir="/tmp",
                delete=False,
            ) as temp:

                password_file = temp.name

                temp.write(
                    "802-11-wireless-security.psk:"
                    + password
                    + "\n"
                )

            os.chmod(
                password_file,
                0o600
            )


        command = [
            "nmcli",
            "connection",
            "up",
            WIFI_TRANSITION_PROFILE,
            "ifname",
            WIFI_TRANSITION_INTERFACE,
        ]

        if password_file:
            command.extend([
                "passwd-file",
                password_file,
            ])


        try:
            activation = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=35,
                check=False,
            )

        finally:
            if (
                password_file
                and os.path.exists(
                    password_file
                )
            ):
                os.remove(
                    password_file
                )


        if activation.returncode != 0:

            detail = (
                activation.stderr
                or activation.stdout
                or ""
            ).strip()

            _cleanup_wifi_transition()

            return jsonify({
                "ok": False,
                "error": (
                    "Yeni Wi-Fi ağına "
                    "bağlantı doğrulanamadı"
                ),
                "detail": detail,
            }), 502


        ip_result = subprocess.run(
            [
                "nmcli",
                "-g",
                "IP4.ADDRESS",
                "device",
                "show",
                WIFI_TRANSITION_INTERFACE,
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )


        ip_addresses = [
            line.strip()
            for line
            in ip_result.stdout.splitlines()
            if line.strip()
        ]


        if not ip_addresses:
            _cleanup_wifi_transition()

            return jsonify({
                "ok": False,
                "error": (
                    "Wi-Fi bağlantısı kuruldu "
                    "ancak IP adresi alınamadı"
                ),
            }), 502


        return jsonify({
            "ok": True,
            "status": "verified",
            "ssid": ssid,
            "signal": network["signal"],
            "security": (
                network["security"]
                or "OPEN"
            ),
            "interface": (
                WIFI_TRANSITION_INTERFACE
            ),
            "profile": (
                WIFI_TRANSITION_PROFILE
            ),
            "ip_addresses": ip_addresses,
            "message": (
                "Yeni Wi-Fi bağlantısı "
                "doğrulandı"
            ),
        })


    except subprocess.TimeoutExpired:

        _cleanup_wifi_transition()

        return jsonify({
            "ok": False,
            "error": (
                "Wi-Fi bağlantı denemesi "
                "zaman aşımına uğradı"
            ),
        }), 504


    except subprocess.CalledProcessError as exc:

        _cleanup_wifi_transition()

        return jsonify({
            "ok": False,
            "error": (
                "Wi-Fi bağlantı profili "
                "hazırlanamadı"
            ),
            "detail": (
                exc.stderr
                or exc.stdout
                or ""
            ).strip(),
        }), 500



# MERALED_ESP32_RUNTIME_VERIFY_API_V1

def _get_transition_ipv4_interfaces():

    result = subprocess.run(
        [
            "nmcli",
            "-g",
            "IP4.ADDRESS",
            "device",
            "show",
            WIFI_TRANSITION_INTERFACE,
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    interfaces = []

    for line in result.stdout.splitlines():

        line = line.strip()

        if not line:
            continue

        try:
            interface = ipaddress.ip_interface(
                line
            )
        except ValueError:
            continue

        if (
            interface.version == 4
        ):
            interfaces.append(
                interface
            )

    return interfaces


def _get_transition_connection_name():

    result = subprocess.run(
        [
            "nmcli",
            "-g",
            "GENERAL.CONNECTION",
            "device",
            "show",
            WIFI_TRANSITION_INTERFACE,
        ],
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )

    return result.stdout.strip()


@app.route(
    "/api/wifi/esp32-verify",
    methods=["POST"]
)
def api_wifi_esp32_verify():

    data = request.get_json(
        silent=True
    ) or {}


    candidate_raw = str(
        data.get(
            "ip",
            ""
        )
    ).strip()


    try:
        candidate_ip = ipaddress.ip_address(
            candidate_raw
        )
    except ValueError:
        return jsonify({
            "ok": False,
            "error": "Geçersiz ESP32 IP adresi",
        }), 400


    if candidate_ip.version != 4:
        return jsonify({
            "ok": False,
            "error": "ESP32 için IPv4 adresi gerekli",
        }), 400


    try:
        active_connection = (
            _get_transition_connection_name()
        )

        transition_interfaces = (
            _get_transition_ipv4_interfaces()
        )

    except Exception:
        return jsonify({
            "ok": False,
            "error": (
                "Servis Wi-Fi bağlantısı "
                "doğrulanamadı"
            ),
        }), 500


    if (
        active_connection
        != WIFI_TRANSITION_PROFILE
    ):
        return jsonify({
            "ok": False,
            "error": (
                "Doğrulanmış geçiş Wi-Fi "
                "bağlantısı aktif değil"
            ),
        }), 409


    if not transition_interfaces:
        return jsonify({
            "ok": False,
            "error": (
                "Geçiş Wi-Fi arayüzünde "
                "IPv4 adresi yok"
            ),
        }), 409


    candidate_on_transition_network = any(
        candidate_ip in interface.network
        for interface
        in transition_interfaces
    )


    if not candidate_on_transition_network:
        return jsonify({
            "ok": False,
            "error": (
                "ESP32 yeni servis Wi-Fi "
                "ağında görünmüyor"
            ),
        }), 409


    if any(
        candidate_ip == interface.ip
        for interface
        in transition_interfaces
    ):
        return jsonify({
            "ok": False,
            "error": (
                "ESP32 IP adresi Jetson "
                "adresinden farklı olmalı"
            ),
        }), 400


    runtime_client = (
        get_esp32_client()
    )


    if runtime_client is None:
        return jsonify({
            "ok": False,
            "error": (
                "Çalışan ESP32 istemcisi "
                "henüz hazır değil"
            ),
        }), 503


    if (
        getattr(
            runtime_client,
            "transport",
            None
        )
        != "wifi"
    ):
        return jsonify({
            "ok": False,
            "error": (
                "ESP32 çalışma bağlantısı "
                "Wi-Fi modunda değil"
            ),
        }), 409


    try:
        current_endpoint = (
            runtime_client
            .get_wifi_endpoint()
        )

        tcp_port = int(
            current_endpoint[
                "tcp_port"
            ]
        )

    except Exception:
        return jsonify({
            "ok": False,
            "error": (
                "Mevcut ESP32 endpoint "
                "bilgisi alınamadı"
            ),
        }), 500


    candidate_client = ESP32Client(
        transport="wifi",
        host=str(candidate_ip),
        tcp_port=tcp_port,
        wifi_timeout=3.0,
    )


    try:
        device_info = (
            candidate_client
            .device_info()
        )

        candidate_health = (
            candidate_client
            .health()
        )

    except Exception:
        return jsonify({
            "ok": False,
            "error": (
                "Yeni ağdaki ESP32 "
                "doğrulanamadı"
            ),
        }), 502


    device_id = str(
        device_info.get(
            "id",
            ""
        )
    )


    if not device_id.startswith(
        "MERALED-"
    ):
        return jsonify({
            "ok": False,
            "error": (
                "Yeni IP adresindeki cihaz "
                "MERALED kontrol ünitesi değil"
            ),
        }), 409


    if not candidate_health.get(
        "connected",
        False
    ):
        return jsonify({
            "ok": False,
            "error": (
                "Yeni ağdaki ESP32 "
                "HEALTH doğrulamasını geçemedi"
            ),
        }), 502


    previous_endpoint = dict(
        current_endpoint
    )


    try:
        runtime_client.set_wifi_endpoint(
            str(candidate_ip),
            tcp_port=tcp_port,
        )

        switched_health = (
            runtime_client.health()
        )

        if not switched_health.get(
            "connected",
            False
        ):
            raise RuntimeError(
                "Runtime HEALTH failed"
            )

    except Exception:

        try:
            runtime_client.set_wifi_endpoint(
                previous_endpoint["host"],
                tcp_port=previous_endpoint[
                    "tcp_port"
                ],
            )
        except Exception:
            pass

        return jsonify({
            "ok": False,
            "error": (
                "ESP32 runtime bağlantısı "
                "yeni IP'ye geçirilemedi"
            ),
        }), 502


    system_state.update_health(
        esp32=True,
        as7343=bool(
            switched_health.get(
                "as7343",
                False
            )
        ),
    )


    # MERALED_ESP32_ENDPOINT_PERSIST_V1
    #
    # Yalnızca DEVICE_INFO + HEALTH + runtime HEALTH
    # doğrulamalarının tamamı geçtikten sonra kalıcılaştır.
    try:
        save_esp32_endpoint(
            str(candidate_ip),
            tcp_port,
            device_id=device_id,
        )

    except Exception:
        return jsonify({
            "ok": False,
            "error": (
                "ESP32 bağlantısı doğrulandı "
                "ancak kalıcı endpoint "
                "kaydedilemedi"
            ),
        }), 500


    return jsonify({
        "ok": True,
        "status": "runtime_switched",
        "device_id": device_id,
        "ip": str(candidate_ip),
        "tcp_port": tcp_port,
        "health": {
            "esp32": bool(
                switched_health.get(
                    "esp32",
                    False
                )
            ),
            "pca9685": bool(
                switched_health.get(
                    "pca9685",
                    False
                )
            ),
            "as7343": bool(
                switched_health.get(
                    "as7343",
                    False
                )
            ),
        },
        "message": (
            "ESP32 yeni Wi-Fi ağında "
            "doğrulandı"
        ),
    })


@app.route(
    "/api/wifi/test-cancel",
    methods=["POST"]
)
def api_wifi_test_cancel():

    _cleanup_wifi_transition()

    return jsonify({
        "ok": True,
        "status": "cancelled",
    })


@app.route("/api/state")
def api_state():
    return jsonify(system_state.get())


@app.route("/api/manual", methods=["POST"])
def api_manual():
    data = request.get_json(silent=True) or {}

    try:
        target_cct = float(data["target_cct"])
        target_brightness = float(data["target_brightness"])
    except (KeyError, TypeError, ValueError):
        return jsonify({
            "ok": False,
            "error": "target_cct and target_brightness are required"
        }), 400

    if not 3000.0 <= target_cct <= 6500.0:
        return jsonify({
            "ok": False,
            "error": "target_cct must be between 3000 and 6500 K"
        }), 400

    if not 0.0 <= target_brightness <= 100.0:
        return jsonify({
            "ok": False,
            "error": "target_brightness must be between 0 and 100"
        }), 400

    system_state.request_manual(
        target_cct=target_cct,
        target_brightness=target_brightness
    )

    return jsonify({
        "ok": True,
        "requested_mode": "MANUAL",
        "target_cct": target_cct,
        "target_brightness": target_brightness
    })


@app.route("/api/auto", methods=["POST"])
def api_auto():
    system_state.request_auto()

    return jsonify({
        "ok": True,
        "requested_mode": "AUTO"
    })


def run_web_server():
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":
    run_web_server()
