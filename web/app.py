from flask import Flask, jsonify, render_template, request

try:
    from web.system_state import system_state
    from web.auth_store import verify_pin, change_pin
except ModuleNotFoundError:
    from system_state import system_state
    from auth_store import verify_pin, change_pin


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/splash")
def splash():
    return render_template("splash.html")


@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/setup")
def setup():
    return render_template("setup.html")


@app.route("/settings")
def settings():
    return render_template("settings.html")


@app.route("/profile")
def profile():
    return render_template("profile.html")


@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    pin = str(data.get("pin", ""))

    if not verify_pin(pin):
        return jsonify({
            "ok": False,
            "error": "Invalid PIN"
        }), 401

    return jsonify({
        "ok": True
    })


@app.route("/api/change-pin", methods=["POST"])
def api_change_pin():
    data = request.get_json(silent=True) or {}

    new_pin = str(data.get("new_pin", ""))

    try:
        change_pin(new_pin)
    except ValueError as exc:
        return jsonify({
            "ok": False,
            "error": str(exc)
        }), 400

    return jsonify({
        "ok": True
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
