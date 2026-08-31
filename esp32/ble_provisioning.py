import bluetooth
import struct
import time


_IRQ_CENTRAL_CONNECT = 1
_IRQ_CENTRAL_DISCONNECT = 2
_IRQ_GATTS_WRITE = 3

_FLAG_READ = 0x0002
_FLAG_WRITE = 0x0008
_FLAG_NOTIFY = 0x0010


SERVICE_UUID = bluetooth.UUID(
    "8f7a0001-4c5d-4f31-8e6d-158298000001"
)

DEVICE_INFO_UUID = bluetooth.UUID(
    "8f7a0002-4c5d-4f31-8e6d-158298000001"
)

SESSION_UUID = bluetooth.UUID(
    "8f7a0003-4c5d-4f31-8e6d-158298000001"
)

AUTH_UUID = bluetooth.UUID(
    "8f7a0004-4c5d-4f31-8e6d-158298000001"
)

WIFI_SSID_UUID = bluetooth.UUID(
    "8f7a0005-4c5d-4f31-8e6d-158298000001"
)

WIFI_PASSWORD_UUID = bluetooth.UUID(
    "8f7a0006-4c5d-4f31-8e6d-158298000001"
)

WIFI_COMMAND_UUID = bluetooth.UUID(
    "8f7a0007-4c5d-4f31-8e6d-158298000001"
)

WIFI_STATUS_UUID = bluetooth.UUID(
    "8f7a0008-4c5d-4f31-8e6d-158298000001"
)


class MeraledBLEProvisioning:
    def __init__(
        self,
        device_id,
        setup_pin,
        provisioned=False,
        session_timeout_seconds=120
    ):
        self.device_id = str(device_id)
        self.setup_pin = str(setup_pin)
        self.provisioned = bool(provisioned)

        self.session_timeout_ms = int(
            session_timeout_seconds * 1000
        )

        self.ble = bluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq)

        device_info_char = (
            DEVICE_INFO_UUID,
            _FLAG_READ | _FLAG_NOTIFY
        )

        session_char = (
            SESSION_UUID,
            _FLAG_READ | _FLAG_WRITE | _FLAG_NOTIFY
        )

        auth_char = (
            AUTH_UUID,
            _FLAG_WRITE | _FLAG_NOTIFY
        )

        wifi_ssid_char = (
            WIFI_SSID_UUID,
            _FLAG_WRITE
        )

        wifi_password_char = (
            WIFI_PASSWORD_UUID,
            _FLAG_WRITE
        )

        wifi_command_char = (
            WIFI_COMMAND_UUID,
            _FLAG_WRITE
        )

        wifi_status_char = (
            WIFI_STATUS_UUID,
            _FLAG_READ | _FLAG_NOTIFY
        )

        service = (
            SERVICE_UUID,
            (
                device_info_char,
                session_char,
                auth_char,
                wifi_ssid_char,
                wifi_password_char,
                wifi_command_char,
                wifi_status_char
            )
        )

        (
            (
                self.device_info_handle,
                self.session_handle,
                self.auth_handle,
                self.wifi_ssid_handle,
                self.wifi_password_handle,
                self.wifi_command_handle,
                self.wifi_status_handle
            ),
        ) = self.ble.gatts_register_services(
            (service,)
        )

        # PIN yazımı için biraz daha büyük buffer.
        self.ble.gatts_set_buffer(
            self.auth_handle,
            64,
            True
        )

        # SSID için 32 byte standart sınırın üzerinde
        # biraz pay bırakıyoruz.
        self.ble.gatts_set_buffer(
            self.wifi_ssid_handle,
            64,
            True
        )

        # WPA/WPA2 parolası için yeterli alan.
        self.ble.gatts_set_buffer(
            self.wifi_password_handle,
            128,
            True
        )

        self.ble.gatts_set_buffer(
            self.wifi_command_handle,
            32,
            True
        )

        self.ble.gatts_write(
            self.wifi_status_handle,
            b"WIFI_IDLE"
        )

        self.connections = set()

        # Hangi BLE bağlantıları PIN doğrulamasından geçti.
        self.authorized_connections = set()

        # Provisioning sırasında tek bir telefon kontrol sahibi.
        self.session_owner = None
        self.session_started_ms = None

        # Wi-Fi bilgileri kalıcı kaydedilmeden önce
        # yalnızca RAM üzerinde tutulur.
        self.pending_wifi_ssid = None
        self.pending_wifi_password = None
        self.wifi_connect_requested = False

        self._update_device_info()
        self._update_session_state()

    def _update_device_info(self):
        value = (
            "ID={};PROVISIONED={}".format(
                self.device_id,
                1 if self.provisioned else 0
            )
        )

        self.ble.gatts_write(
            self.device_info_handle,
            value.encode()
        )

    def _session_is_active(self):
        if self.session_owner is None:
            return False

        if self.session_started_ms is None:
            return False

        elapsed = time.ticks_diff(
            time.ticks_ms(),
            self.session_started_ms
        )

        if elapsed > self.session_timeout_ms:
            self._close_session()
            return False

        return True

    def _update_session_state(self):
        active = self._session_is_active()

        value = (
            "SESSION_ACTIVE={}".format(
                1 if active else 0
            )
        )

        self.ble.gatts_write(
            self.session_handle,
            value.encode()
        )

    def _notify(
        self,
        conn_handle,
        attr_handle,
        value
    ):
        try:
            self.ble.gatts_notify(
                conn_handle,
                attr_handle,
                value.encode()
            )
        except Exception:
            pass

    def _close_session(self):
        self.session_owner = None
        self.session_started_ms = None

        # Session bittiginde gecici Wi-Fi bilgilerini
        # ve bekleyen CONNECT istegini unut.
        self.pending_wifi_ssid = None
        self.pending_wifi_password = None
        self.wifi_connect_requested = False

        try:
            self.ble.gatts_write(
                self.session_handle,
                b"SESSION_ACTIVE=0"
            )
        except Exception:
            pass

    def _handle_auth(
        self,
        conn_handle
    ):
        raw = self.ble.gatts_read(
            self.auth_handle
        )

        try:
            supplied_pin = raw.decode().strip()
        except Exception:
            supplied_pin = ""

        if supplied_pin == self.setup_pin:
            self.authorized_connections.add(
                conn_handle
            )

            self._notify(
                conn_handle,
                self.auth_handle,
                "AUTH_OK"
            )

            print(
                "BLE AUTH OK",
                conn_handle
            )

        else:
            self.authorized_connections.discard(
                conn_handle
            )

            self._notify(
                conn_handle,
                self.auth_handle,
                "AUTH_FAILED"
            )

            print(
                "BLE AUTH FAILED",
                conn_handle
            )

        # PIN'i characteristic üzerinde bırakma.
        try:
            self.ble.gatts_write(
                self.auth_handle,
                b""
            )
        except Exception:
            pass

    def _connection_can_provision(
        self,
        conn_handle
    ):
        if (
            conn_handle
            not in self.authorized_connections
        ):
            return False

        if not self._session_is_active():
            return False

        if self.session_owner != conn_handle:
            return False

        return True

    def _handle_wifi_ssid(
        self,
        conn_handle
    ):
        if not self._connection_can_provision(
            conn_handle
        ):
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                "WIFI_DENIED_SESSION_REQUIRED"
            )
            return

        raw = self.ble.gatts_read(
            self.wifi_ssid_handle
        )

        try:
            value = raw.decode().strip()
        except Exception:
            value = ""

        if not value:
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                "WIFI_SSID_INVALID"
            )
            return

        self.pending_wifi_ssid = value

        self._notify(
            conn_handle,
            self.wifi_status_handle,
            "WIFI_SSID_OK"
        )

        print(
            "BLE WIFI SSID RECEIVED",
            conn_handle
        )

    def _handle_wifi_password(
        self,
        conn_handle
    ):
        if not self._connection_can_provision(
            conn_handle
        ):
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                "WIFI_DENIED_SESSION_REQUIRED"
            )
            return

        raw = self.ble.gatts_read(
            self.wifi_password_handle
        )

        try:
            value = raw.decode()
        except Exception:
            value = None

        if value is None:
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                "WIFI_PASSWORD_INVALID"
            )
            return

        self.pending_wifi_password = value

        self._notify(
            conn_handle,
            self.wifi_status_handle,
            "WIFI_PASSWORD_OK"
        )

        # Parolayı characteristic üzerinde bırakma.
        try:
            self.ble.gatts_write(
                self.wifi_password_handle,
                b""
            )
        except Exception:
            pass

        print(
            "BLE WIFI PASSWORD RECEIVED",
            conn_handle
        )

    def _handle_wifi_command(
        self,
        conn_handle
    ):
        if not self._connection_can_provision(
            conn_handle
        ):
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                "WIFI_DENIED_SESSION_REQUIRED"
            )
            return

        raw = self.ble.gatts_read(
            self.wifi_command_handle
        )

        try:
            command = raw.decode().strip().upper()
        except Exception:
            command = ""

        # Komutu characteristic üzerinde bırakma.
        try:
            self.ble.gatts_write(
                self.wifi_command_handle,
                b""
            )
        except Exception:
            pass

        if command != "CONNECT":
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                "WIFI_COMMAND_INVALID"
            )
            return

        if not self.pending_wifi_ssid:
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                "WIFI_SSID_REQUIRED"
            )
            return

        if self.pending_wifi_password is None:
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                "WIFI_PASSWORD_REQUIRED"
            )
            return

        self.wifi_connect_requested = True

        self._notify(
            conn_handle,
            self.wifi_status_handle,
            "WIFI_CONNECT_QUEUED"
        )

        print(
            "BLE WIFI CONNECT QUEUED",
            conn_handle
        )

    def take_wifi_connect_request(self):
        if not self.wifi_connect_requested:
            return None

        if not self._session_is_active():
            self.wifi_connect_requested = False
            return None

        conn_handle = self.session_owner

        if conn_handle is None:
            self.wifi_connect_requested = False
            return None

        request = {
            "conn_handle": conn_handle,
            "ssid": self.pending_wifi_ssid,
            "password": self.pending_wifi_password
        }

        self.wifi_connect_requested = False

        # Ana döngü isteği aldıktan sonra BLE sınıfında
        # kimlik bilgilerini tutmaya devam etme.
        self.pending_wifi_ssid = None
        self.pending_wifi_password = None

        return request

    def set_wifi_status(
        self,
        conn_handle,
        value
    ):
        value = str(value)

        try:
            self.ble.gatts_write(
                self.wifi_status_handle,
                value.encode()
            )
        except Exception:
            pass

        if conn_handle is not None:
            self._notify(
                conn_handle,
                self.wifi_status_handle,
                value
            )

    def mark_provisioned(
        self,
        conn_handle
    ):
        self.provisioned = True
        self._update_device_info()

        self.set_wifi_status(
            conn_handle,
            "WIFI_PROVISIONED"
        )

    def _handle_session_command(
        self,
        conn_handle
    ):
        raw = self.ble.gatts_read(
            self.session_handle
        )

        try:
            command = raw.decode().strip().upper()
        except Exception:
            command = ""

        if command == "START":
            if (
                conn_handle
                not in self.authorized_connections
            ):
                self._notify(
                    conn_handle,
                    self.session_handle,
                    "SESSION_DENIED_AUTH_REQUIRED"
                )
                return

            if (
                self._session_is_active()
                and self.session_owner != conn_handle
            ):
                self._notify(
                    conn_handle,
                    self.session_handle,
                    "SESSION_DENIED_BUSY"
                )
                return

            self.session_owner = conn_handle
            self.session_started_ms = (
                time.ticks_ms()
            )

            self._update_session_state()

            self._notify(
                conn_handle,
                self.session_handle,
                "SESSION_ACTIVE=1"
            )

            print(
                "BLE SESSION STARTED",
                conn_handle
            )

        elif command == "STOP":
            if self.session_owner == conn_handle:
                self._close_session()

                self._notify(
                    conn_handle,
                    self.session_handle,
                    "SESSION_ACTIVE=0"
                )

                print(
                    "BLE SESSION STOPPED",
                    conn_handle
                )

            else:
                self._notify(
                    conn_handle,
                    self.session_handle,
                    "SESSION_DENIED_NOT_OWNER"
                )

    def _irq(self, event, data):
        if event == _IRQ_CENTRAL_CONNECT:
            conn_handle, _, _ = data

            self.connections.add(
                conn_handle
            )

            print(
                "BLE CLIENT CONNECTED",
                conn_handle
            )

        elif event == _IRQ_CENTRAL_DISCONNECT:
            conn_handle, _, _ = data

            self.connections.discard(
                conn_handle
            )

            self.authorized_connections.discard(
                conn_handle
            )

            if self.session_owner == conn_handle:
                self._close_session()

                self.pending_wifi_ssid = None
                self.pending_wifi_password = None

            print(
                "BLE CLIENT DISCONNECTED",
                conn_handle
            )

            self._advertise()

        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data

            if attr_handle == self.auth_handle:
                self._handle_auth(
                    conn_handle
                )

            elif attr_handle == self.session_handle:
                self._handle_session_command(
                    conn_handle
                )

            elif attr_handle == self.wifi_ssid_handle:
                self._handle_wifi_ssid(
                    conn_handle
                )

            elif attr_handle == self.wifi_password_handle:
                self._handle_wifi_password(
                    conn_handle
                )

            elif attr_handle == self.wifi_command_handle:
                self._handle_wifi_command(
                    conn_handle
                )

    def _advertising_payload(self):
        name = self.device_id.encode()

        payload = bytearray()

        # Flags
        payload += struct.pack(
            "BB",
            2,
            0x01
        )
        payload += b"\x06"

        # Complete Local Name
        payload += struct.pack(
            "BB",
            len(name) + 1,
            0x09
        )
        payload += name

        return payload

    def _advertise(self):
        self.ble.gap_advertise(
            250000,
            adv_data=self._advertising_payload()
        )

    def start(self):
        self._advertise()

        print(
            "BLE PROVISIONING READY:",
            self.device_id
        )

    def stop(self):
        self._close_session()

        try:
            self.ble.gap_advertise(None)
        except Exception:
            pass

        self.ble.active(False)

        print(
            "BLE PROVISIONING STOPPED"
        )
