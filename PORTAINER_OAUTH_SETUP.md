# Portainer OAuth Setup with JumpCloud

Portainer OAuth configuration must be done through the web UI after deployment. Environment variables are not supported for OAuth configuration.

## JumpCloud Application Setup

### 1. Create OIDC Application in JumpCloud
1. Login to JumpCloud Admin Portal
2. Navigate to **USER AUTHENTICATION** → **SSO Applications**
3. Click **Add New Application**
4. Select **Custom Application** → **Configure SSO with OIDC**

### 2. Configure Application Settings
- **Application Name**: `Portainer`
- **Redirect URI**: `https://mgmt.example.com` (your `PORTAINER_HOSTNAME`)
- **Client Authentication**: `Client Secret Post` or `Client Secret Basic`
- **Grant Types**: `Authorization Code`
- **Scopes**: `openid`, `profile`, `email`

### 3. Note Down Credentials
Save the following for Portainer configuration:
- **Client ID**: (shown in JumpCloud app settings)
- **Client Secret**: (shown in JumpCloud app settings)

## Portainer OAuth Configuration

### 1. Access Portainer Web UI
1. Deploy your stack: `docker compose -f docker-compose.yml -f traefik/docker-compose.yml -f jumpcloud/docker-compose.yml up -d`
2. Access Portainer at `https://mgmt.example.com`
3. Complete initial admin setup if not done already

### 2. Configure OAuth in Portainer
1. Navigate to **Settings** → **Authentication**
2. Select **OAuth** tab
3. Configure the following:

**OAuth Settings:**
- **Automatic user provisioning**: ✓ Enabled
- **Client ID**: `[Your JumpCloud Client ID]`
- **Client Secret**: `[Your JumpCloud Client Secret]`
- **Authorization URL**: `https://oauth.id.jumpcloud.com/oauth2/auth`
- **Access Token URL**: `https://oauth.id.jumpcloud.com/oauth2/token`
- **Resource URL**: `https://oauth.id.jumpcloud.com/userinfo`
- **Redirect URL**: `https://mgmt.example.com` (auto-filled, should match your hostname)
- **User Identifier**: `email` (recommended) or `sub`
- **Scopes**: `openid profile email`

### 3. Test OAuth Flow
1. Click **Save Settings**
2. Logout of Portainer
3. You should see an OAuth login button on the login page
4. Test the OAuth authentication flow

## Troubleshooting

### Common Issues
1. **Redirect URI Mismatch**: Ensure JumpCloud redirect URI exactly matches `PORTAINER_HOSTNAME`
2. **Scope Issues**: Ensure `openid profile email` scopes are configured in JumpCloud
3. **Network Issues**: Verify Portainer can reach `oauth.id.jumpcloud.com`

### Debug Logs
Debug logging is enabled in the Portainer container. Check logs:
```bash
docker compose logs -f portainer
```

### JumpCloud OIDC Endpoints
- **Well-known config**: `https://oauth.id.jumpcloud.com/.well-known/openid-configuration`
- **Authorization**: `https://oauth.id.jumpcloud.com/oauth2/auth`
- **Token**: `https://oauth.id.jumpcloud.com/oauth2/token`
- **UserInfo**: `https://oauth.id.jumpcloud.com/userinfo`

## User Provisioning

Users will be automatically provisioned in Portainer when they first login via OAuth. They will have standard user permissions by default. Admin permissions must be granted manually in Portainer after first login.