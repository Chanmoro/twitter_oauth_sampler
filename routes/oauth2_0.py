import base64
import hashlib
import json
import os
import random
import string

import requests
from flask import Blueprint, render_template, redirect, session, request, url_for
from requests_oauthlib import OAuth2, OAuth2Session

oauth2_0_blueprint = Blueprint("oauth2_0", __name__, template_folder="templates")


TWITTER_APP_CLIENT_ID = os.getenv("TWITTER_APP_CLIENT_ID")
TWITTER_APP_CLIENT_SECRET = os.getenv("TWITTER_APP_CLIENT_SECRET")


@oauth2_0_blueprint.route("/")
def index():
    """
    セッションに認証したユーザー情報、アクセストークンがある場合は内容を表示する
    """
    authorized_user_response = session.get("oauth2_authorized_user_response", {})

    return render_template(
        "oauth2_0.html",
        oauth2_access_token=json.dumps(session.get("oauth2_access_token"), indent=2),
        callback_args=json.dumps(session.get("oauth2_callback_args"), indent=2),
        oauth2_code_verifier=session.get("oauth2_code_verifier"),
        oauth2_state=session.get("oauth2_state"),
        authorized_user=json.dumps(
            authorized_user_response.get("body"), indent=2, ensure_ascii=False
        ),
        response_status=authorized_user_response.get("status_code"),
        response_header=authorized_user_response.get("headers"),
    )


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
        redirect_uri="http://127.0.0.1:8000/oauth2_0/twitter_auth/callback",
        scope=["tweet.read", "users.read", "offline.access"],
        state=state,
    )


@oauth2_0_blueprint.route("/twitter_auth")
def twitter_auth():
    """
    twitter の認可の URL を取得してリダイレクトする
    """
    session.clear()

    oauth2_session = create_oauth2_session()
    code_verifier, code_challenge = generate_pkce_code()
    authorization_url, state = oauth2_session.authorization_url(
        "https://twitter.com/i/oauth2/authorize",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )

    session["oauth2_code_verifier"] = code_verifier
    session["oauth2_state"] = state
    return redirect(authorization_url)


def get_authorized_user(access_token: dict) -> dict:
    """
    twitter API v2 を利用して token に紐づく twitter アカウントの情報を取得する
    """
    oauth2 = OAuth2(
        token={
            "access_token": access_token["access_token"],
            "token_type": access_token["token_type"],
        }
    )
    res = requests.get(
        "https://api.twitter.com/2/users/me",
        auth=oauth2,
        params={
            "user.fields": ",".join(
                [
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
                ]
            )
        },
    )
    return {
        "status_code": res.status_code,
        "headers": "\n".join([f"{k}: {v}" for k, v in res.headers.items()]),
        "body": res.json(),
    }


@oauth2_0_blueprint.route("/twitter_auth/callback")
def twitter_auth_callback():
    """
    コールバックを処理する
    認可が正常に完了した場合はアクセストークンが取得できるので、トークンを利用して認可されたユーザーの情報を取得する
    """
    session["oauth2_callback_args"] = request.args
    # エラーがあった場合はクエリパラメータに error がセットされる
    error = request.args.get("error")
    if error:
        return redirect(url_for("oauth2_0.index"))

    code = request.args.get("code")
    oauth2_session = create_oauth2_session(session["oauth2_state"])
    oauth2_access_token = oauth2_session.fetch_token(
        token_url="https://api.twitter.com/2/oauth2/token",
        client_secret=TWITTER_APP_CLIENT_SECRET,
        code_verifier=session["oauth2_code_verifier"],
        code=code,
    )

    # 認可されたユーザー情報を取得する
    authorized_user_response = get_authorized_user(oauth2_access_token)

    # 簡易的にセッションにデータを保持するために dict に変換する
    session["oauth2_access_token"] = oauth2_access_token
    session["oauth2_authorized_user_response"] = authorized_user_response
    return redirect(url_for("oauth2_0.index"))
