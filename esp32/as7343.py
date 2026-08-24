import time


class AS7343:
    ADDRESS = 0x39

    ENABLE = 0x80
    ATIME = 0x81
    STATUS2 = 0x90
    DATA_START = 0x95
    ASTEP_L = 0xD4
    ASTEP_H = 0xD5
    CFG20 = 0xD6

    def __init__(self, i2c, address=ADDRESS):
        self.i2c = i2c
        self.address = address

    def begin(self):
        devices = self.i2c.scan()

        if self.address not in devices:
            raise RuntimeError(
                "AS7343 not found at 0x39"
            )

        # Power ON
        self.i2c.writeto_mem(
            self.address,
            self.ENABLE,
            b'\x01'
        )

        time.sleep_ms(10)

        # 18-channel Auto-SMUX
        self.i2c.writeto_mem(
            self.address,
            self.CFG20,
            b'\x60'
        )

        # Integration settings
        self.i2c.writeto_mem(
            self.address,
            self.ATIME,
            b'\x1d'
        )

        self.i2c.writeto_mem(
            self.address,
            self.ASTEP_L,
            b'\xe7'
        )

        self.i2c.writeto_mem(
            self.address,
            self.ASTEP_H,
            b'\x03'
        )

        return True

    def read_raw(self):
        # Power + spectral measurement enable
        self.i2c.writeto_mem(
            self.address,
            self.ENABLE,
            b'\x03'
        )

        time.sleep_ms(200)

        raw = self.i2c.readfrom_mem(
            self.address,
            self.DATA_START,
            36
        )

        values = [
            raw[i] | (raw[i + 1] << 8)
            for i in range(0, 36, 2)
        ]

        return values

    def read_channels(self):
        v = self.read_raw()

        return {
            "FZ_450": v[0],
            "FY_555": v[1],
            "FXL_600": v[2],
            "NIR_855": v[3],

            "F2_425": v[6],
            "F3_475": v[7],
            "F4_515": v[8],
            "F6_640": v[9],

            "F1_405": v[12],
            "F7_690": v[13],
            "F8_745": v[14],
            "F5_550": v[15],

            "VIS": (
                v[4] +
                v[10] +
                v[16]
            ) // 3,

            "FD": (
                v[5] +
                v[11] +
                v[17]
            ) // 3
        }

    def print_channels(self):
        d = self.read_channels()

        order = [
            "F1_405",
            "F2_425",
            "FZ_450",
            "F3_475",
            "F4_515",
            "F5_550",
            "FY_555",
            "FXL_600",
            "F6_640",
            "F7_690",
            "F8_745",
            "NIR_855",
            "VIS",
            "FD"
        ]

        print("------------------------")
        print("AS7343 SPECTRUM")
        print("------------------------")

        for key in order:
            print(
                "{:<8} : {}".format(
                    key,
                    d[key]
                )
            )

        return d
