import json
import os

import requests
from flask import Blueprint, render_template, redirect, session, request, url_for, current_app
from oauthlib.oauth2 import OAuth2Error
from requests_oauthlib import OAuth2, OAuth2Session

oauth2_0_blueprint = Blueprint("oauth2_0", __name__, template_folder="templates")


TWITTER_OAUTH2_CLIENT_ID = os.getenv("TWITTER_OAUTH2_CLIENT_ID")
TWITTER_OAUTH2_CLIENT_SECRET = os.getenv("TWITTER_OAUTH2_CLIENT_SECRET")


def create_oauth2_session(state: str | None = None) -> OAuth2Session:
    """
    requests_oauthlib の OAuth2Session を作成する
    新規に認可のセッションを開始するときは state=None, コールバックでの検証のためにセッションを復元するときは state が指定される
    """
    # scope に指定できる権限の種類はこちらの Scopes の項目を参照
    # https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code
    return OAuth2Session(
        TWITTER_OAUTH2_CLIENT_ID,
        redirect_uri="http://localhost:8000/oauth2_0/twitter_auth/callback",
        scope=["tweet.read", "users.read", "offline.access"],
        state=state,
    )


def generate_oauth2_pkce_params(oauth2_session: OAuth2Session) -> tuple[str, str, str]:
    """
    OAuth 2.0 with PKCE のためのパラメータを生成する
    """
    # OAuth2Session が保持している oauthlib.oauth2.Client が PKCE のパラメータ生成のメソッドを実装しているため _client に直接アクセス
    code_verifier = oauth2_session._client.create_code_verifier(128)
    code_challenge = oauth2_session._client.create_code_challenge(code_verifier, "S256")

    # 認可 URL を生成する
    authorization_url, state = oauth2_session.authorization_url(
        "https://twitter.com/i/oauth2/authorize",
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return authorization_url, code_verifier, state


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


@oauth2_0_blueprint.route("/")
def index():
    """
    セッションに認証したユーザー情報、アクセストークンがある場合は内容を表示する
    """
    authorized_user_response = session.get("oauth2_authorized_user_response", {})

    return render_template(
        "oauth2_0.html",
        oauth2_error=session.get("oauth2_error"),
        oauth2_access_token=json.dumps(session.get("oauth2_access_token"), indent=2),
        callback_args=json.dumps(session.get("oauth2_callback_args"), indent=2),
        oauth2_code_verifier=session.get("oauth2_code_verifier"),
        oauth2_state=session.get("oauth2_state"),
        authorized_user=json.dumps(authorized_user_response.get("body"), indent=2, ensure_ascii=False),
        response_status=authorized_user_response.get("status_code"),
        response_header=authorized_user_response.get("headers"),
    )


@oauth2_0_blueprint.route("/twitter_auth")
def twitter_auth():
    """
    twitter の認可の URL を取得してリダイレクトする
    """
    # 過去のセッションデータが残らないように削除する
    session.clear()

    authorization_url, code_verifier, state = generate_oauth2_pkce_params(create_oauth2_session())

    # コールバックで利用するために code_verifier, state をセッションに保存する
    session["oauth2_code_verifier"] = code_verifier
    session["oauth2_state"] = state
    return redirect(authorization_url)


@oauth2_0_blueprint.route("/twitter_auth/callback")
def twitter_auth_callback():
    """
    コールバックを処理する
    認可が正常に完了した場合はアクセストークンが取得できるので、トークンを利用して認可されたユーザーの情報を取得する
    """
    session["oauth2_callback_args"] = request.args

    # アクセストークンを取得する
    oauth2_session = create_oauth2_session(session["oauth2_state"])
    try:
        oauth2_access_token = oauth2_session.fetch_token(
            token_url="https://api.twitter.com/2/oauth2/token",
            client_secret=TWITTER_OAUTH2_CLIENT_SECRET,
            code_verifier=session["oauth2_code_verifier"],
            authorization_response=request.url,
        )
    except OAuth2Error as e:
        current_app.logger.exception(e)
        session["oauth2_error"] = f"{type(e)} {e.error} {e.description}"
        return redirect(url_for("oauth2_0.index"))

    # 認可されたユーザー情報を取得する
    authorized_user_response = get_authorized_user(oauth2_access_token)

    # 画面表示のためにデータをセッションに保存
    session["oauth2_access_token"] = oauth2_access_token
    session["oauth2_authorized_user_response"] = authorized_user_response
    return redirect(url_for("oauth2_0.index"))
