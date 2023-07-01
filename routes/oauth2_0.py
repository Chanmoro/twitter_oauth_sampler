import json
import os

import requests
from authlib.common.security import generate_token
from authlib.integrations.base_client import OAuthError
from authlib.integrations.requests_client import OAuth2Session, OAuth2Auth
from authlib.oauth2.rfc7636 import create_s256_code_challenge
from flask import Blueprint, render_template, redirect, session, request, url_for, current_app

oauth2_0_blueprint = Blueprint("oauth2_0", __name__, template_folder="templates")


TWITTER_OAUTH2_CLIENT_ID = os.getenv("TWITTER_OAUTH2_CLIENT_ID")
TWITTER_OAUTH2_CLIENT_SECRET = os.getenv("TWITTER_OAUTH2_CLIENT_SECRET")


def create_oauth2_session(state: str | None = None) -> OAuth2Session:
    """
    Creates OAuth2Session with requests_oauthlib.
    When starting a new authorization session, state is None.
    When restoring a session for callback validation, state is specified.
    """
    # Refer to the Scopes section for the types of permissions that can be specified in scope.
    # NOTE: https://developer.twitter.com/en/docs/authentication/oauth-2-0/authorization-code
    return OAuth2Session(
        TWITTER_OAUTH2_CLIENT_ID,
        TWITTER_OAUTH2_CLIENT_SECRET,
        redirect_uri="http://localhost:8000/oauth2_0/twitter_auth/callback",
        scope=["tweet.read", "users.read", "offline.access"],
        state=state,
    )


def get_authorized_user(access_token: dict) -> dict:
    """
    Retrieve Twitter account data associated with the token using Twitter API v2.
    """
    oauth2 = OAuth2Auth(token=access_token)
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
    Display the data stored in the session.
    """
    authorized_user_response = session.get("oauth2_authorized_user_response", {})

    return render_template(
        "oauth2_0.html",
        oauth2_access_token=json.dumps(session.get("oauth2_access_token"), indent=2),
        callback_args=json.dumps(session.get("oauth2_callback_args"), indent=2),
        oauth2_code_verifier=session.get("oauth2_code_verifier"),
        oauth2_state=session.get("oauth2_state"),
        authorized_user=json.dumps(authorized_user_response.get("body"), indent=2, ensure_ascii=False),
        response_status=authorized_user_response.get("status_code"),
        response_header=authorized_user_response.get("headers"),
        oauth2_error=session.get("oauth2_error"),
    )


@oauth2_0_blueprint.route("/twitter_auth")
def twitter_auth():
    """
    Obtain the authorization URL for Twitter and redirect to it.
    """
    session.clear()

    oauth2_session = create_oauth2_session()

    # Generate code_verifier and code_challenge for use with PKCE.
    # NOTE: https://docs.authlib.org/en/latest/specs/rfc7636.html#specs-rfc7636
    code_verifier = generate_token(128)
    code_challenge = create_s256_code_challenge(code_verifier)

    authorization_url, state = oauth2_session.create_authorization_url(
        "https://twitter.com/i/oauth2/authorize", code_challenge=code_challenge, code_challenge_method="S256"
    )

    # Save code_verifier and state to the session for use in the callback.
    session["oauth2_code_verifier"] = code_verifier
    session["oauth2_state"] = state
    return redirect(authorization_url)


@oauth2_0_blueprint.route("/twitter_auth/callback")
def twitter_auth_callback():
    """
    Process the callback from Twitter.
    If authorization is successful, retrieve the authorized user's information.
    """
    session["oauth2_callback_args"] = request.args

    # Obtain the access token.
    oauth2_session = create_oauth2_session(session["oauth2_state"])
    try:
        oauth2_access_token = oauth2_session.fetch_token(
            "https://api.twitter.com/2/oauth2/token",
            authorization_response=request.url,
            code_verifier=session["oauth2_code_verifier"],
        )
    except OAuthError as e:
        current_app.logger.exception(e)
        session["oauth2_error"] = f"{type(e)} {e.error} {e.description}"
        return redirect(url_for("oauth2_0.index"))

    # Retrieve the authorized user's information.
    authorized_user_response = get_authorized_user(oauth2_access_token)

    # Save data to the session for display.
    session["oauth2_access_token"] = oauth2_access_token
    session["oauth2_authorized_user_response"] = authorized_user_response
    return redirect(url_for("oauth2_0.index"))
