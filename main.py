import base64
import hashlib
import os
import random
import string

import orjson
import tweepy
from flask import Flask, render_template, redirect, session, request, url_for
from requests_oauthlib import OAuth2Session


app = Flask(__name__)
app.secret_key = "dummy secret"

TWITTER_APP_CLIENT_ID = os.getenv("TWITTER_APP_CLIENT_ID")
TWITTER_APP_CLIENT_SECRET = os.getenv("TWITTER_APP_CLIENT_SECRET")

TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"


def generate_pkce_code() -> tuple[str, str]:
    """
    Oauth2 PKCE 認証で使う code_verifier,  code_challenge を生成する
    NOTE: こちらを参考に実装
    https://www.camiloterevinto.com/post/oauth-pkce-flow-from-python-desktop
    """
    rand = random.SystemRandom()
    code_verifier = "".join(rand.choices(string.ascii_letters + string.digits, k=128))

    code_sha_256 = hashlib.sha256(code_verifier.encode("utf-8")).digest()
    b64 = base64.urlsafe_b64encode(code_sha_256)
    code_challenge = b64.decode("utf-8").replace("=", "")

    return code_verifier, code_challenge


def create_oauth2_session(state: str | None = None) -> OAuth2Session:
    """
    requests_oauthlib の OAuth2Session を作成する
    NOTE: 指定できるスコープの種類はこちらの Scopes の項目を参照
    https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code
    """
    return OAuth2Session(
        TWITTER_APP_CLIENT_ID,
        redirect_uri="http://127.0.0.1:8000/twitter_auth/callback",
        scope=["tweet.read", "users.read", "offline.access"],
        state=state,
    )


def get_user_info(access_token: str) -> tweepy.user.User:
    """
    token に紐づく twitter アカウントの情報を取得する
    """
    client = tweepy.Client(bearer_token=access_token)
    # 取得したいユーザー情報のフィールドを指定するとレスポンスに追加される
    # see: https://developer.twitter.com/en/docs/twitter-api/users/lookup/api-reference/get-users-me
    response = client.get_me(
        user_auth=False,
        user_fields=[
            "created_at",
            "description",
            "entities",
            "id",
            "location",
            "name",
            "pinned_tweet_id",
            "profile_image_url",
            "protected",
            "public_metrics",
            "url",
            "username",
            "verified",
            "verified_type",
            "withheld",
        ],
    )
    return response.data


@app.route("/health_check")
def health_check():
    return "OK"


@app.route("/")
def index():
    """
    セッションに認証したユーザー情報、アクセストークンがある場合は内容を表示する
    """
    user_info = session.get("user_info")
    oauth2_access_token = session.get("oauth2_access_token")

    # datetime オブジェクトの json ダンプを簡単にするために orjson を利用
    return render_template(
        "index.html",
        user_info=orjson.dumps(
            user_info, option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_INDENT_2
        ).decode()
        if user_info
        else None,  # noqa
        oauth2_access_token=orjson.dumps(
            oauth2_access_token, option=orjson.OPT_APPEND_NEWLINE | orjson.OPT_INDENT_2
        ).decode()
        if oauth2_access_token
        else None,  # noqa
    )


@app.route("/twitter_auth")
def twitter_auth():
    """
    twitter の認証 URL を取得してリダイレクトする
    """
    oauth2_session = create_oauth2_session()
    code_verifier, code_challenge = generate_pkce_code()
    authorization_url, state = oauth2_session.authorization_url(
        TWITTER_AUTH_URL, code_challenge=code_challenge, code_challenge_method="S256"
    )

    session["oauth_code_verifier"] = code_verifier
    session["oauth_state"] = state
    return redirect(authorization_url)


@app.route("/twitter_auth/callback")
def twitter_auth_callback():
    """
    認証のコールバックでのリダイレクトを処理する
    認証が正常に完了した場合はアクセストークンが取得できる
    """
    code = request.args.get("code")

    oauth2_session = create_oauth2_session(session["oauth_state"])
    oauth2_access_token = oauth2_session.fetch_token(
        token_url=TWITTER_TOKEN_URL,
        client_secret=TWITTER_APP_CLIENT_SECRET,
        code_verifier=session["oauth_code_verifier"],
        code=code,
    )

    user_info = get_user_info(oauth2_access_token["access_token"])

    # 簡易的にセッションにデータを保持するために dict に変換する
    session["oauth2_access_token"] = dict(oauth2_access_token)
    session["user_info"] = dict(user_info)
    return redirect(url_for("index"))
