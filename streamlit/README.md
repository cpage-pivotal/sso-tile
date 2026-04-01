# SSO Tile — Streamlit

A Streamlit application demonstrating OAuth2 authentication with [Tanzu Single Sign-On](https://techdocs.broadcom.com/us/en/vmware-tanzu/platform/single-sign-on/1-16/sso/index.html) (p-identity) on Cloud Foundry.

## Prerequisites

- Python 3.12+
- A bound `sso` service instance (p-identity) on Cloud Foundry, **or** a local identity provider with OAuth2/OIDC support

## Install dependencies

```bash
pip install -r requirements.txt
```

## Run locally

```bash
streamlit run app.py
```

The app runs at `http://localhost:8501` by default.

### Local environment variables

| Variable | Description |
|---|---|
| `SSO_CLIENT_ID` | OAuth2 client ID |
| `SSO_CLIENT_SECRET` | OAuth2 client secret |
| `SSO_AUTH_DOMAIN` | Base URL of the UAA authorization server (e.g. `https://my-plan.login.example.com`) |
| `REDIRECT_URI` | OAuth2 redirect URI (defaults to `http://localhost:8501`) |
| `SSO_SKIP_SSL_VALIDATION` | Set to `true` to disable SSL certificate verification |
| `ALLOWED_USERS` | Comma-separated list of permitted email addresses (omit to allow all authenticated users) |

## Deploy to Cloud Foundry

```bash
cf push
```

The app binds to the `sso` service instance declared in `manifest.yml`. The redirect URI is derived automatically from `VCAP_APPLICATION`.

## Access control

Set the `ALLOWED_USERS` environment variable to restrict access to specific accounts:

```bash
cf set-env sso-tile-streamlit ALLOWED_USERS "alice@example.com,bob@example.com"
cf restage sso-tile-streamlit
```

When unset, all authenticated users are permitted.

## OAuth2 flow

1. Unauthenticated users are immediately redirected to the SSO authorization endpoint.
2. After the user authenticates, the provider redirects back with an authorization code.
3. The app exchanges the code for an access token and fetches user info from `/userinfo`.
4. If an allowlist is configured, the user's email is checked before the session is created.
5. Logout is available via the link in the footer, which clears the Streamlit session.
