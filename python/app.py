"""
Flask application with OAuth2 SSO integration for Cloud Foundry.

This application demonstrates OAuth2 authentication using the Tanzu Single Sign-On
service (p-identity) on Cloud Foundry. It parses VCAP_SERVICES to extract SSO
credentials and secures all routes with OAuth2 login.
"""

import json
import os
import secrets
from functools import wraps

from authlib.integrations.flask_client import OAuth
from flask import Flask, redirect, render_template, session, url_for

app = Flask(__name__)

# Configure secret key for session management
app.secret_key = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))


def get_ssl_verify():
    """
    Determine SSL verification settings for OAuth requests.
    
    Cloud Foundry environments may use self-signed certificates. This function
    checks for CF-provided CA certificates or allows disabling verification
    via environment variable for development/testing.
    
    Returns:
        str or bool: Path to CA bundle, or False to disable verification
    """
    # Check if SSL verification should be disabled (for dev/test environments)
    if os.environ.get('SSO_SKIP_SSL_VALIDATION', '').lower() in ('true', '1', 'yes'):
        app.logger.warning("SSL verification disabled via SSO_SKIP_SSL_VALIDATION")
        return False
    
    # Check for Cloud Foundry system CA certificates
    cf_ca_cert = '/etc/ssl/certs/ca-certificates.crt'
    if os.path.exists(cf_ca_cert):
        app.logger.info(f"Using CF CA certificates: {cf_ca_cert}")
        return cf_ca_cert
    
    # Check for alternative CA cert locations
    alt_ca_paths = [
        '/etc/pki/tls/certs/ca-bundle.crt',  # RHEL/CentOS
        '/etc/ssl/ca-bundle.pem',  # OpenSUSE
    ]
    for ca_path in alt_ca_paths:
        if os.path.exists(ca_path):
            app.logger.info(f"Using CA certificates: {ca_path}")
            return ca_path
    
    # Default: use requests library default verification
    return True


def get_sso_config():
    """
    Extract SSO configuration from VCAP_SERVICES (Cloud Foundry) or environment variables.
    
    Returns a tuple of (client_id, client_secret, auth_domain) or raises an error
    if configuration is not available.
    """
    vcap_services = os.environ.get('VCAP_SERVICES')
    
    if vcap_services:
        # Running on Cloud Foundry - parse VCAP_SERVICES
        try:
            vcap = json.loads(vcap_services)
            sso_services = vcap.get('p-identity', [])
            
            if not sso_services:
                raise ValueError("No p-identity service found in VCAP_SERVICES. "
                               "Bind the app to an SSO service instance.")
            
            credentials = sso_services[0].get('credentials', {})
            client_id = credentials['client_id']
            client_secret = credentials['client_secret']
            auth_domain = credentials['auth_domain']
            
            app.logger.info(f"Configuring SSO client with auth_domain: {auth_domain}")
            app.logger.info(f"Client ID: {client_id}")
            
            return client_id, client_secret, auth_domain
            
        except (json.JSONDecodeError, KeyError) as e:
            raise ValueError(f"Failed to parse SSO credentials from VCAP_SERVICES: {e}")
    
    # Local development - use environment variables
    client_id = os.environ.get('SSO_CLIENT_ID')
    client_secret = os.environ.get('SSO_CLIENT_SECRET')
    auth_domain = os.environ.get('SSO_AUTH_DOMAIN')
    
    if not all([client_id, client_secret, auth_domain]):
        raise ValueError(
            "SSO configuration not found. Set VCAP_SERVICES (Cloud Foundry) or "
            "SSO_CLIENT_ID, SSO_CLIENT_SECRET, and SSO_AUTH_DOMAIN environment variables."
        )
    
    return client_id, client_secret, auth_domain


def configure_oauth(app):
    """Configure OAuth2 client with SSO provider."""
    client_id, client_secret, auth_domain = get_sso_config()
    ssl_verify = get_ssl_verify()
    
    oauth = OAuth(app)
    
    # Build fetch_token_kwargs based on SSL verification setting
    fetch_kwargs = {}
    if ssl_verify is not True:
        fetch_kwargs['verify'] = ssl_verify
    
    oauth.register(
        name='sso',
        client_id=client_id,
        client_secret=client_secret,
        authorize_url=f"{auth_domain}/oauth/authorize",
        access_token_url=f"{auth_domain}/oauth/token",
        userinfo_endpoint=f"{auth_domain}/userinfo",
        jwks_uri=f"{auth_domain}/token_keys",
        client_kwargs={
            'scope': 'openid',
            'verify': ssl_verify,
        },
        fetch_token_kwargs=fetch_kwargs,
    )
    
    # Store SSL verify setting for use in userinfo requests
    app.config['SSO_SSL_VERIFY'] = ssl_verify
    
    return oauth


# Initialize OAuth - will be None if not configured
oauth = None
try:
    oauth = configure_oauth(app)
except ValueError as e:
    app.logger.warning(f"OAuth not configured: {e}")


def get_user_name(user_info):
    """
    Extract user's display name from OAuth2 user info.
    
    Tries various common claim names to handle different identity providers:
    - name: Standard OIDC
    - user_name: UAA style
    - username: Common alternative
    - preferred_username: OIDC
    - email: Fallback
    - sub: Last resort - subject identifier
    """
    if not user_info:
        return "Guest"
    
    claim_names = ['name', 'user_name', 'username', 'preferred_username', 'email', 'sub']
    
    for claim in claim_names:
        value = user_info.get(claim)
        if value and isinstance(value, str) and value.strip():
            return value.strip()
    
    return "Guest"


def get_allowed_users():
    """Load allowed user emails from ALLOWED_USERS environment variable."""
    allowed = os.environ.get('ALLOWED_USERS', '')
    return {email.strip().lower() for email in allowed.split(',') if email.strip()}


def is_user_allowed(user_info):
    """Check if the authenticated user is in the allowlist. Returns True if no allowlist is configured."""
    allowed_users = get_allowed_users()
    if not allowed_users:
        return True
    email = user_info.get('email') or user_info.get('user_name') or user_info.get('preferred_username') or ''
    return email.strip().lower() in allowed_users


def login_required(f):
    """Decorator to require authentication for a route."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
@login_required
def greeting():
    """Display greeting page with authenticated user's name."""
    user_info = session.get('user', {})
    name = get_user_name(user_info)
    return render_template('greeting.html', name=name)


@app.route('/login')
def login():
    """Initiate OAuth2 login flow."""
    if oauth is None:
        return "OAuth not configured. Check server logs for details.", 500
    
    redirect_uri = url_for('callback', _external=True)
    return oauth.sso.authorize_redirect(redirect_uri)


@app.route('/login/oauth2/code/sso')
def callback():
    """Handle OAuth2 callback and store user info in session."""
    if oauth is None:
        return "OAuth not configured. Check server logs for details.", 500
    
    ssl_verify = app.config.get('SSO_SSL_VERIFY', True)
    
    # Fetch access token with SSL verification setting
    if ssl_verify is not True:
        token = oauth.sso.authorize_access_token(verify=ssl_verify)
        user_info = oauth.sso.userinfo(verify=ssl_verify)
    else:
        token = oauth.sso.authorize_access_token()
        user_info = oauth.sso.userinfo()
    
    if not is_user_allowed(user_info):
        app.logger.warning(f"Access denied for user: {get_user_name(user_info)}")
        return "Access denied: your account is not authorized to use this application.", 403

    session['user'] = dict(user_info)
    session['token'] = token

    app.logger.info(f"User authenticated: {get_user_name(user_info)}")

    return redirect(url_for('greeting'))


@app.route('/logout')
def logout():
    """Clear session and log out user."""
    session.clear()
    return redirect(url_for('login'))


if __name__ == '__main__':
    # Run with debug mode for local development
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
