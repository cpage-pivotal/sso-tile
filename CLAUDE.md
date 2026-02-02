# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains two implementations of the same OAuth2 SSO demo application:

1. **Spring Boot (Java)** - A Spring Boot 4.0.2 application using Java 21
2. **Flask (Python)** - A Flask application using Python 3.12

Both applications demonstrate OAuth2 integration with Tanzu Single Sign-On (SSO) on Cloud Foundry, providing identical functionality with their respective technology stacks.

---

# Spring Boot Application (Java)

This is a Spring Boot 4.0.2 application that demonstrates OAuth2 integration with Tanzu Single Sign-On (SSO) on Cloud Foundry. It uses Java 21 and follows Package-by-Feature organization.

## Build and Run Commands

### Build
```bash
./mvnw clean package
```

### Run locally
```bash
./mvnw spring-boot:run
```

### Test
```bash
./mvnw test
```

### Deploy to Cloud Foundry
```bash
./mvnw clean package
cf push
```

The app expects a bound `sso` service instance (p-identity) on Cloud Foundry as defined in `manifest.yml`.

## Architecture

### Package Structure

The codebase uses **Package-by-Feature** organization:
- `org.tanzu.ssotile.greeting` - Greeting functionality with OAuth2 user display
- `org.tanzu.ssotile.security` - Security configuration and OAuth2 client setup

### OAuth2 Client Configuration

The application has two modes of OAuth2 configuration:

1. **Cloud Foundry** (src/main/java/org/tanzu/ssotile/security/SsoClientConfiguration.java:22):
   - Active when `@ConditionalOnCloudPlatform(CloudPlatform.CLOUD_FOUNDRY)` is met
   - Parses `VCAP_SERVICES` environment variable to extract SSO credentials from bound `p-identity` service
   - Programmatically creates `ClientRegistrationRepository` with credentials from `auth_domain`, `client_id`, `client_secret`
   - Uses UAA-style endpoints: `/oauth/authorize`, `/oauth/token`, `/userinfo`, `/token_keys`

2. **Local Development** (src/main/resources/application.properties:7-13):
   - Properties commented out by default
   - Can be configured with local identity provider credentials
   - Use environment variables for `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_ISSUER_URI`

### Security Configuration

All endpoints require authentication (src/main/java/org/tanzu/ssotile/security/SecurityConfig.java:26) with OAuth2 login enabled. The `GreetingController` extracts user information from `OAuth2User` attributes, attempting multiple claim names to handle different identity providers (`name`, `user_name`, `username`, `preferred_username`, `email`, `sub`).

### View Layer

Uses Thymeleaf templates (src/main/resources/templates/greeting.html) with inline CSS styling. The template displays authenticated user information.

## Dependencies

Key dependencies in `pom.xml`:
- `spring-boot-starter-webmvc` - Web MVC support
- `spring-boot-starter-oauth2-client` - OAuth2 client functionality
- `spring-boot-starter-thymeleaf` - Template engine
- `jackson-databind` - JSON parsing for VCAP_SERVICES

## Cloud Foundry Configuration

`manifest.yml` specifies:
- Memory: 1G
- Java buildpack (offline) with JRE 21
- Service binding: `sso` (p-identity service instance must exist)
- Artifact: `target/sso-tile-0.0.1-SNAPSHOT.jar`

---

# Flask Application (Python)

The `python/` folder contains a Flask application that provides identical functionality to the Spring Boot application.

## Build and Run Commands

### Install dependencies
```bash
cd python
pip install -r requirements.txt
```

### Run locally
```bash
cd python
python app.py
```

### Deploy to Cloud Foundry
```bash
cd python
cf push
```

The app expects a bound `sso` service instance (p-identity) on Cloud Foundry as defined in `python/manifest.yml`.

## Architecture

### Project Structure

```
python/
├── app.py              # Main Flask application with OAuth2 integration
├── requirements.txt    # Python dependencies
├── manifest.yml        # Cloud Foundry manifest
├── Procfile            # Process declaration for CF (gunicorn)
├── runtime.txt         # Python version specification
└── templates/
    └── greeting.html   # Jinja2 template for greeting page
```

### OAuth2 Client Configuration

The application has two modes of OAuth2 configuration:

1. **Cloud Foundry** (python/app.py - `get_sso_config` function):
   - Parses `VCAP_SERVICES` environment variable to extract SSO credentials from bound `p-identity` service
   - Extracts `auth_domain`, `client_id`, `client_secret` from credentials
   - Uses UAA-style endpoints: `/oauth/authorize`, `/oauth/token`, `/userinfo`, `/token_keys`

2. **Local Development**:
   - Set environment variables: `SSO_CLIENT_ID`, `SSO_CLIENT_SECRET`, `SSO_AUTH_DOMAIN`
   - Optionally set `FLASK_SECRET_KEY` for session encryption

### Security Configuration

All routes except `/login` require authentication via the `@login_required` decorator. The `get_user_name` function extracts user information from OAuth2 userinfo, attempting multiple claim names to handle different identity providers (`name`, `user_name`, `username`, `preferred_username`, `email`, `sub`).

### View Layer

Uses Jinja2 templates (python/templates/greeting.html) with inline CSS styling identical to the Spring Boot version. The template displays authenticated user information.

## Dependencies

Key dependencies in `requirements.txt`:
- `Flask` - Web framework
- `Authlib` - OAuth2 client functionality
- `requests` - HTTP client (Authlib dependency)
- `gunicorn` - Production WSGI server

## Cloud Foundry Configuration

`python/manifest.yml` specifies:
- Memory: 256M
- Python buildpack
- Service binding: `sso` (p-identity service instance must exist)