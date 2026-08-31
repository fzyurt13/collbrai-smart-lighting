from flask import Flask

app = Flask(__name__)

@app.route("/")
def index():
    return """
    <html>
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <title>Meraled Smart Lighting</title>
    </head>
    <body style="font-family: Arial; padding: 30px;">
        <h1>Meraled Smart Lighting</h1>
        <p>Jetson web panel is running.</p>
        <p>Status: ONLINE</p>
    </body>
    </html>
    """

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=False)
