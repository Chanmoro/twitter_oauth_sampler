# twitter oauth sampler

This is a demo application for Twitter API v2 using access tokens obtained through both OAuth1.0a user context and OAuth 2.0 with PKCE.

## Setup

- Set environment variables on your local machine. Each values can be obtained from [Twitter developer portal](https://developer.twitter.com/en/portal/products).
  - TWITTER_OAUTH2_CLIENT_ID
    - OAuth 2.0 Client ID value
  - TWITTER_OAUTH2_CLIENT_SECRET
    - OAuth 2.0 Client Secret value
  - TWITTER_CONSUMER_KEYS_API_KEY
    - API key in the "Consumer Keys" section
  - TWITTER_CONSUMER_KEYS_API_KEY_SECRET
    - API key secret in the "Consumer Keys" section

## Run application

1. Start application
  - `$ docker-compose up`
2. Access to `http://localhost:8000/`

## Screen shots

Click `Authorize Twitter` link to initiate Twitter authorization.  
If the authorization is successful, authorized user and access token will be displayed on the screen.

### OAuth1.0a
![oauth1](https://github.com/Chanmoro/twitter_oauth_sampler/raw/main/docs/oauth1.png)

### OAuth 2.0 with PKCE
![oauth2](https://github.com/Chanmoro/twitter_oauth_sampler/raw/main/docs/oauth2.png)
