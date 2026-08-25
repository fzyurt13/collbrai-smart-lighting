import argparse
import time

from config.settings import (
    MODE,
    ESP32_HOST,
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

    return parser.parse_args()


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


def run_real(target_cct, target_brightness):
    print("MODE: REAL")
    print(
        "TARGET: {:.0f} K / {:.1f}% brightness".format(
            target_cct,
            target_brightness
        )
    )

    esp32 = ESP32Client(
        port="/dev/ttyACM0",
        baudrate=115200,
        timeout=0.3,
        startup_delay=1.0
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
                spectral["VIS"]
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

def main():
    args = parse_args()

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
                try:
                    camera.open()

                    frame = camera.read()
                    prediction = classifier.predict(frame)

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

        for _ in range(3):
            confirmation = temporal_confirmation.update(
                detected_class
            )

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
            target_brightness=target_brightness
        )

    else:
        print("Invalid MODE:", MODE)


if __name__ == "__main__":
    main()
