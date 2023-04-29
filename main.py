from flask import Flask, render_template

from routes import oauth2_0_blueprint

app = Flask(__name__)
app.secret_key = "dummy secret"

app.register_blueprint(oauth2_0_blueprint, url_prefix="/oauth2_0")


@app.route("/")
def index():
    return render_template("index.html")
