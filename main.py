import argparse
import time
import threading

from web.app import run_web_server
from web.system_state import system_state

from config.settings import (
    MODE,
    ESP32_TRANSPORT,
    ESP32_HOST,
    ESP32_TCP_PORT,
    ESP32_TIMEOUT,
    TARGET_CCT,
    CCT_TOLERANCE,
    START_WARM,
    START_COOL,
    TARGET_BRIGHTNESS,
    BRIGHTNESS_TOLERANCE,
    START_BRIGHTNESS,
)

from control.lighting_controller import LightingController
from control.cct_controller import CCTController
from control.brightness_controller import BrightnessController
from control.pwm_mixer import PWMMixer
from control.profile_manager import ProfileManager
from control.compensation_guard import CompensationGuard
from ai.mock_classifier import MockAIClassifier
from camera.camera_factory import create_camera
from ai.classifier_factory import create_classifier
from ai.decision_manager import AIDecisionManager
from ai.temporal_confirmation import TemporalConfirmation
from control.recipe_manager import RecipeManager
from control.smooth_transition import SmoothTransition
from control.system_state_manager import SystemStateManager
from ai.product_presence_manager import ProductPresenceManager

from communication.mock_esp32 import MockESP32
from communication.esp32_client import ESP32Client
from sensors.spectral_ratio_estimator import SpectralRatioEstimator
from sensors.brightness_estimator import BrightnessEstimator
from control.spectral_feedback_controller import SpectralFeedbackController
from control.cct_feedback_controller import CCTFeedbackController
from control.brightness_feedback_controller import BrightnessFeedbackController

from spectral.mock_environment import MockLightingEnvironment
from sensors.mock_light_sensor import MockLightSensor
from jetson.data_logger import DataLogger


def parse_args():
    parser = argparse.ArgumentParser(
        description="Collbrai Smart Lighting Controller"
    )

    parser.add_argument(
        "--camera",
        type=str,
        default="mock",
        choices=["mock", "imx219"],
        help="Camera backend"
    )

    parser.add_argument(
        "--ai",
        action="store_true",
        help="Run lighting selection through AI decision layer"
    )

    parser.add_argument(
        "--continuous",
        action="store_true",
        help="Run continuous showcase mode with 1%% standby lighting"
    )

    parser.add_argument(
        "--mock-ai-sequence",
        action="store_true",
        help="Simulate changing products during runtime"
    )

    parser.add_argument(
        "--mock-confidence",
        type=float,
        default=1.0,
        help="Mock AI confidence value between 0.0 and 1.0"
    )

    parser.add_argument(
        "--mock-product",
        type=str,
        default="yellow_gold",
        help="Mock AI product class"
    )

    parser.add_argument(
        "--dynamic-ambient",
        action="store_true",
        help="Simulate changing ambient light during runtime"
    )

    parser.add_argument(
        "--ambient",
        type=float,
        default=15.0,
        help="Mock ambient light percentage (0-100)"
    )

    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="Lighting profile, e.g. yellow_gold, diamond, silver, white_gold"
    )

    parser.add_argument(
        "--cct",
        type=float,
        default=TARGET_CCT,
        help="Target CCT in Kelvin"
    )

    parser.add_argument(
        "--brightness",
        type=float,
        default=TARGET_BRIGHTNESS,
        help="Target brightness percentage (0-100)"
    )

    parser.add_argument(
        "--esp32-transport",
        type=str,
        default=None,
        choices=["serial", "wifi"],
        help="ESP32 communication transport"
    )

    parser.add_argument(
        "--esp32-host",
        type=str,
        default=None,
        help="ESP32 IP address for Wi-Fi transport"
    )

    parser.add_argument(
        "--esp32-tcp-port",
        type=int,
        default=None,
        help="ESP32 TCP server port"
    )

    return parser.parse_args()


def create_esp32_client_from_args(args):
    # Command-line arguments override product defaults.
    transport = args.esp32_transport or ESP32_TRANSPORT
    host = args.esp32_host or ESP32_HOST
    tcp_port = args.esp32_tcp_port or ESP32_TCP_PORT

    if transport == "wifi":
        if not host:
            raise ValueError(
                "ESP32 Wi-Fi host is not configured"
            )

        return ESP32Client(
            transport="wifi",
            host=host,
            tcp_port=tcp_port,
            wifi_timeout=5.0
        )

    return ESP32Client(
        port="/dev/ttyACM0",
        baudrate=115200,
        timeout=0.3,
        startup_delay=1.0,
        transport="serial"
    )


def run_mock(
    target_cct,
    target_brightness,
    ambient_light,
    dynamic_ambient,
    transition_start_cct=None,
    transition_start_brightness=None,
    mock_ai_sequence=False
):
    print("MODE: MOCK")
    print(
        "TARGET: {:.0f} K / {:.1f}% brightness".format(
            target_cct,
            target_brightness
        )
    )
    print()

    lighting = LightingController()

    transition = SmoothTransition(
        cct_step=100.0,
        brightness_step=2.0
    )

    if transition_start_cct is None:
        active_target_cct = target_cct
    else:
        active_target_cct = float(
            transition_start_cct
        )

    if transition_start_brightness is None:
        active_target_brightness = target_brightness
    else:
        active_target_brightness = float(
            transition_start_brightness
        )

    cct_controller = CCTController(
        target_cct=active_target_cct,
        tolerance=CCT_TOLERANCE
    )

    brightness_controller = BrightnessController(
        target_brightness=active_target_brightness,
        tolerance=BRIGHTNESS_TOLERANCE
    )

    pwm_mixer = PWMMixer()
    compensation_guard = CompensationGuard()
    logger = DataLogger()

    print("LOG FILE:", logger.path)

    esp32 = MockESP32()
    environment = MockLightingEnvironment()
    sensor = MockLightSensor(environment)

    ai_classifier = None
    ai_confirmation = None
    presence_manager = None
    recipe_manager = None
    system_state = None
    active_product = None

    if mock_ai_sequence:
        ai_sequence = [
            "yellow_gold",
            "yellow_gold",
            "diamond",
            "yellow_gold",
            "diamond",
            "diamond",
            "diamond",

            "unknown",
            "unknown",
            "unknown",

            "diamond",

            "unknown",
            "unknown",
            "unknown",
            "unknown",
            "unknown",

            "silver",
            "silver",
            "silver",

            "yellow_gold",
            "yellow_gold",
            "yellow_gold"
        ]

        ai_classifier = MockAIClassifier(
            confidence=0.95,
            sequence=ai_sequence
        )

        ai_confirmation = TemporalConfirmation(
            required_hits=3
        )

        presence_manager = ProductPresenceManager(
            required_absence_hits=5
        )

        recipe_manager = RecipeManager()
        system_state = SystemStateManager()

        print("MOCK AI SEQUENCE: ENABLED")
        print()

    environment.set_ambient_light(ambient_light)

    print(
        "AMBIENT LIGHT: {:.1f}%".format(
            ambient_light
        )
    )
    print()

    warm = START_WARM
    cool = START_COOL
    brightness = START_BRIGHTNESS

    for iteration in range(1, 61):

        if mock_ai_sequence:
            prediction = ai_classifier.predict()

            product_class = prediction.get(
                "class",
                "unknown"
            )

            confidence = float(
                prediction.get(
                    "confidence",
                    0.0
                )
            )

            print(
                "AI Frame {:02d} | {:12s} | conf={:.0f}%".format(
                    iteration,
                    product_class,
                    confidence * 100.0
                )
            )

            presence = presence_manager.update(
                product_class
            )

            if product_class == "unknown":
                ai_confirmation.reset()

                print(
                    "AI Presence | absence={}/{}".format(
                        presence["absence_hits"],
                        presence_manager.required_absence_hits
                    )
                )

                if (
                    presence["absence_confirmed"]
                    and active_product is not None
                ):
                    print()
                    print(
                        ">>> NO PRODUCT CONFIRMED"
                    )

                    active_product = None

                    system_state.clear_product()

                    standby_recipe = recipe_manager.get(
                        "standby"
                    )

                    target_cct = standby_recipe[
                        "target_cct"
                    ]
                    target_brightness = standby_recipe[
                        "target_brightness"
                    ]

                    print(
                        ">>> SYSTEM STATE: STANDBY"
                    )
                    print(
                        ">>> STANDBY RECIPE: {:.0f} K / {:.1f}%".format(
                            target_cct,
                            target_brightness
                        )
                    )
                    print()

            else:
                system_state.product_detected(
                    product_class
                )

                confirmation = ai_confirmation.update(
                    product_class
                )

                print(
                    "AI Confirm  | hits={}/{} | confirmed={}".format(
                        confirmation["hits"],
                        ai_confirmation.required_hits,
                        confirmation["confirmed"]
                    )
                )

                if confirmation["confirmed"]:
                    confirmed_product = confirmation[
                        "product_class"
                    ]

                    if confirmed_product != active_product:
                        if recipe_manager.exists(
                            confirmed_product
                        ):
                            recipe = recipe_manager.get(
                                confirmed_product
                            )

                            recipe_manager.validate(
                                recipe
                            )

                            active_product = (
                                confirmed_product
                            )

                            system_state.confirm_product(
                                active_product
                            )
                            system_state.start_transition()

                            target_cct = recipe[
                                "target_cct"
                            ]
                            target_brightness = recipe[
                                "target_brightness"
                            ]

                            print()
                            print(
                                ">>> PRODUCT CHANGE CONFIRMED:",
                                active_product
                            )
                            print(
                                ">>> NEW RECIPE: {:.0f} K / {:.1f}%".format(
                                    target_cct,
                                    target_brightness
                                )
                            )
                            print(
                                ">>> SYSTEM STATE: TRANSITIONING"
                            )
                            print()

        transition_state = transition.update(
            current_cct=active_target_cct,
            target_cct=target_cct,
            current_brightness=active_target_brightness,
            target_brightness=target_brightness
        )

        active_target_cct = transition_state[
            "target_cct"
        ]

        active_target_brightness = transition_state[
            "target_brightness"
        ]

        cct_controller.target_cct = (
            active_target_cct
        )

        brightness_controller.target_brightness = (
            active_target_brightness
        )

        if (
            active_target_cct != target_cct
            or
            active_target_brightness
            != target_brightness
        ):
            print(
                "Recipe transition: {:.0f} K / {:.1f}%".format(
                    active_target_cct,
                    active_target_brightness
                )
            )

        if dynamic_ambient:
            ambient_state = environment.simulate_ambient_step(
                iteration
            )

            print(
                "Ambient now: {:.1f}% / {:.0f} K".format(
                    ambient_state["ambient_light_percent"],
                    ambient_state["ambient_cct"]
                )
            )

        lighting.set_target(
            warm=warm,
            cool=cool,
            brightness=brightness
        )

        state = lighting.get_state()

        pwm = pwm_mixer.mix(
            state["warm"],
            state["cool"],
            state["brightness"]
        )

        esp32.send_pwm_command(
            pwm["warm_pwm"],
            pwm["cool_pwm"]
        )

        environment.apply_led_state(
            state["warm"],
            state["cool"],
            state["brightness"]
        )

        time.sleep(0.2)

        measurement = sensor.read()

        measured_cct = measurement["measured_cct"]
        measured_brightness = measurement["measured_light_percent"]

        cct_error = cct_controller.calculate_error(
            measured_cct
        )

        brightness_error = (
            brightness_controller.calculate_error(
                measured_brightness
            )
        )

        compensation = compensation_guard.check(
            warm=state["warm"],
            cool=state["cool"],
            cct_error=cct_error
        )

        if compensation["limited"]:
            print(
                "STATUS: CCT COMPENSATION LIMIT | "
                "Reason: {}".format(
                    compensation["reason"]
                )
            )
            print(
                "DETAIL:",
                compensation["message"]
            )

        logger.log(
            iteration=iteration,
            target_cct=target_cct,
            measured_cct=measured_cct,
            cct_error=cct_error,
            target_brightness=target_brightness,
            measured_brightness=measured_brightness,
            brightness_error=brightness_error,
            warm=state["warm"],
            cool=state["cool"],
            brightness=state["brightness"],
            pwm=pwm
        )

        print(
            "Iter {:02d} | "
            "W {:5.1f}% C {:5.1f}% | "
            "PWM {:5.1f}% | "
            "CCT {:7.1f} K ({:+6.1f}) | "
            "Light {:5.1f}% ({:+5.1f})".format(
                iteration,
                state["warm"],
                state["cool"],
                state["brightness"],
                measured_cct,
                cct_error,
                measured_brightness,
                brightness_error
            )
        )

        cct_ok = cct_controller.is_target_reached(
            measured_cct
        )

        brightness_ok = (
            brightness_controller.is_target_reached(
                measured_brightness
            )
        )

        if cct_ok and brightness_ok:
            print(
                "STATUS: TARGET LOCKED | "
                "CCT {:.1f} K | Light {:.1f}%".format(
                    measured_cct,
                    measured_brightness
                )
            )

        if not cct_ok:
            warm, cool = cct_controller.adjust(
                warm,
                cool,
                measured_cct
            )

        if not brightness_ok:
            brightness = brightness_controller.adjust(
                brightness,
                measured_brightness
            )

    logger.close()

    print()
    print("TRACKING SESSION COMPLETED")
    print("Control loop finished after monitoring period.")


def run_real(target_cct, target_brightness, args):
    print("MODE: REAL")
    print(
        "TARGET: {:.0f} K / {:.1f}% brightness".format(
            target_cct,
            target_brightness
        )
    )

    esp32 = create_esp32_client_from_args(
        args
    )

    spectral_estimator = SpectralRatioEstimator()
    brightness_estimator = BrightnessEstimator()

    cct_feedback = CCTFeedbackController(
        warm_cct=3000.0,
        cool_cct=6500.0,
        gain=0.5,
        tolerance_kelvin=50.0,
        max_correction=5.0
    )

    brightness_feedback = BrightnessFeedbackController(
        gain=0.5,
        tolerance=2.0,
        max_correction=8.0
    )

    try:
        health = esp32.health()

        print("ESP32 ONLINE")
        print(health)

        min_cct = 3000.0
        max_cct = 6500.0

        target_cool_ratio = (
            float(target_cct) - min_cct
        ) / (
            max_cct - min_cct
        )

        target_cool_ratio = max(
            0.0,
            min(1.0, target_cool_ratio)
        )

        target_cool = target_cool_ratio * 100.0
        target_warm = 100.0 - target_cool

        command_cool = target_cool
        command_brightness = float(target_brightness)

        print(
            "SPECTRAL TARGET: "
            "WARM {:.1f}% / COOL {:.1f}%".format(
                target_warm,
                target_cool
            )
        )

        for iteration in range(1, 8):
            command_warm = 100.0 - command_cool

            warm_output = (
                command_warm
                * command_brightness
                / 100.0
            )

            cool_output = (
                command_cool
                * command_brightness
                / 100.0
            )

            print()
            print("ITERATION", iteration)

            print(
                "COMMAND: "
                "WARM {:.2f}% / COOL {:.2f}% "
                "| BRIGHTNESS CMD {:.2f}%".format(
                    warm_output,
                    cool_output,
                    command_brightness
                )
            )

            esp32.set_warm_cool(
                warm_output,
                cool_output
            )

            time.sleep(1)

            # İlk okuma stale olabildigi icin at
            esp32.read_spectral()

            spectral = esp32.read_spectral()

            estimate = spectral_estimator.estimate(
                spectral
            )

            measured_warm = estimate["warm_percent"]
            measured_cool = estimate["cool_percent"]
            measured_cct = estimate["estimated_cct"]

            measured_brightness = brightness_estimator.estimate(
                spectral["VIS"],
                measured_cct
            )

            print(
                "MEASURED: "
                "WARM {:.2f}% / COOL {:.2f}%".format(
                    measured_warm,
                    measured_cool
                )
            )

            print(
                "MEASURED CCT       : {:.0f} K".format(
                    measured_cct
                )
            )

            print(
                "MEASURED BRIGHTNESS: {:.1f}%".format(
                    measured_brightness
                )
            )

            print(
                "CCT ERROR          : {:+.0f} K".format(
                    float(target_cct) - measured_cct
                )
            )

            print(
                "BRIGHTNESS ERROR   : {:+.1f}%".format(
                    float(target_brightness)
                    - measured_brightness
                )
            )

            print(
                "R1/R2              : {:.4f} / {:.4f}".format(
                    estimate["ratio_450_640"],
                    estimate["ratio_475_690"]
                )
            )

            cct_result = cct_feedback.calculate(
                target_cct=target_cct,
                measured_cct=measured_cct,
                current_cool=command_cool
            )

            brightness_result = brightness_feedback.calculate(
                target_brightness=target_brightness,
                measured_brightness=measured_brightness,
                current_brightness=command_brightness
            )

            if cct_result["locked"]:
                print("CCT STATUS        : LOCKED")
            else:
                print(
                    "CCT CORRECTION    : {:+.2f} Cool %".format(
                        cct_result["correction_cool"]
                    )
                )

            if brightness_result["locked"]:
                print("BRIGHTNESS STATUS : LOCKED")
            else:
                print(
                    "BRIGHTNESS CORRECT: {:+.2f}%".format(
                        brightness_result["correction"]
                    )
                )

            command_cool = cct_result["new_cool"]
            command_brightness = brightness_result["new_brightness"]

            if (
                cct_result["locked"]
                and brightness_result["locked"]
            ):
                print("STATUS: DUAL TARGET LOCKED")
                break

    except Exception as exc:
        print("ESP32 ERROR")
        print(exc)

    finally:
        try:
            esp32.off()
        except Exception:
            pass

        esp32.close()




def calculate_recipe_output(target_cct, target_brightness):
    min_cct = 3000.0
    max_cct = 6500.0

    target_cool_ratio = (
        float(target_cct) - min_cct
    ) / (
        max_cct - min_cct
    )

    target_cool_ratio = max(
        0.0,
        min(1.0, target_cool_ratio)
    )

    cool_mix = target_cool_ratio * 100.0
    warm_mix = 100.0 - cool_mix

    brightness = max(
        0.0,
        min(100.0, float(target_brightness))
    )

    warm_output = (
        warm_mix * brightness / 100.0
    )

    cool_output = (
        cool_mix * brightness / 100.0
    )

    return {
        "warm_mix": warm_mix,
        "cool_mix": cool_mix,
        "warm_output": warm_output,
        "cool_output": cool_output
    }


def linear_fade_warm_cool(
    esp32,
    start_warm,
    start_cool,
    target_warm,
    target_cool,
    duration=3.0,
    steps=150
):
    start_warm = float(start_warm)
    start_cool = float(start_cool)
    target_warm = float(target_warm)
    target_cool = float(target_cool)
    duration = max(float(duration), 0.01)

    start_time = time.monotonic()

    while True:
        elapsed = time.monotonic() - start_time

        if elapsed >= duration:
            break

        ratio = elapsed / duration

        warm = (
            start_warm
            + (target_warm - start_warm) * ratio
        )

        cool = (
            start_cool
            + (target_cool - start_cool) * ratio
        )

        if not safe_set_warm_cool(
            esp32,
            warm,
            cool
        ):
            print("FADE ABORTED: ESP32 unavailable")
            return False

        # ESP32 command time is included in elapsed time.
        # This sleep only limits unnecessary update frequency.
        time.sleep(0.02)

    if not safe_set_warm_cool(
        esp32,
        target_warm,
        target_cool
    ):
        print("FADE FINAL COMMAND FAILED: ESP32 unavailable")
        return False

    return True


def smooth_set_warm_cool(
    esp32,
    start_warm,
    start_cool,
    target_warm,
    target_cool,
    duration=3.0,
    steps=90
):
    import math

    start_warm = float(start_warm)
    start_cool = float(start_cool)
    target_warm = float(target_warm)
    target_cool = float(target_cool)

    steps = max(int(steps), 1)
    delay = float(duration) / steps

    for step in range(1, steps + 1):
        t = step / steps

        # Cosine ease-in / ease-out:
        # soft start -> faster middle -> soft finish
        ratio = 0.5 - 0.5 * math.cos(math.pi * t)

        warm = (
            start_warm
            + (target_warm - start_warm) * ratio
        )

        cool = (
            start_cool
            + (target_cool - start_cool) * ratio
        )

        if not safe_set_warm_cool(
            esp32,
            warm,
            cool
        ):
            print("SMOOTH FADE ABORTED: ESP32 unavailable")
            return False

        time.sleep(delay)

    return True




def manual_smooth_transition(
    esp32,
    start_warm,
    start_cool,
    target_warm,
    target_cool,
    duration=0.8
):
    import math

    start_warm = float(start_warm)
    start_cool = float(start_cool)
    target_warm = float(target_warm)
    target_cool = float(target_cool)

    duration = max(float(duration), 0.05)
    start_time = time.monotonic()

    current_warm = start_warm
    current_cool = start_cool

    while True:
        # AUTO veya yeni MANUAL hedefi geldiyse mevcut hareketi kes.
        state = system_state.get()

        if state.get("requested_mode") != "MANUAL":
            return current_warm, current_cool, True

        requested_cct = state.get("manual_target_cct")
        requested_brightness = state.get(
            "manual_target_brightness"
        )

        elapsed = time.monotonic() - start_time

        if elapsed >= duration:
            break

        t = elapsed / duration

        # Cosine ease-in/ease-out:
        # yumusak baslangic -> hizli orta -> yumusak bitis
        ratio = 0.5 - 0.5 * math.cos(math.pi * t)

        warm = (
            start_warm
            + (target_warm - start_warm) * ratio
        )

        cool = (
            start_cool
            + (target_cool - start_cool) * ratio
        )

        if not safe_set_warm_cool(
            esp32,
            warm,
            cool
        ):
            print("MANUAL TRANSITION ABORTED: ESP32 unavailable")
            return current_warm, current_cool, True

        current_warm = warm
        current_cool = cool

        # Web panelinde gercek uygulanmakta olan PWM'i goster.
        system_state.update(
            warm_output=warm,
            cool_output=cool
        )

        # Hedef transition basladiktan sonra degistiyse kes.
        current_target = (
            requested_cct,
            requested_brightness
        )

        active_target = (
            state.get("target_cct"),
            state.get("target_brightness")
        )

        if (
            requested_cct is not None
            and requested_brightness is not None
            and current_target != active_target
        ):
            return current_warm, current_cool, True

        time.sleep(0.02)

    if not safe_set_warm_cool(
        esp32,
        target_warm,
        target_cool
    ):
        print("MANUAL FINAL COMMAND FAILED: ESP32 unavailable")
        return current_warm, current_cool, True

    system_state.update(
        warm_output=target_warm,
        cool_output=target_cool
    )

    return target_warm, target_cool, False



def update_esp32_live_health(esp32):
    """
    ESP32 ve AS7343 durumunu gercek HEALTH komutundan gunceller.
    Basarili sorguda True/False degerlerini,
    haberlesme hatasinda ESP32=False ve AS7343=False yazar.
    """
    try:
        health = esp32.health()

        esp32_ok = bool(health.get("esp32", False))
        as7343_ok = bool(health.get("as7343", False))

        system_state.update_health(
            esp32=esp32_ok,
            as7343=as7343_ok
        )

        return True

    except Exception as exc:
        system_state.update_health(
            esp32=False,
            as7343=False
        )

        print("LIVE HEALTH ERROR:", exc)
        return False




def safe_set_warm_cool(esp32, warm, cool):
    """
    LED komutunu guvenli gonderir.
    ESP32 haberlesmesi koparsa ana programi kapatmaz.
    """
    try:
        esp32.set_warm_cool(warm, cool)

        system_state.update_health(
            esp32=True
        )

        return True

    except Exception as exc:
        system_state.update_health(
            esp32=False,
            as7343=False
        )

        print("ESP32 LED COMMAND ERROR:", exc)
        return False



def run_manual_control(
    esp32,
    current_warm,
    current_cool,
    standby_level
):
    print()
    print("=" * 60)
    print("MANUAL MODE ENTERED")
    print("=" * 60)

    spectral_estimator = SpectralRatioEstimator()
    brightness_estimator = BrightnessEstimator()

    cct_feedback = CCTFeedbackController(
        warm_cct=3000.0,
        cool_cct=6500.0,
        gain=0.5,
        tolerance_kelvin=50.0,
        max_correction=5.0
    )

    brightness_feedback = BrightnessFeedbackController(
        gain=0.5,
        tolerance=2.0,
        max_correction=8.0
    )

    active_target = None
    last_feedback = 0.0
    feedback_interval = 5.0

    last_health_check = 0.0
    health_interval = 3.0

    while True:
        now = time.monotonic()

        if now - last_health_check >= health_interval:
            update_esp32_live_health(esp32)
            last_health_check = now

        state = system_state.get()

        if state.get("requested_mode") != "MANUAL":
            print()
            print("MANUAL MODE EXIT REQUESTED")

            standby_ok = safe_set_warm_cool(
                esp32,
                standby_level,
                standby_level
            )

            if standby_ok:
                current_warm = standby_level
                current_cool = standby_level
            else:
                print(
                    "AUTO RESTORE LIGHT SKIPPED: ESP32 unavailable"
                )

            system_state.update(
                mode="AUTO",
                requested_mode=None,
                status="STANDBY",
                product=None,
                target_cct=None,
                measured_cct=None,
                target_brightness=None,
                measured_brightness=None,
                warm_output=current_warm,
                cool_output=current_cool
            )

            print("AUTO MODE RESTORED")
            print()

            return current_warm, current_cool

        target_cct = state.get("manual_target_cct")
        target_brightness = state.get(
            "manual_target_brightness"
        )

        if (
            target_cct is None
            or target_brightness is None
        ):
            time.sleep(0.2)
            continue

        target_cct = float(target_cct)
        target_brightness = float(target_brightness)

        requested_target = (
            target_cct,
            target_brightness
        )

        # Yeni MANUAL hedef geldiyse nominal seviyeye gec.
        if requested_target != active_target:
            active_target = requested_target

            print()
            print(
                "MANUAL TARGET: {:.0f} K / {:.1f}%".format(
                    target_cct,
                    target_brightness
                )
            )

            recipe_output = calculate_recipe_output(
                target_cct=target_cct,
                target_brightness=target_brightness
            )

            target_warm_output = float(
                recipe_output["warm_output"]
            )
            target_cool_output = float(
                recipe_output["cool_output"]
            )

            print(
                "MANUAL NOMINAL: WARM {:.2f}% / COOL {:.2f}%".format(
                    target_warm_output,
                    target_cool_output
                )
            )

            system_state.update(
                mode="MANUAL",
                status="ADJUSTING",
                product=None,
                target_cct=target_cct,
                target_brightness=target_brightness
            )

            current_warm, current_cool, interrupted = (
                manual_smooth_transition(
                    esp32=esp32,
                    start_warm=current_warm,
                    start_cool=current_cool,
                    target_warm=target_warm_output,
                    target_cool=target_cool_output,
                    duration=0.8
                )
            )

            if interrupted:
                continue

            system_state.update(
                status="TARGET HOLD",
                warm_output=current_warm,
                cool_output=current_cool
            )

            # Yeni MANUAL hedefinden hemen sonra AS7343 okumasi baslatma.
            # Kullanici slider/AUTO komutlari bu surede onceliklidir.
            last_feedback = time.monotonic()

        now = time.monotonic()

        if now - last_feedback < feedback_interval:
            time.sleep(0.1)
            continue

        last_feedback = now

        try:
            spectral = esp32.read_spectral()

            estimate = spectral_estimator.estimate(
                spectral
            )

            measured_cct = float(
                estimate["estimated_cct"]
            )

            measured_brightness = float(
                brightness_estimator.estimate(
                    spectral["VIS"],
                    measured_cct
                )
            )

            system_state.update(
                measured_cct=measured_cct,
                measured_brightness=measured_brightness
            )

            print()
            print(
                "MANUAL MEASURED: {:.0f} K / {:.1f}%".format(
                    measured_cct,
                    measured_brightness
                )
            )

            command_brightness = max(
                0.0,
                min(
                    100.0,
                    current_warm + current_cool
                )
            )

            if command_brightness > 0.01:
                command_cool = (
                    current_cool
                    / command_brightness
                    * 100.0
                )
            else:
                command_cool = 0.0

            cct_result = cct_feedback.calculate(
                target_cct=target_cct,
                measured_cct=measured_cct,
                current_cool=command_cool
            )

            brightness_result = (
                brightness_feedback.calculate(
                    target_brightness=target_brightness,
                    measured_brightness=measured_brightness,
                    current_brightness=command_brightness
                )
            )

            if (
                cct_result["locked"]
                and brightness_result["locked"]
            ):
                system_state.update(
                    status="TARGET HOLD",
                    warm_output=current_warm,
                    cool_output=current_cool
                )

                print("MANUAL STATUS: TARGET HOLD")
                continue

            command_cool = float(
                cct_result["new_cool"]
            )

            command_brightness = float(
                brightness_result["new_brightness"]
            )

            command_warm = 100.0 - command_cool

            new_warm_output = (
                command_warm
                * command_brightness
                / 100.0
            )

            new_cool_output = (
                command_cool
                * command_brightness
                / 100.0
            )

            # Apply AS7343 correction with an interruptible smooth transition.
            current_warm, current_cool, interrupted = (
                manual_smooth_transition(
                    esp32=esp32,
                    start_warm=current_warm,
                    start_cool=current_cool,
                    target_warm=new_warm_output,
                    target_cool=new_cool_output,
                    duration=0.6
                )
            )

            if interrupted:
                continue

            ambient_limit = (
                current_warm <= 0.01
                and current_cool <= 0.01
                and measured_brightness
                > target_brightness + 2.0
            )

            system_state.update(
                status=(
                    "AMBIENT LIMIT"
                    if ambient_limit
                    else "ADJUSTING"
                ),
                warm_output=current_warm,
                cool_output=current_cool,
                measured_cct=measured_cct,
                measured_brightness=measured_brightness
            )

            print(
                "MANUAL CORRECTION: "
                "WARM {:.2f}% / COOL {:.2f}%".format(
                    current_warm,
                    current_cool
                )
            )

        except Exception as exc:
            print(
                "MANUAL AS7343 ERROR:",
                exc
            )

            time.sleep(1.0)


def run_continuous_real(args):
    import cv2
    import numpy as np

    STANDBY_LEVEL = 2.0
    ANALYSIS_LEVEL = 10.0
    PRESENCE_THRESHOLD = 15.0
    REQUIRED_HITS = 3

    esp32 = create_esp32_client_from_args(
        args
    )

    camera = None

    current_warm = STANDBY_LEVEL
    current_cool = STANDBY_LEVEL

    try:
        print()
        print("=" * 70)
        print("CONTINUOUS SHOWCASE MODE")
        print("=" * 70)
        print(
            "STANDBY: WARM {:.1f}% / COOL {:.1f}%".format(
                STANDBY_LEVEL,
                STANDBY_LEVEL
            )
        )
        print(
            "PRESENCE THRESHOLD: STD >= {:.1f}".format(
                PRESENCE_THRESHOLD
            )
        )
        print(
            "CONFIRMATION: {} consecutive hits".format(
                REQUIRED_HITS
            )
        )
        print()

        standby_ok = safe_set_warm_cool(
            esp32,
            STANDBY_LEVEL,
            STANDBY_LEVEL
        )

        if standby_ok:
            current_warm = STANDBY_LEVEL
            current_cool = STANDBY_LEVEL
        else:
            print(
                "INITIAL STANDBY LIGHT SKIPPED: ESP32 unavailable"
            )

        system_state.update(
            status="STANDBY",
            warm_output=current_warm,
            cool_output=current_cool
        )

        update_esp32_live_health(esp32)

        time.sleep(5)

        camera = create_camera("imx219")
        camera.open()

        system_state.update_health(
            camera=True
        )

        time.sleep(5)

        presence_hits = 0

        CHANGE_PIXEL_THRESHOLD = 15.0
        PRESENCE_CHANGED_PERCENT = 0.7

        # -------------------------------------------------
        # STARTUP PRODUCT CHECK
        #
        # Sistem urun vitrindeyken acilirsa urunlu goruntuyu
        # bos vitrin referansi olarak kaydetme.
        # -------------------------------------------------

        print("CHECKING FOR PRODUCT AT STARTUP...")
        print("STARTUP ANALYSIS LIGHT: WARM 10.0% / COOL 10.0%")

        startup_light_ok = safe_set_warm_cool(
            esp32,
            10.0,
            10.0
        )

        if startup_light_ok:
            current_warm = 10.0
            current_cool = 10.0
            system_state.update(
                warm_output=current_warm,
                cool_output=current_cool
            )
        else:
            print(
                "STARTUP ANALYSIS LIGHT FAILED: "
                "ESP32 unavailable"
            )

        print("WAITING FOR STARTUP ANALYSIS LIGHT TO STABILIZE...")
        time.sleep(2.0)

        for _ in range(10):
            camera.read()

        startup_probe_frame = camera.read()

        h, w = startup_probe_frame.shape[:2]

        roi_w = int(w * 0.70)
        roi_h = int(h * 0.70)

        x1 = (w - roi_w) // 2
        y1 = (h - roi_h) // 2

        startup_classifier = create_classifier(
            classifier_type="imx219"
        )

        startup_decision_manager = AIDecisionManager(
            confidence_threshold=0.80
        )

        startup_confirmation = TemporalConfirmation(
            required_hits=3
        )

        startup_result = None

        for startup_frame_index in range(1, 4):
            startup_frame = camera.read()

            startup_prediction = startup_classifier.predict(
                startup_frame
            )

            startup_decision = startup_decision_manager.evaluate(
                startup_prediction
            )

            if startup_decision["accepted"]:
                startup_result = startup_confirmation.update(
                    startup_decision["product_class"]
                )
            else:
                startup_result = startup_confirmation.update(
                    "unknown"
                )

            print(
                "STARTUP AI FRAME {} | class={} | confidence={:.1f}%".format(
                    startup_frame_index,
                    startup_prediction.get(
                        "class",
                        "unknown"
                    ),
                    float(
                        startup_prediction.get(
                            "confidence",
                            0.0
                        )
                    ) * 100.0
                )
            )

            time.sleep(0.2)

        startup_product_present = bool(
            startup_result
            and startup_result.get("confirmed", False)
            and startup_result.get("product_class")
            in ("gold_like", "diamond_like")
        )

        reference_valid = False
        reference_gray = None

        if startup_product_present:
            print()
            print(
                "PRODUCT PRESENT AT STARTUP: {}".format(
                    startup_result["product_class"]
                )
            )
            print(
                "EMPTY REFERENCE CAPTURE DEFERRED "
                "UNTIL PRODUCT REMOVAL"
            )
            print()

            presence_hits = REQUIRED_HITS

        else:
            print()
            print("NO PRODUCT DETECTED AT STARTUP")
            print("RETURNING TO STANDBY FOR EMPTY REFERENCE...")

            standby_ok = safe_set_warm_cool(
                esp32,
                STANDBY_LEVEL,
                STANDBY_LEVEL
            )

            if standby_ok:
                current_warm = STANDBY_LEVEL
                current_cool = STANDBY_LEVEL
                system_state.update(
                    warm_output=current_warm,
                    cool_output=current_cool
                )
            else:
                print(
                    "STARTUP STANDBY RESTORE FAILED: "
                    "ESP32 unavailable"
                )

            print("WAITING FOR STANDBY LIGHT TO STABILIZE...")
            time.sleep(2.0)

            print("CAPTURING EMPTY STANDBY REFERENCE...")

            for _ in range(10):
                camera.read()

            reference_frame = camera.read()

            reference_roi = reference_frame[
                y1:y1 + roi_h,
                x1:x1 + roi_w
            ]

            reference_gray = cv2.cvtColor(
                reference_roi,
                cv2.COLOR_BGR2GRAY
            ).astype(np.float32)

            reference_valid = True

            print("EMPTY REFERENCE READY")
            print("WAITING FOR OBJECT...")
            print()

        last_health_check = 0.0
        health_interval = 3.0

        while True:
            now = time.monotonic()

            if now - last_health_check >= health_interval:
                health_before = system_state.get()["health"]
                esp32_was_ok = bool(
                    health_before.get("esp32", False)
                )

                update_esp32_live_health(esp32)

                health_after = system_state.get()["health"]
                esp32_is_ok = bool(
                    health_after.get("esp32", False)
                )

                if (not esp32_was_ok) and esp32_is_ok:
                    print()
                    print("ESP32 RECOVERED")
                    print("RESTORING AUTO STANDBY...")

                    recovery_standby_ok = safe_set_warm_cool(
                        esp32,
                        STANDBY_LEVEL,
                        STANDBY_LEVEL
                    )

                    if recovery_standby_ok:
                        current_warm = STANDBY_LEVEL
                        current_cool = STANDBY_LEVEL

                        system_state.update(
                            status="STANDBY",
                            warm_output=current_warm,
                            cool_output=current_cool
                        )

                        print(
                            "WAITING FOR RECOVERY LIGHT TO STABILIZE..."
                        )
                        time.sleep(5.0)

                        print(
                            "RECAPTURING EMPTY STANDBY REFERENCE..."
                        )

                        for _ in range(10):
                            camera.read()

                        reference_frame = camera.read()

                        reference_roi = reference_frame[
                            y1:y1 + roi_h,
                            x1:x1 + roi_w
                        ]

                        reference_gray = cv2.cvtColor(
                            reference_roi,
                            cv2.COLOR_BGR2GRAY
                        ).astype(np.float32)

                        reference_valid = True
                        startup_product_present = False
                        presence_hits = 0

                        print("RECOVERY EMPTY REFERENCE READY")
                        print("WAITING FOR OBJECT...")
                        print()
                    else:
                        print(
                            "RECOVERY STANDBY FAILED: "
                            "ESP32 unavailable"
                        )

                last_health_check = now

            state = system_state.get()

            if state.get("requested_mode") == "MANUAL":
                current_warm, current_cool = run_manual_control(
                    esp32=esp32,
                    current_warm=current_warm,
                    current_cool=current_cool,
                    standby_level=STANDBY_LEVEL
                )

                presence_hits = 0
                continue

            if startup_product_present:
                print(
                    "STARTUP PRODUCT -> ENTERING NORMAL "
                    "PRODUCT ANALYSIS"
                )
                presence_hits = REQUIRED_HITS
            elif reference_valid and reference_gray is not None:
                frame = camera.read()

                roi = frame[
                    y1:y1 + roi_h,
                    x1:x1 + roi_w
                ]

                gray = cv2.cvtColor(
                    roi,
                    cv2.COLOR_BGR2GRAY
                ).astype(np.float32)

                diff = np.abs(
                    gray - reference_gray
                )

                changed_percent = float(
                    np.mean(
                        diff > CHANGE_PIXEL_THRESHOLD
                    ) * 100.0
                )

                object_present = (
                    changed_percent >= PRESENCE_CHANGED_PERCENT
                )

                if object_present:
                    presence_hits += 1
                else:
                    presence_hits = 0

                print(
                    "CHANGED={:.2f}% | presence={} | hits={}/{}".format(
                        changed_percent,
                        "YES" if object_present else "NO",
                        presence_hits,
                        REQUIRED_HITS
                    )
                )

            else:
                print(
                    "EMPTY REFERENCE NOT READY - "
                    "WAITING FOR EMPTY REFERENCE"
                )
                presence_hits = 0
                time.sleep(0.2)
                continue

            if presence_hits >= REQUIRED_HITS:
                startup_product_present = False
                print()
                print("OBJECT CONFIRMED")
                print(
                    "ANALYSIS LIGHT: WARM {:.1f}% / COOL {:.1f}%".format(
                        ANALYSIS_LEVEL,
                        ANALYSIS_LEVEL
                    )
                )

                analysis_light_ok = safe_set_warm_cool(
                    esp32,
                    ANALYSIS_LEVEL,
                    ANALYSIS_LEVEL
                )

                if not analysis_light_ok:
                    print(
                        "ANALYSIS LIGHT SKIPPED: ESP32 unavailable"
                    )
                    presence_hits = 0
                    time.sleep(1.0)
                    continue

                current_warm = ANALYSIS_LEVEL
                current_cool = ANALYSIS_LEVEL

                # Allow camera exposure / white balance to settle
                # after the smooth lighting transition.
                time.sleep(2)

                print("ANALYSIS LIGHT READY")
                print()

                classifier = create_classifier(
                    classifier_type="imx219"
                )

                real_predictions = []

                for frame_index in range(1, 4):
                    frame = camera.read()
                    frame_prediction = classifier.predict(frame)
                    real_predictions.append(frame_prediction)

                    features = frame_prediction.get(
                        "features",
                        {}
                    )

                    print(
                        "AI FRAME {} | class={} | confidence={:.1f}% | "
                        "purple={} ({:.2f}%) | green={} ({:.2f}%)".format(
                            frame_index,
                            frame_prediction.get(
                                "class",
                                "unknown"
                            ),
                            float(
                                frame_prediction.get(
                                    "confidence",
                                    0.0
                                )
                            ) * 100.0,
                            features.get(
                                "purple_pixels",
                                0
                            ),
                            float(
                                features.get(
                                    "purple_percent",
                                    0.0
                                )
                            ),
                            features.get(
                                "green_pixels",
                                0
                            ),
                            float(
                                features.get(
                                    "green_percent",
                                    0.0
                                )
                            )
                        )
                    )

                    time.sleep(0.2)

                decision_manager = AIDecisionManager(
                    confidence_threshold=0.80
                )

                temporal_confirmation = TemporalConfirmation(
                    required_hits=3
                )

                confirmation = None

                for frame_prediction in real_predictions:
                    frame_decision = decision_manager.evaluate(
                        frame_prediction
                    )

                    if frame_decision["accepted"]:
                        confirmation = temporal_confirmation.update(
                            frame_decision["product_class"]
                        )
                    else:
                        confirmation = temporal_confirmation.update(
                            "unknown"
                        )

                if confirmation["confirmed"]:
                    detected_class = confirmation[
                        "product_class"
                    ]

                    print()
                    print(
                        "PRODUCT CONFIRMED: {}".format(
                            detected_class
                        )
                    )

                    recipe_manager = RecipeManager()

                    if not recipe_manager.exists(
                        detected_class
                    ):
                        print(
                            "RECIPE NOT FOUND: {}".format(
                                detected_class
                            )
                        )
                    else:
                        profile = recipe_manager.get(
                            detected_class
                        )

                        recipe_manager.validate(
                            profile
                        )

                        target_cct = float(
                            profile["target_cct"]
                        )

                        target_brightness = float(
                            profile["target_brightness"]
                        )

                        system_state.update(
                            status="PRODUCT DETECTED",
                            product=detected_class,
                            target_cct=target_cct,
                            target_brightness=target_brightness
                        )

                        recipe_output = calculate_recipe_output(
                            target_cct=target_cct,
                            target_brightness=target_brightness
                        )

                        target_warm_output = recipe_output[
                            "warm_output"
                        ]

                        target_cool_output = recipe_output[
                            "cool_output"
                        ]

                        print()
                        print(
                            "RECIPE: {} K / {:.1f}%".format(
                                int(target_cct),
                                target_brightness
                            )
                        )

                        print(
                            "NOMINAL PWM: "
                            "WARM {:.2f}% / COOL {:.2f}%".format(
                                target_warm_output,
                                target_cool_output
                            )
                        )

                        print()
                        print(
                            "RECIPE TRANSITION: 3.0 s LINEAR"
                        )

                        linear_fade_warm_cool(
                            esp32=esp32,
                            start_warm=current_warm,
                            start_cool=current_cool,
                            target_warm=target_warm_output,
                            target_cool=target_cool_output,
                            duration=3.0,
                            steps=150
                        )

                        current_warm = target_warm_output
                        current_cool = target_cool_output

                        system_state.update(
                            status="ADJUSTING",
                            warm_output=current_warm,
                            cool_output=current_cool
                        )

                        print(
                            "RECIPE NOMINAL LEVEL REACHED"
                        )

                        print()
                        print("=" * 60)
                        print("AS7343 CLOSED-LOOP FINE TUNING")
                        print("=" * 60)

                        spectral_estimator = SpectralRatioEstimator()
                        brightness_estimator = BrightnessEstimator()

                        cct_feedback = CCTFeedbackController(
                            warm_cct=3000.0,
                            cool_cct=6500.0,
                            gain=0.5,
                            tolerance_kelvin=50.0,
                            max_correction=5.0
                        )

                        brightness_feedback = BrightnessFeedbackController(
                            gain=0.5,
                            tolerance=2.0,
                            max_correction=8.0
                        )

                        min_cct = 3000.0
                        max_cct = 6500.0

                        command_cool = (
                            (float(target_cct) - min_cct)
                            / (max_cct - min_cct)
                            * 100.0
                        )

                        command_cool = max(
                            0.0,
                            min(100.0, command_cool)
                        )

                        command_brightness = float(
                            target_brightness
                        )

                        feedback_locked = False

                        for iteration in range(1, 8):
                            command_warm = (
                                100.0 - command_cool
                            )

                            warm_output = (
                                command_warm
                                * command_brightness
                                / 100.0
                            )

                            cool_output = (
                                command_cool
                                * command_brightness
                                / 100.0
                            )

                            print()
                            print(
                                "FEEDBACK ITERATION {}".format(
                                    iteration
                                )
                            )

                            print(
                                "COMMAND: "
                                "WARM {:.2f}% / COOL {:.2f}% "
                                "| BRIGHTNESS {:.2f}%".format(
                                    warm_output,
                                    cool_output,
                                    command_brightness
                                )
                            )

                            if not safe_set_warm_cool(
                                esp32,
                                warm_output,
                                cool_output
                            ):
                                print(
                                    "FEEDBACK ABORTED: ESP32 unavailable"
                                )
                                feedback_locked = False
                                break

                            # Gercekte uygulanmis son PWM degerlerini tut.
                            current_warm = warm_output
                            current_cool = cool_output

                            time.sleep(1.0)

                            try:
                                # Ilk spectral okuma stale olabildigi icin at.
                                esp32.read_spectral()

                                spectral = esp32.read_spectral()

                            except Exception as exc:
                                system_state.update_health(
                                    esp32=False,
                                    as7343=False
                                )

                                print(
                                    "FEEDBACK SPECTRAL ERROR:",
                                    exc
                                )

                                feedback_locked = False
                                break

                            system_state.update_health(
                                esp32=True,
                                as7343=True
                            )

                            estimate = spectral_estimator.estimate(
                                spectral
                            )

                            measured_cct = estimate[
                                "estimated_cct"
                            ]

                            measured_brightness = (
                                brightness_estimator.estimate(
                                    spectral["VIS"],
                                    measured_cct
                                )
                            )

                            system_state.update(
                                status="ADJUSTING",
                                measured_cct=measured_cct,
                                measured_brightness=measured_brightness,
                                warm_output=current_warm,
                                cool_output=current_cool
                            )

                            print(
                                "MEASURED CCT       : "
                                "{:.0f} K".format(
                                    measured_cct
                                )
                            )

                            print(
                                "MEASURED BRIGHTNESS: "
                                "{:.1f}%".format(
                                    measured_brightness
                                )
                            )

                            print(
                                "CCT ERROR          : "
                                "{:+.0f} K".format(
                                    float(target_cct)
                                    - measured_cct
                                )
                            )

                            print(
                                "BRIGHTNESS ERROR   : "
                                "{:+.1f}%".format(
                                    float(target_brightness)
                                    - measured_brightness
                                )
                            )

                            print(
                                "R1/R2              : "
                                "{:.4f} / {:.4f}".format(
                                    estimate[
                                        "ratio_450_640"
                                    ],
                                    estimate[
                                        "ratio_475_690"
                                    ]
                                )
                            )

                            cct_result = (
                                cct_feedback.calculate(
                                    target_cct=target_cct,
                                    measured_cct=measured_cct,
                                    current_cool=command_cool
                                )
                            )

                            brightness_result = (
                                brightness_feedback.calculate(
                                    target_brightness=(
                                        target_brightness
                                    ),
                                    measured_brightness=(
                                        measured_brightness
                                    ),
                                    current_brightness=(
                                        command_brightness
                                    )
                                )
                            )

                            if cct_result["locked"]:
                                print(
                                    "CCT STATUS        : LOCKED"
                                )
                            else:
                                print(
                                    "CCT CORRECTION    : "
                                    "{:+.2f} Cool %".format(
                                        cct_result[
                                            "correction_cool"
                                        ]
                                    )
                                )

                            if brightness_result["locked"]:
                                print(
                                    "BRIGHTNESS STATUS : LOCKED"
                                )
                            else:
                                print(
                                    "BRIGHTNESS CORRECT: "
                                    "{:+.2f}%".format(
                                        brightness_result[
                                            "correction"
                                        ]
                                    )
                                )

                            if (
                                cct_result["locked"]
                                and brightness_result["locked"]
                            ):
                                feedback_locked = True

                                system_state.update(
                                    status="TARGET HOLD",
                                    measured_cct=measured_cct,
                                    measured_brightness=measured_brightness,
                                    warm_output=current_warm,
                                    cool_output=current_cool
                                )

                                print()
                                print(
                                    "STATUS: DUAL TARGET LOCKED"
                                )
                                break

                            command_cool = (
                                cct_result["new_cool"]
                            )

                            command_brightness = (
                                brightness_result[
                                    "new_brightness"
                                ]
                            )

                        if not feedback_locked:
                            print()
                            print(
                                "STATUS: FEEDBACK ITERATION "
                                "LIMIT REACHED"
                            )

                        print("=" * 60)
                else:
                    print()
                    print("PRODUCT NOT CONFIRMED")

                print()
                print("MONITORING PRODUCT REMOVAL...")
                print()

                REMOVAL_STD_THRESHOLD = 15.0
                REMOVAL_REQUIRED_HITS = 2

                # Urun vitrinde kaldigi surece periyodik
                # AS7343 closed-loop kontrol araligi.
                PERIODIC_FEEDBACK_INTERVAL = 5.0

                removal_hits = 0
                active_product_recovery_pending = False
                removal_monitor_start = time.time()
                last_periodic_feedback = time.monotonic()

                while True:
                    # MANUAL mode has priority over AUTO product monitoring.
                    # Leave this inner loop so the outer loop can enter
                    # run_manual_control() immediately.
                    state = system_state.get()

                    if state.get("requested_mode") == "MANUAL":
                        print()
                        print("MANUAL REQUESTED - LEAVING AUTO PRODUCT MONITOR")
                        print()
                        break

                    frame = camera.read()

                    roi = frame[
                        y1:y1 + roi_h,
                        x1:x1 + roi_w
                    ]

                    gray = cv2.cvtColor(
                        roi,
                        cv2.COLOR_BGR2GRAY
                    )

                    removal_std = float(
                        gray.std()
                    )

                    removed_now = (
                        removal_std < REMOVAL_STD_THRESHOLD
                    )

                    if removed_now:
                        # Isik kaybi, urun kaldirildi gibi gorunebilir.
                        # Removal kararindan once ESP32'nin gercekten
                        # erisilebilir oldugunu dogrula.
                        health_before_removal = system_state.get()["health"]
                        esp32_before_removal = bool(
                            health_before_removal.get("esp32", False)
                        )

                        update_esp32_live_health(esp32)

                        removal_health = system_state.get()["health"]
                        esp32_available = bool(
                            removal_health.get("esp32", False)
                        )

                        if esp32_available:
                            if not esp32_before_removal:
                                active_product_recovery_pending = True
                            removal_hits += 1
                        else:
                            active_product_recovery_pending = True
                            removal_hits = 0
                            print(
                                "REMOVAL CHECK PAUSED: "
                                "ESP32 unavailable"
                            )
                            time.sleep(0.5)
                            continue
                    else:
                        removal_hits = 0

                    print(
                        "T={:.2f}s | RECIPE STD={:.2f} | removed={} | hits={}/{}".format(
                            time.time() - removal_monitor_start,
                            removal_std,
                            "YES" if removed_now else "NO",
                            removal_hits,
                            REMOVAL_REQUIRED_HITS
                        )
                    )

                    if removal_hits >= REMOVAL_REQUIRED_HITS:
                        print()
                        print("OBJECT REMOVED")
                        print("RETURNING TO STANDBY: 5.0 s LINEAR")

                        linear_fade_warm_cool(
                            esp32,
                            current_warm,
                            current_cool,
                            STANDBY_LEVEL,
                            STANDBY_LEVEL,
                            duration=5.0,
                            steps=100
                        )

                        current_warm = STANDBY_LEVEL
                        current_cool = STANDBY_LEVEL

                        system_state.update(
                            status="STANDBY",
                            product=None,
                            target_cct=None,
                            measured_cct=None,
                            target_brightness=None,
                            measured_brightness=None,
                            warm_output=STANDBY_LEVEL,
                            cool_output=STANDBY_LEVEL
                        )

                        print("STANDBY LEVEL REACHED")

                        presence_hits = 0

                        if not reference_valid:
                            print(
                                "CAPTURING FIRST EMPTY REFERENCE "
                                "AFTER STARTUP PRODUCT REMOVAL..."
                            )

                            time.sleep(2.0)

                            for _ in range(10):
                                camera.read()

                            reference_frame = camera.read()

                            reference_roi = reference_frame[
                                y1:y1 + roi_h,
                                x1:x1 + roi_w
                            ]

                            reference_gray = cv2.cvtColor(
                                reference_roi,
                                cv2.COLOR_BGR2GRAY
                            ).astype(np.float32)

                            reference_valid = True

                            print("EMPTY REFERENCE READY")
                        else:
                            print(
                                "USING ORIGINAL EMPTY REFERENCE"
                            )

                        print("WAITING FOR OBJECT...")
                        print()

                        break

                    # Urun hala vitrindeyse belirli araliklarla
                    # AS7343 ile CCT ve parlaklik kontrolu yap.
                    periodic_now = time.monotonic()

                    if (
                        periodic_now - last_periodic_feedback
                        >= PERIODIC_FEEDBACK_INTERVAL
                    ):
                        last_periodic_feedback = periodic_now

                        print()
                        print("-" * 60)
                        print("PERIODIC AS7343 CHECK")
                        print("-" * 60)

                        try:
                            health_before = system_state.get()["health"]
                            esp32_was_ok = bool(
                                health_before.get("esp32", False)
                            )

                            spectral = esp32.read_spectral()

                            system_state.update_health(
                                esp32=True,
                                as7343=True
                            )

                            if (
                                active_product_recovery_pending
                                or not esp32_was_ok
                            ):
                                print()
                                print(
                                    "ESP32 RECOVERED DURING ACTIVE PRODUCT"
                                )
                                print(
                                    "RESTORING ACTIVE PRODUCT OUTPUT: "
                                    "WARM {:.2f}% / COOL {:.2f}%".format(
                                        current_warm,
                                        current_cool
                                    )
                                )

                                recovery_output_ok = (
                                    safe_set_warm_cool(
                                        esp32,
                                        current_warm,
                                        current_cool
                                    )
                                )

                                if recovery_output_ok:
                                    system_state.update(
                                        warm_output=current_warm,
                                        cool_output=current_cool
                                    )

                                    print(
                                        "ACTIVE PRODUCT OUTPUT RESTORED"
                                    )

                                    print(
                                        "WAITING FOR RECOVERY LIGHT "
                                        "TO STABILIZE..."
                                    )
                                    time.sleep(2.0)

                                    print(
                                        "RE-READING AS7343 "
                                        "AFTER RECOVERY..."
                                    )
                                    spectral = esp32.read_spectral()
                                    active_product_recovery_pending = False
                                else:
                                    print(
                                        "ACTIVE PRODUCT OUTPUT "
                                        "RESTORE FAILED"
                                    )

                            estimate = spectral_estimator.estimate(
                                spectral
                            )

                            measured_cct = estimate[
                                "estimated_cct"
                            ]

                            measured_brightness = (
                                brightness_estimator.estimate(
                                    spectral["VIS"],
                                    measured_cct
                                )
                            )

                            system_state.update(
                                measured_cct=measured_cct,
                                measured_brightness=measured_brightness
                            )

                            print(
                                "TARGET             : "
                                "{:.0f} K / {:.1f}%".format(
                                    float(target_cct),
                                    float(target_brightness)
                                )
                            )

                            print(
                                "MEASURED CCT       : "
                                "{:.0f} K".format(
                                    measured_cct
                                )
                            )

                            print(
                                "MEASURED BRIGHTNESS: "
                                "{:.1f}%".format(
                                    measured_brightness
                                )
                            )

                            print(
                                "CCT ERROR          : "
                                "{:+.0f} K".format(
                                    float(target_cct)
                                    - measured_cct
                                )
                            )

                            print(
                                "BRIGHTNESS ERROR   : "
                                "{:+.1f}%".format(
                                    float(target_brightness)
                                    - measured_brightness
                                )
                            )

                            cct_result = (
                                cct_feedback.calculate(
                                    target_cct=target_cct,
                                    measured_cct=measured_cct,
                                    current_cool=command_cool
                                )
                            )

                            brightness_result = (
                                brightness_feedback.calculate(
                                    target_brightness=(
                                        target_brightness
                                    ),
                                    measured_brightness=(
                                        measured_brightness
                                    ),
                                    current_brightness=(
                                        command_brightness
                                    )
                                )
                            )

                            if (
                                cct_result["locked"]
                                and brightness_result["locked"]
                            ):
                                system_state.update(
                                    status="TARGET HOLD",
                                    warm_output=current_warm,
                                    cool_output=current_cool
                                )

                                print(
                                    "PERIODIC STATUS    : "
                                    "TARGET HOLD"
                                )

                            else:
                                command_cool = (
                                    cct_result["new_cool"]
                                )

                                command_brightness = (
                                    brightness_result[
                                        "new_brightness"
                                    ]
                                )

                                command_warm = (
                                    100.0 - command_cool
                                )

                                new_warm_output = (
                                    command_warm
                                    * command_brightness
                                    / 100.0
                                )

                                new_cool_output = (
                                    command_cool
                                    * command_brightness
                                    / 100.0
                                )

                                print(
                                    "PERIODIC CORRECTION: "
                                    "WARM {:.2f}% / COOL {:.2f}%".format(
                                        new_warm_output,
                                        new_cool_output
                                    )
                                )

                                correction_ok = safe_set_warm_cool(
                                    esp32,
                                    new_warm_output,
                                    new_cool_output
                                )

                                if not correction_ok:
                                    print(
                                        "PERIODIC CORRECTION SKIPPED: "
                                        "ESP32 unavailable"
                                    )
                                else:
                                    current_warm = (
                                        new_warm_output
                                    )

                                    current_cool = (
                                        new_cool_output
                                    )

                                    system_state.update(
                                        status="ADJUSTING",
                                        warm_output=current_warm,
                                        cool_output=current_cool,
                                        measured_cct=measured_cct,
                                        measured_brightness=measured_brightness
                                    )

                                ambient_limit = (
                                    new_warm_output <= 0.01
                                    and new_cool_output <= 0.01
                                    and measured_brightness
                                    > float(target_brightness) + 2.0
                                )

                                if ambient_limit:
                                    system_state.update(
                                        status="AMBIENT LIMIT"
                                    )

                                    print(
                                        "PERIODIC STATUS    : "
                                        "AMBIENT LIMIT"
                                    )
                                    print(
                                        "TARGET NOT REACHABLE: "
                                        "EXTERNAL LIGHT EXCEEDS "
                                        "CONTROLLABLE RANGE"
                                    )
                                else:
                                    print(
                                        "PERIODIC STATUS    : "
                                        "CORRECTION APPLIED"
                                    )

                        except Exception as exc:
                            system_state.update_health(
                                esp32=False,
                                as7343=False
                            )

                            print(
                                "PERIODIC AS7343 ERROR:"
                            )
                            print(exc)

                        print("-" * 60)
                        print()

                    time.sleep(0.1)

                continue

            time.sleep(0.7)

    except KeyboardInterrupt:
        print()
        print("CONTINUOUS MODE STOPPED")

    finally:
        if camera is not None:
            camera.close()

        try:
            if (
                abs(current_warm - STANDBY_LEVEL) > 0.01
                or abs(current_cool - STANDBY_LEVEL) > 0.01
            ):
                print()
                print("RETURNING TO STANDBY...")

                standby_reached = smooth_set_warm_cool(
                    esp32=esp32,
                    start_warm=current_warm,
                    start_cool=current_cool,
                    target_warm=STANDBY_LEVEL,
                    target_cool=STANDBY_LEVEL,
                    duration=3.0,
                    steps=90
                )

                if standby_reached:
                    current_warm = STANDBY_LEVEL
                    current_cool = STANDBY_LEVEL
                    system_state.update(
                        status="STANDBY",
                        warm_output=STANDBY_LEVEL,
                        cool_output=STANDBY_LEVEL
                    )
                    print("FINAL STANDBY REACHED")
                else:
                    print(
                        "FINAL STANDBY NOT REACHED: "
                        "ESP32 unavailable"
                    )

        except KeyboardInterrupt:
            print()
            print("SHUTDOWN INTERRUPTED")
            print("TRYING DIRECT STANDBY...")

            try:
                if safe_set_warm_cool(
                    esp32,
                    STANDBY_LEVEL,
                    STANDBY_LEVEL
                ):
                    current_warm = STANDBY_LEVEL
                    current_cool = STANDBY_LEVEL
                    system_state.update(
                        status="STANDBY",
                        warm_output=STANDBY_LEVEL,
                        cool_output=STANDBY_LEVEL
                    )
                    print("FINAL STANDBY REACHED")
                else:
                    print(
                        "FINAL STANDBY NOT REACHED: "
                        "ESP32 unavailable"
                    )
            except (KeyboardInterrupt, Exception):
                print(
                    "FINAL STANDBY NOT REACHED: "
                    "shutdown interrupted"
                )

        except Exception as exc:
            print("FINAL STANDBY ERROR:", exc)

        try:
            esp32.close()
        except Exception:
            pass


def main():
    args = parse_args()

    if args.continuous:
        if MODE != "real":
            print("ERROR: --continuous requires MODE=real")
            return

        if not args.ai:
            print("ERROR: --continuous requires --ai")
            return

        if args.camera != "imx219":
            print("ERROR: --continuous requires --camera imx219")
            return

        system_state.update(
            status="STARTING",
            mode="AUTO"
        )

        web_thread = threading.Thread(
            target=run_web_server,
            name="MeraledWebServer",
            daemon=True
        )
        web_thread.start()

        print()
        print("WEB PANEL STARTED")
        print("PORT      : 8080")
        print()

        run_continuous_real(args)
        return

    profile_manager = ProfileManager()

    if args.ai:
        try:
            camera = create_camera(
                camera_type=args.camera
            )

            classifier = create_classifier(
                classifier_type=args.camera,
                product_class=args.mock_product,
                confidence=args.mock_confidence
            )

            if args.camera == "mock":
                prediction = classifier.predict()

            else:
                analysis_esp32 = create_esp32_client_from_args(
                    args
                )

                try:
                    print()
                    print("AI ANALYSIS LIGHT: WARM 50% / COOL 50%")

                    analysis_esp32.set_warm_cool(
                        50.0,
                        50.0
                    )

                    # Allow analysis illumination to stabilize.
                    time.sleep(3)

                    camera.open()

                    # Let camera exposure / white balance settle.
                    time.sleep(3)

                    real_predictions = []

                    for frame_index in range(1, 4):
                        frame = camera.read()
                        frame_prediction = classifier.predict(frame)
                        real_predictions.append(frame_prediction)

                        print(
                            "AI FRAME {} | class={} | confidence={:.1f}% | R/B={}".format(
                                frame_index,
                                frame_prediction.get("class", "unknown"),
                                float(frame_prediction.get("confidence", 0.0)) * 100.0,
                                frame_prediction.get("features", {}).get("r_b_ratio")
                            )
                        )

                        time.sleep(0.2)

                    prediction = real_predictions[-1]

                except NotImplementedError as exc:
                    print()
                    print("=" * 70)
                    print("CAMERA NOT READY")
                    print("=" * 70)
                    print("Camera backend :", args.camera)
                    print("Reason         :", exc)
                    print()
                    print(
                        "IMX219 integration layer is ready, "
                        "but real camera capture is not enabled yet."
                    )
                    return

                except RuntimeError as exc:
                    print()
                    print("=" * 70)
                    print("CAMERA ERROR")
                    print("=" * 70)
                    print("Camera backend :", args.camera)
                    print("Reason         :", exc)
                    return

                finally:
                    camera.close()
                    analysis_esp32.close()

        except ValueError as exc:
            print("AI ERROR:", exc)
            return

        decision_manager = AIDecisionManager(
            confidence_threshold=0.80
        )

        decision = decision_manager.evaluate(
            prediction
        )

        if not decision["accepted"]:
            print()
            print("=" * 70)
            print("AI DECISION REJECTED")
            print("=" * 70)
            print(
                "Detected class :",
                prediction.get("class", "unknown")
            )
            print(
                "Confidence     : {:.1f}%".format(
                    decision["confidence"] * 100.0
                )
            )
            print(
                "Reason         :",
                decision["reason"]
            )
            print(
                "Result         : UNKNOWN"
            )
            print()
            print(
                "Lighting recipe was not changed."
            )
            return

        detected_class = decision["product_class"]
        confidence = decision["confidence"]

        temporal_confirmation = TemporalConfirmation(
            required_hits=3
        )

        confirmation = None

        if args.camera == "mock":
            for _ in range(3):
                confirmation = temporal_confirmation.update(
                    detected_class
                )
        else:
            for frame_prediction in real_predictions:
                frame_decision = decision_manager.evaluate(
                    frame_prediction
                )

                if frame_decision["accepted"]:
                    confirmation = temporal_confirmation.update(
                        frame_decision["product_class"]
                    )
                else:
                    confirmation = temporal_confirmation.update(
                        "unknown"
                    )

            prediction = real_predictions[-1]

        if not confirmation["confirmed"]:
            print()
            print("=" * 70)
            print("AI PRODUCT NOT CONFIRMED")
            print("=" * 70)
            print("Product :", detected_class)
            print(
                "Hits    : {}/{}".format(
                    confirmation["hits"],
                    temporal_confirmation.required_hits
                )
            )
            print()
            print(
                "Lighting recipe was not changed."
            )
            return

        recipe_manager = RecipeManager()

        if not recipe_manager.exists(detected_class):
            print(
                "No lighting recipe for AI class:",
                detected_class
            )
            return

        profile = recipe_manager.get(
            detected_class
        )

        recipe_manager.validate(profile)

        target_cct = profile["target_cct"]
        target_brightness = profile["target_brightness"]

        print("AI DECISION")
        print("Product    :", detected_class)
        print(
            "Confidence : {:.1f}%".format(
                confidence * 100.0
            )
        )
        print(
            "Source     :",
            prediction["source"]
        )
        print()
        print("RECIPE SELECTED")
        print("Profile    :", profile["name"])
        print(
            "Target CCT : {:.0f} K".format(
                target_cct
            )
        )
        print(
            "Brightness : {:.1f}%".format(
                target_brightness
            )
        )
        print()

    elif args.profile:
        if not profile_manager.exists(args.profile):
            print("Unknown profile:", args.profile)
            print(
                "Available profiles:",
                ", ".join(profile_manager.list_profiles())
            )
            return

        profile = profile_manager.get(args.profile)

        target_cct = profile["target_cct"]
        target_brightness = profile["target_brightness"]

        print(
            "PROFILE: {} ({})".format(
                profile["name"],
                args.profile
            )
        )

    else:
        target_cct = max(
            3000.0,
            min(6500.0, args.cct)
        )

        target_brightness = max(
            0.0,
            min(100.0, args.brightness)
        )

    print("=" * 70)
    print("COLLBRAI SMART LIGHTING")
    print("Adaptive CCT + Brightness Controller")
    print("=" * 70)

    if MODE == "mock":
        run_mock(
            target_cct=target_cct,
            target_brightness=target_brightness,
            ambient_light=max(
                0.0,
                min(100.0, args.ambient)
            ),
            dynamic_ambient=args.dynamic_ambient,
            transition_start_cct=(
                4200.0 if args.ai else None
            ),
            transition_start_brightness=(
                85.0 if args.ai else None
            ),
            mock_ai_sequence=args.mock_ai_sequence
        )

    elif MODE == "real":
        run_real(
            target_cct=target_cct,
            target_brightness=target_brightness,
            args=args
        )

    else:
        print("Invalid MODE:", MODE)


if __name__ == "__main__":
    main()
