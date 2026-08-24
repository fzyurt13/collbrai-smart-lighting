from machine import Pin, I2C
import sys
import time


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


def pca_init():
    devices = i2c.scan()

    print("I2C:", devices)

    if PCA_ADDR not in devices:
        raise RuntimeError(
            "PCA9685 not found at 0x40"
        )

    # Sleep
    i2c.writeto_mem(
        PCA_ADDR,
        0x00,
        b'\x10'
    )

    # ~1 kHz PWM
    i2c.writeto_mem(
        PCA_ADDR,
        0xFE,
        b'\x05'
    )

    # MODE2
    i2c.writeto_mem(
        PCA_ADDR,
        0x01,
        b'\x04'
    )

    # Wake + auto increment
    i2c.writeto_mem(
        PCA_ADDR,
        0x00,
        b'\x20'
    )

    time.sleep_ms(2)


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


def process_command(line):
    line = line.strip()

    if not line:
        return

    parts = line.split()

    try:
        if (
            len(parts) == 4
            and parts[0].upper() == "WARM"
            and parts[2].upper() == "COOL"
        ):
            warm = float(parts[1])
            cool = float(parts[3])

            set_warm_cool(
                warm,
                cool
            )

        elif line.upper() == "OFF":
            all_off()

        elif line.upper() == "STATUS":
            print(
                "STATUS READY PCA=0x40"
            )

        else:
            print(
                "ERROR COMMAND"
            )

    except Exception as exc:
        print(
            "ERROR",
            exc
        )


pca_init()
all_off()

print(
    "COLLBRAI ESP32 LIGHT CONTROLLER READY"
)

while True:
    try:
        line = sys.stdin.readline()

        if line:
            process_command(line)

    except Exception as exc:
        print(
            "LOOP ERROR",
            exc
        )
        time.sleep_ms(100)
