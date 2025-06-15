# JumpCloud Authentication Service

External authentication service using JumpCloud OIDC provider with traefik-forward-auth. Provides centralized authentication for all services through Traefik middleware.

## Service Overview

- **Image**: `thomseddon/traefik-forward-auth:latest`
- **Purpose**: External OAuth/OIDC authentication for Traefik services
- **Port**: 4181 (internal authentication endpoint)
- **Network**: Requires `traefik` network

## Dependencies

**Required Services**:
- **Traefik**: Provides reverse proxy and network connectivity
- **JumpCloud Account**: External OIDC provider configuration

**Integrated Services**:
- Any service using `jumpcloud-auth@docker` middleware

## Prerequisites

### JumpCloud OIDC Application Setup

1. **Login to JumpCloud Admin Portal**
2. **Navigate to USER AUTHENTICATION → SSO Applications**
3. **Create new application**:
   - Click **Add New Application**
   - Select **Custom Application**
   - Choose **Configure SSO with OIDC**

4. **Configure application settings**:
   - **Application Name**: `Stacksmith Auth`
   - **Redirect URI**: `https://auth.example.com` (your auth hostname)
   - **Client Authentication**: `Client Secret Post`
   - **Grant Types**: `Authorization Code`
   - **Scopes**: `openid`, `profile`, `email`

5. **Note credentials**:
   - **Client ID**: Save for configuration
   - **Client Secret**: Save for configuration

## Configuration

### Environment Variables

Copy and configure the environment file:
```bash
cp .env.example .env
```

**Required Variables**:
- `JUMPCLOUD_CLIENT_ID`: Client ID from JumpCloud application
- `JUMPCLOUD_CLIENT_SECRET`: Client secret from JumpCloud application
- `JUMPCLOUD_AUTH_HOSTNAME`: Auth service hostname (e.g., `auth.example.com`)
- `COOKIE_DOMAIN`: Domain for auth cookies (e.g., `example.com`)
- `AUTH_SECRET`: Random 32+ character string for cookie encryption

**Optional Variables**:
- `CLOUDFLARE_EMAIL`: Email for Let's Encrypt (if using Traefik)
- `CLOUDFLARE_API_TOKEN`: API token for DNS challenge (if using Traefik)
- `TRAEFIK_INTERFACE`: Network interface binding (default: `0.0.0.0`)

### Generate AUTH_SECRET

```bash
# Generate random secret
openssl rand -base64 32
```

## Deployment

### Prerequisites Check
```bash
# Ensure Traefik network exists
docker network ls | grep traefik
```

### Standalone Deployment
```bash
# Configure environment
cp .env.example .env
# Edit .env with JumpCloud credentials

# Deploy with Traefik
docker compose -f ../traefik/docker-compose.yml -f docker-compose.yml up -d
```

### With Full Stack
```bash
# Deploy complete authenticated stack
docker compose -f ../traefik/docker-compose.yml -f docker-compose.yml -f ../docker-compose.yml up -d
```

## Service Integration

### Protecting Services with JumpCloud Auth

Add middleware to any service's docker-compose.yml:

```yaml
labels:
  - "traefik.http.routers.service-name.middlewares=jumpcloud-auth@docker"
```

### Middleware Configuration

The JumpCloud service automatically creates the `jumpcloud-auth@docker` middleware with:
- **Forward Auth Address**: `http://jumpcloud-auth:4181`
- **Trust Forward Header**: `true`
- **Auth Response Headers**: `X-Forwarded-User`, `X-Forwarded-Email`, `X-Forwarded-Groups`

### Currently Protected Services

Services using JumpCloud authentication:
- **Traefik Dashboard**: `https://proxy.example.com`
- **Pi-hole Web Interface**: `https://dns.example.com`

## Authentication Flow

1. **User accesses protected service**
2. **Traefik forwards auth request** to JumpCloud service
3. **JumpCloud service checks authentication**:
   - If authenticated: Allow access
   - If not authenticated: Redirect to JumpCloud login
4. **User authenticates** with JumpCloud
5. **JumpCloud redirects back** with auth token
6. **JumpCloud service validates token** and sets auth cookies
7. **User gains access** to protected service

## Accessing Services

### JumpCloud Auth Service
- **URL**: `https://auth.example.com` (or your configured hostname)
- **Purpose**: OAuth callback endpoint and auth status
- **Direct access**: Not typically needed by users

### Testing Authentication
1. **Access protected service** (e.g., Traefik dashboard)
2. **Should redirect** to JumpCloud login
3. **After login**, should redirect back to original service
4. **Subsequent access** should be automatic (cookie-based)

## Troubleshooting

### Common Issues

**Authentication Redirect Loop**:
```bash
# Check JumpCloud service logs
docker compose logs -f jumpcloud-auth

# Verify redirect URI matches JumpCloud app configuration
echo "Configured: https://${JUMPCLOUD_AUTH_HOSTNAME}"
```

**OAuth Configuration Issues**:
- **Verify Client ID/Secret**: Check JumpCloud app credentials
- **Check Redirect URI**: Must exactly match JumpCloud app configuration
- **Validate Cookie Domain**: Should match your domain structure

**Network Connectivity**:
```bash
# Test JumpCloud service accessibility
docker compose exec traefik nslookup jumpcloud-auth

# Check network membership
docker network inspect traefik | grep jumpcloud
```

### Debug Mode

Enable debug logging by modifying docker-compose.yml:
```yaml
environment:
  - LOG_LEVEL=debug
```

### Validation Commands

```bash
# Test JumpCloud OIDC endpoints
curl https://oauth.id.jumpcloud.com/.well-known/openid-configuration

# Check auth service health
curl http://[container-ip]:4181/health

# Verify cookie domain
docker compose exec jumpcloud-auth env | grep COOKIE_DOMAIN
```

## Security Considerations

- **Client Secret**: Store securely, never commit to version control
- **AUTH_SECRET**: Use strong random string, rotate periodically
- **Cookie Domain**: Set appropriately for security scope
- **HTTPS Only**: All authentication flows require HTTPS
- **Session Management**: JumpCloud handles session lifecycle

## JumpCloud OIDC Endpoints

- **Issuer**: `https://oauth.id.jumpcloud.com/oauth2`
- **Authorization**: `https://oauth.id.jumpcloud.com/oauth2/auth`
- **Token**: `https://oauth.id.jumpcloud.com/oauth2/token`
- **UserInfo**: `https://oauth.id.jumpcloud.com/userinfo`
- **Well-known**: `https://oauth.id.jumpcloud.com/.well-known/openid-configuration`

## Monitoring

```bash
# Monitor authentication attempts
docker compose logs -f jumpcloud-auth

# Check service health
docker compose ps jumpcloud-auth

# View auth service configuration
docker compose exec jumpcloud-auth env | grep -E "(CLIENT|OIDC|AUTH)"
```

This service provides enterprise-grade authentication for the entire stacksmith architecture using your existing JumpCloud identity infrastructure.