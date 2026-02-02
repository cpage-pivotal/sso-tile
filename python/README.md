# SSO Tile - Python Flask Application

A Flask application demonstrating OAuth2 authentication with Tanzu Single Sign-On (SSO) on Cloud Foundry.

## Prerequisites

- Cloud Foundry CLI (`cf`) installed and configured
- Access to a Cloud Foundry environment with the Tanzu SSO tile (p-identity) installed
- An SSO service instance named `sso` created in your space

### Creating the SSO Service Instance

If you don't have an SSO service instance, create one:

```bash
cf create-service p-identity <plan-name> sso
```

Replace `<plan-name>` with an available plan (e.g., `auth-domain`). List available plans with:

```bash
cf marketplace -e p-identity
```

## Deploying to Cloud Foundry

1. Navigate to the python directory:

   ```bash
   cd python
   ```

2. Push the application:

   ```bash
   cf push
   ```

3. Access the application at the URL shown in the output (e.g., `https://sso-tile-python.apps.<your-domain>.com`)

## Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `FLASK_SECRET_KEY` | Secret key for Flask session encryption | Auto-generated |

### Local Development

For local development, set these environment variables:

```bash
export SSO_CLIENT_ID=<your-client-id>
export SSO_CLIENT_SECRET=<your-client-secret>
export SSO_AUTH_DOMAIN=<your-auth-domain>
export FLASK_SECRET_KEY=<your-secret-key>
```

Then run:

```bash
pip install -r requirements.txt
python app.py
```

The app will be available at `http://localhost:8080`.

## Project Structure

```
python/
├── app.py              # Main Flask application with OAuth2 integration
├── requirements.txt    # Python dependencies
├── manifest.yml        # Cloud Foundry deployment manifest
├── Procfile            # Process declaration (gunicorn)
├── runtime.txt         # Python version specification
└── templates/
    └── greeting.html   # Jinja2 template for the greeting page
```

## How It Works

1. When deployed to Cloud Foundry, the app reads SSO credentials from `VCAP_SERVICES` (automatically populated when bound to the `sso` service)

2. All routes require authentication via the `@login_required` decorator

3. Unauthenticated users are redirected to `/login`, which initiates the OAuth2 authorization code flow

4. After successful authentication, the user is redirected back to the app with their identity information stored in the session

5. The greeting page displays the authenticated user's name, trying multiple claim names (`name`, `user_name`, `username`, `preferred_username`, `email`, `sub`) to handle different identity providers

## Troubleshooting

### SSL Certificate Errors

If you encounter SSL certificate verification errors when the app tries to communicate with the SSO service, you can set `SSO_SKIP_SSL_VALIDATION=true` in the manifest or via:

```bash
cf set-env sso-tile-python SSO_SKIP_SSL_VALIDATION true
cf restage sso-tile-python
```

### Viewing Logs

```bash
cf logs sso-tile-python --recent
```

### Checking Service Binding

Verify the app is bound to the SSO service:

```bash
cf services
cf env sso-tile-python
```

The `VCAP_SERVICES` section should contain `p-identity` credentials.
