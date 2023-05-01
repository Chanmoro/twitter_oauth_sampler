import json
import os

import requests
from authlib.integrations.base_client import OAuthError
from authlib.integrations.requests_client import OAuth1Session, OAuth1Auth
from flask import Blueprint, render_template, redirect, session, request, url_for, current_app

oauth1_0a_blueprint = Blueprint("oauth1_0a", __name__, template_folder="templates")


TWITTER_CONSUMER_KEYS_API_KEY = os.getenv("TWITTER_CONSUMER_KEYS_API_KEY")
TWITTER_CONSUMER_KEYS_API_KEY_SECRET = os.getenv("TWITTER_CONSUMER_KEYS_API_KEY_SECRET")


def get_authorized_user(access_token: str, access_token_secret: str) -> dict:
    """
    twitter API v2 を利用して token に紐づく twitter アカウントの情報を取得する
    """
    oauth1 = OAuth1Auth(
        TWITTER_CONSUMER_KEYS_API_KEY,
        TWITTER_CONSUMER_KEYS_API_KEY_SECRET,
        access_token,
        access_token_secret,
    )
    res = requests.get(
        "https://api.twitter.com/2/users/me",
        auth=oauth1,
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


@oauth1_0a_blueprint.route("/")
def index():
    """
    認可されたユーザー情報、アクセストークンの情報がセッションにある場合は内容を表示する
    """
    authorized_user_response = session.get("oauth1_authorized_user_response", {})

    return render_template(
        "oauth1_0a.html",
        oauth1_oauth_token=session.get("oauth1_oauth_token"),
        oauth1_oauth_token_secret=session.get("oauth1_oauth_token_secret"),
        oauth1_access_token=session.get("oauth1_access_token"),
        oauth1_access_token_secret=session.get("oauth1_access_token_secret"),
        callback_args=json.dumps(session.get("oauth1_callback_args"), indent=2),
        authorized_user=json.dumps(authorized_user_response.get("body"), indent=2, ensure_ascii=False),
        response_status=authorized_user_response.get("status_code"),
        response_header=authorized_user_response.get("headers"),
        oauth1_error=session.get("oauth1_error"),
    )


@oauth1_0a_blueprint.route("/twitter_auth")
def twitter_auth():
    """
    twitter の認可の URL を取得してリダイレクトする
    """
    session.clear()

    oauth1_session = OAuth1Session(
        TWITTER_CONSUMER_KEYS_API_KEY,
        TWITTER_CONSUMER_KEYS_API_KEY_SECRET,
        redirect_uri="http://localhost:8000/oauth1_0a/twitter_auth/callback",
    )

    request_token = oauth1_session.fetch_request_token("https://api.twitter.com/oauth/request_token")
    authorization_url = oauth1_session.create_authorization_url("https://api.twitter.com/oauth/authorize", request_token["oauth_token"])

    session["oauth1_oauth_token"] = request_token["oauth_token"]
    session["oauth1_oauth_token_secret"] = request_token["oauth_token_secret"]

    return redirect(authorization_url)


@oauth1_0a_blueprint.route("/twitter_auth/callback")
def twitter_auth_callback():
    """
    oauth のコールバックを処理する
    認可が正常に完了した場合はアクセストークンが取得できるので、トークンを利用して認可されたユーザーの情報を取得する
    """
    session["oauth1_callback_args"] = request.args

    oauth1_session = OAuth1Session(
        TWITTER_CONSUMER_KEYS_API_KEY,
        TWITTER_CONSUMER_KEYS_API_KEY_SECRET,
        token=session["oauth1_oauth_token"],
        oauth_token_secret=session["oauth1_oauth_token_secret"],
    )

    try:
        oauth1_session.parse_authorization_response(request.url)
        token = oauth1_session.fetch_access_token("https://api.twitter.com/oauth/access_token")
    except OAuthError as e:
        current_app.logger.exception(e)
        session["oauth1_error"] = f"{type(e)} {e}"
        return redirect(url_for("oauth1_0a.index"))

    # 認可されたユーザーの情報を取得する
    authorized_user_response = get_authorized_user(token["oauth_token"], token["oauth_token_secret"])

    session["oauth1_access_token"] = token
    # session["oauth1_access_token_secret"] = access_token_secret
    session["oauth1_authorized_user_response"] = authorized_user_response
    return redirect(url_for("oauth1_0a.index"))
