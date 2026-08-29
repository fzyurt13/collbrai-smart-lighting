from flask import Flask, jsonify, render_template

try:
    from web.system_state import system_state
except ModuleNotFoundError:
    from system_state import system_state


app = Flask(__name__)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/state")
def api_state():
    return jsonify(system_state.get())


def run_web_server():
    app.run(
        host="0.0.0.0",
        port=8080,
        debug=False,
        use_reloader=False
    )


if __name__ == "__main__":
    run_web_server()
