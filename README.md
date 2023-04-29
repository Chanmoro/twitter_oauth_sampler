# twitter_oauth_sampler

Twitter OAuth authentication sampler.

## Environment Setup

- Set environment variables on your local machine
  - TWITTER_APP_CLIENT_ID
    - Set OAuth 2.0 Client ID value created in the twitter developer portal.
  - TWITTER_APP_CLIENT_SECRET
    - Set OAuth 2.0 Client Secret value created in the twitter developer portal.

## Run application

1. Start application
  - `$ docker-compose up`
2. Access to `http://127.0.0.1:8000/`

## Screen shots

- Click `twitter Login!` link to initiate twitter authentication.
![auth_error](https://raw.githubusercontent.com/Chanmoro/twitter_oauth2_sampler/main/docs/initial.png)

- If authentication is successful, authenticated user information and access token are displayed.
![auth_error](https://raw.githubusercontent.com/Chanmoro/twitter_oauth2_sampler/main/docs/auth_success.png)

- If authentication encounters an error, contents of parameters passed to callback are displayed.
![auth_error](https://raw.githubusercontent.com/Chanmoro/twitter_oauth2_sampler/main/docs/auth_error.png)
