import json
import os

import requests
import tweepy
from flask import Blueprint, render_template, redirect, session, request, url_for
from requests_oauthlib import OAuth1

oauth1_0a_blueprint = Blueprint("oauth1_0a", __name__, template_folder="templates")


TWITTER_CONSUMER_KEYS_API_KEY = os.getenv("TWITTER_CONSUMER_KEYS_API_KEY")
TWITTER_CONSUMER_KEYS_API_KEY_SECRET = os.getenv("TWITTER_CONSUMER_KEYS_API_KEY_SECRET")

TWITTER_AUTH_URL = "https://twitter.com/i/oauth2/authorize"
TWITTER_TOKEN_URL = "https://api.twitter.com/2/oauth2/token"


def get_authorized_user(access_token: str, access_token_secret: str) -> dict:
    """
    twitter API v2 を利用して token に紐づく twitter アカウントの情報を取得する
    """
    oauth1 = OAuth1(
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


def create_oauth1_user_handler() -> tweepy.OAuth1UserHandler:
    return tweepy.OAuth1UserHandler(
        consumer_key=TWITTER_CONSUMER_KEYS_API_KEY,
        consumer_secret=TWITTER_CONSUMER_KEYS_API_KEY_SECRET,
        callback="http://127.0.0.1:8000/oauth1_0a/twitter_auth/callback",
    )


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
        authorized_user=json.dumps(
            authorized_user_response.get("body"), indent=2, ensure_ascii=False
        ),
        response_status=authorized_user_response.get("status_code"),
        response_header=authorized_user_response.get("headers"),
    )


@oauth1_0a_blueprint.route("/twitter_auth")
def twitter_auth():
    """
    twitter の認可の URL を取得してリダイレクトする
    """
    session.clear()

    oauth1_user_handler = create_oauth1_user_handler()
    authorization_url = oauth1_user_handler.get_authorization_url()
    session["oauth1_oauth_token"] = oauth1_user_handler.request_token["oauth_token"]
    session["oauth1_oauth_token_secret"] = oauth1_user_handler.request_token[
        "oauth_token_secret"
    ]
    return redirect(authorization_url)


@oauth1_0a_blueprint.route("/twitter_auth/callback")
def twitter_auth_callback():
    """
    oauth のコールバックを処理する
    認可が正常に完了した場合はアクセストークンが取得できるので、トークンを利用して認可されたユーザーの情報を取得する
    """
    session["oauth1_callback_args"] = request.args
    oauth_verifier = request.args.get("oauth_verifier")

    # 認可の処理でエラーがあった場合はコールバックのパラメータに oauth_verifier が含まれない
    if not oauth_verifier:
        return redirect(url_for("oauth1_0a.index"))

    oauth1_user_handler = create_oauth1_user_handler()
    oauth1_user_handler.request_token = {
        "oauth_token": session["oauth1_oauth_token"],
        "oauth_token_secret": session["oauth1_oauth_token_secret"],
    }
    access_token, access_token_secret = oauth1_user_handler.get_access_token(
        oauth_verifier
    )

    # 認可されたユーザーの情報を取得する
    authorized_user_response = get_authorized_user(access_token, access_token_secret)

    session["oauth1_access_token"] = access_token
    session["oauth1_access_token_secret"] = access_token_secret
    session["oauth1_authorized_user_response"] = authorized_user_response
    return redirect(url_for("oauth1_0a.index"))
