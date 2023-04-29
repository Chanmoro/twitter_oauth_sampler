from flask import Flask, redirect, url_for

from routes import oauth2_0_blueprint, oauth1_0a_blueprint

app = Flask(__name__)
app.secret_key = "dummy secret"

app.register_blueprint(oauth1_0a_blueprint, url_prefix="/oauth1_0a")
app.register_blueprint(oauth2_0_blueprint, url_prefix="/oauth2_0")


@app.route("/")
def index():
    return redirect(url_for("oauth1_0a.index"))
