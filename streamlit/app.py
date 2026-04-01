"""
Streamlit application with OAuth2 SSO integration for Cloud Foundry.

Demonstrates OAuth2 authentication using the Tanzu Single Sign-On service
(p-identity) on Cloud Foundry. Parses VCAP_SERVICES to extract SSO credentials
and secures the app with OAuth2 login.
"""

import json
import os
import secrets
from urllib.parse import urlencode

import requests
import streamlit as st


def get_sso_config():
    """
    Extract SSO configuration from VCAP_SERVICES (Cloud Foundry) or environment variables.

    Returns a tuple of (client_id, client_secret, auth_domain) or raises ValueError.
    """
    vcap_services = os.environ.get('VCAP_SERVICES')

    if vcap_services:
        try:
            vcap = json.loads(vcap_services)
            sso_services = vcap.get('p-identity', [])
            if not sso_services:
                raise ValueError("No p-identity service found in VCAP_SERVICES. "
                                 "Bind the app to an SSO service instance.")
            credentials = sso_services[0].get('credentials', {})
            return credentials['client_id'], credentials['client_secret'], credentials['auth_domain']
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Failed to parse SSO credentials from VCAP_SERVICES: {e}")

    client_id = os.environ.get('SSO_CLIENT_ID')
    client_secret = os.environ.get('SSO_CLIENT_SECRET')
    auth_domain = os.environ.get('SSO_AUTH_DOMAIN')

    if not all([client_id, client_secret, auth_domain]):
        raise ValueError(
            "SSO configuration not found. Set VCAP_SERVICES (Cloud Foundry) or "
            "SSO_CLIENT_ID, SSO_CLIENT_SECRET, and SSO_AUTH_DOMAIN environment variables."
        )

    return client_id, client_secret, auth_domain


def get_redirect_uri():
    """
    Determine the OAuth2 redirect URI for this Streamlit app.

    On Cloud Foundry, reads VCAP_APPLICATION to find the app's public URI.
    Falls back to REDIRECT_URI env var or localhost for local development.
    """
    vcap_app = os.environ.get('VCAP_APPLICATION')
    if vcap_app:
        try:
            app_info = json.loads(vcap_app)
            uris = app_info.get('application_uris', [])
            if uris:
                return f"https://{uris[0]}"
        except (json.JSONDecodeError, KeyError):
            pass

    return os.environ.get('REDIRECT_URI', 'http://localhost:8501')


def get_ssl_verify():
    """
    Determine SSL verification settings for OAuth requests.

    Cloud Foundry environments may use self-signed certificates. Set
    SSO_SKIP_SSL_VALIDATION=true to disable verification for dev/test.
    """
    if os.environ.get('SSO_SKIP_SSL_VALIDATION', '').lower() in ('true', '1', 'yes'):
        return False

    cf_ca_cert = '/etc/ssl/certs/ca-certificates.crt'
    if os.path.exists(cf_ca_cert):
        return cf_ca_cert

    for ca_path in ['/etc/pki/tls/certs/ca-bundle.crt', '/etc/ssl/ca-bundle.pem']:
        if os.path.exists(ca_path):
            return ca_path

    return True


def get_allowed_users():
    """Load allowed user emails from ALLOWED_USERS environment variable (comma-separated)."""
    allowed = os.environ.get('ALLOWED_USERS', '')
    return {email.strip().lower() for email in allowed.split(',') if email.strip()}


def is_user_allowed(user_info):
    """Check if the authenticated user is in the allowlist. Returns True if no allowlist is set."""
    allowed_users = get_allowed_users()
    if not allowed_users:
        return True
    email = (user_info.get('email') or user_info.get('user_name') or
             user_info.get('preferred_username') or '')
    return email.strip().lower() in allowed_users


def get_user_name(user_info):
    """
    Extract user's display name from OAuth2 user info.

    Tries claim names in order to handle different identity providers.
    """
    if not user_info:
        return "Guest"
    for claim in ['name', 'user_name', 'username', 'preferred_username', 'email', 'sub']:
        value = user_info.get(claim)
        if value and isinstance(value, str) and value.strip():
            return value.strip()
    return "Guest"


def exchange_code_for_token(code, client_id, client_secret, auth_domain, redirect_uri, ssl_verify):
    """Exchange an OAuth2 authorization code for an access token."""
    response = requests.post(
        f"{auth_domain}/oauth/token",
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': redirect_uri,
            'client_id': client_id,
            'client_secret': client_secret,
        },
        verify=ssl_verify,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def fetch_userinfo(auth_domain, access_token, ssl_verify):
    """Fetch user info from the SSO provider's userinfo endpoint."""
    response = requests.get(
        f"{auth_domain}/userinfo",
        headers={'Authorization': f"Bearer {access_token}"},
        verify=ssl_verify,
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def show_greeting(user_info):
    """Render the greeting page with authenticated user info."""
    name = get_user_name(user_info)
    st.markdown(f"""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&display=swap');

    .stApp {{
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%) !important;
        background-attachment: fixed;
    }}

    #MainMenu, footer, header {{visibility: hidden;}}

    .sso-container {{
        text-align: center;
        padding: 3rem 4rem;
        background: rgba(255, 255, 255, 0.03);
        backdrop-filter: blur(20px);
        border-radius: 24px;
        border: 1px solid rgba(255, 255, 255, 0.08);
        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.4),
                    inset 0 1px 0 rgba(255, 255, 255, 0.1);
        max-width: 500px;
        margin: 4rem auto;
        font-family: 'DM Sans', sans-serif;
        animation: fadeIn 0.6s ease-out;
    }}

    @keyframes fadeIn {{
        from {{ opacity: 0; transform: translateY(20px); }}
        to {{ opacity: 1; transform: translateY(0); }}
    }}

    .sso-icon {{
        width: 80px;
        height: 80px;
        margin: 0 auto 1.5rem;
        background: linear-gradient(135deg, #4ecdc4 0%, #44a08d 100%);
        border-radius: 20px;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 10px 30px rgba(78, 205, 196, 0.3);
        animation: pulse 3s ease-in-out infinite;
    }}

    @keyframes pulse {{
        0%, 100% {{ transform: scale(1); }}
        50% {{ transform: scale(1.05); }}
    }}

    .sso-title {{
        color: #ffffff;
        font-size: 2rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
        letter-spacing: -0.02em;
    }}

    .sso-greeting {{
        color: rgba(255, 255, 255, 0.7);
        font-size: 1.1rem;
        margin-bottom: 2rem;
        font-weight: 400;
    }}

    .sso-username {{
        color: #4ecdc4;
        font-weight: 500;
    }}

    .sso-badge {{
        display: inline-flex;
        align-items: center;
        gap: 0.5rem;
        padding: 0.6rem 1.2rem;
        background: rgba(78, 205, 196, 0.15);
        border: 1px solid rgba(78, 205, 196, 0.3);
        border-radius: 100px;
        color: #4ecdc4;
        font-size: 0.85rem;
        font-weight: 500;
        margin-bottom: 2rem;
    }}

    .sso-footer {{
        padding-top: 1.5rem;
        border-top: 1px solid rgba(255, 255, 255, 0.08);
        color: rgba(255, 255, 255, 0.4);
        font-size: 0.8rem;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }}

    .sso-footer a {{
        color: rgba(255, 255, 255, 0.6);
        text-decoration: none;
    }}

    .sso-footer a:hover {{
        color: #4ecdc4;
    }}

    .sso-logout {{
        background: rgba(255, 255, 255, 0.08);
        border: 1px solid rgba(255, 255, 255, 0.15);
        border-radius: 8px;
        color: rgba(255, 255, 255, 0.6);
        padding: 0.3rem 0.9rem;
        font-size: 0.8rem;
        text-decoration: none;
        cursor: pointer;
        font-family: 'DM Sans', sans-serif;
    }}

    .sso-logout:hover {{
        color: #ffffff;
        border-color: rgba(255, 255, 255, 0.3);
    }}
    </style>

    <div class="sso-container">
        <div class="sso-icon">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="white" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 3c1.66 0 3 1.34 3 3s-1.34 3-3 3-3-1.34-3-3 1.34-3 3-3zm0 14.2c-2.5 0-4.71-1.28-6-3.22.03-1.99 4-3.08 6-3.08 1.99 0 5.97 1.09 6 3.08-1.29 1.94-3.5 3.22-6 3.22z"/>
            </svg>
        </div>
        <div class="sso-title">Welcome!</div>
        <div class="sso-greeting">Hello, <span class="sso-username">{name}</span></div>
        <div class="sso-badge">
            <svg width="16" height="16" viewBox="0 0 24 24" fill="currentColor" xmlns="http://www.w3.org/2000/svg">
                <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/>
            </svg>
            Authenticated via SSO
        </div>
        <div class="sso-footer">
            <span>Secured by <a href="https://techdocs.broadcom.com/us/en/vmware-tanzu/platform/single-sign-on/1-16/sso/index.html" target="_blank">Tanzu Single Sign-On</a></span>
            <a href="?action=logout" class="sso-logout">Logout</a>
        </div>
    </div>
    """, unsafe_allow_html=True)


def main():
    st.set_page_config(page_title="Welcome - SSO Tile", page_icon="🔒", layout="centered")

    try:
        client_id, client_secret, auth_domain = get_sso_config()
    except ValueError as e:
        st.error(f"Configuration error: {e}")
        return

    ssl_verify = get_ssl_verify()
    redirect_uri = get_redirect_uri()
    params = st.query_params

    # Handle logout
    if params.get('action') == 'logout':
        st.session_state.pop('user', None)
        st.query_params.clear()
        st.rerun()

    # Handle OAuth2 callback
    if 'code' in params:
        with st.spinner("Completing login..."):
            try:
                token = exchange_code_for_token(
                    params['code'], client_id, client_secret,
                    auth_domain, redirect_uri, ssl_verify,
                )
                user_info = fetch_userinfo(auth_domain, token['access_token'], ssl_verify)

                if not is_user_allowed(user_info):
                    st.error("Access denied: your account is not authorized to use this application.")
                    return

                st.session_state['user'] = user_info
                st.query_params.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Authentication failed: {e}")
        return

    # Show greeting for authenticated users
    if 'user' in st.session_state:
        show_greeting(st.session_state['user'])
        return

    # Redirect unauthenticated users to the SSO authorization endpoint
    state = secrets.token_urlsafe(16)
    auth_url = f"{auth_domain}/oauth/authorize?{urlencode({
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': 'openid',
        'state': state,
    })}"
    st.markdown(
        f'<meta http-equiv="refresh" content="0;url={auth_url}">',
        unsafe_allow_html=True,
    )
    st.markdown(f"[Redirecting to login...]({auth_url})")


if __name__ == '__main__':
    main()
