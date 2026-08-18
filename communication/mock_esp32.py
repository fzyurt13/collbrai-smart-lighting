class MockESP32:
    def send_pwm_command(self, warm_pwm, cool_pwm):
        print(
            "[ESP32 MOCK] warm_pwm={} cool_pwm={}".format(
                int(warm_pwm),
                int(cool_pwm)
            )
        )

    def send_led_command(self, warm, cool, brightness):
        print(
            "[ESP32 MOCK] warm={} cool={} brightness={}".format(
                warm, cool, brightness
            )
        )
