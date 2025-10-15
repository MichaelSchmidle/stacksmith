# Ghost Publishing Platform

Open-source publishing platform with professional content editor, membership features, and SEO optimization. Self-hosted alternative to Medium.

## Features

- **Professional Publishing**: Modern content editor with SEO optimization
- **Membership & Subscriptions**: Built-in membership and paid subscription features
- **Dual Access Configuration**: Admin via Tailscale VPN, public blog via secondary interface
- **Email Integration**: SMTP configuration for user management and notifications
- **MySQL Database**: Reliable persistent storage

## Services

- **Ghost**: Publishing platform (`ghost:5-alpine`)
- **MySQL**: Database backend (`mysql:8.0`)

## Quick Start

### Prerequisites

Ensure the external network exists:
```bash
docker network create stacksmith
```

### Environment Configuration

1. Copy the environment template:
```bash
cp ghost/.env.example ghost/.env
```

2. Edit `ghost/.env` with your configuration:
```bash
# Hostnames
GHOST_ADMIN_HOSTNAME=blog-admin.yourdomain.com
GHOST_PUBLIC_HOSTNAME=blog.yourdomain.com

# Database passwords - use strong passwords
DATABASE_ROOT_PASSWORD=your-strong-root-password
DATABASE_PASSWORD=your-strong-ghost-db-password

# SMTP Configuration
MAIL_SERVICE=Mailgun
MAIL_HOST=smtp.mailgun.org
MAIL_PORT=465
MAIL_SECURE=true
MAIL_USER=your-mail-username
MAIL_PASSWORD=your-mail-password
MAIL_FROM=noreply@blog.yourdomain.com
```

### Deployment

Deploy the Ghost stack:
```bash
docker compose -f ghost/docker-compose.yml up -d
```

Deploy with Traefik (recommended):
```bash
docker compose -f traefik/docker-compose.yml -f ghost/docker-compose.yml up -d
```

## Initial Setup

1. **Access Ghost**: Navigate to your admin hostname (e.g., `https://blog-admin.yourdomain.com/ghost`)

2. **Create Owner Account**: Set up your administrator account on first access

3. **Complete Setup Wizard**: Configure basic site settings

4. **Start Publishing**: Create your first post

## SMTP Providers

Common SMTP configurations:

**Mailgun:**
```bash
MAIL_SERVICE=Mailgun
MAIL_HOST=smtp.mailgun.org
MAIL_PORT=465
MAIL_SECURE=true
```

**Gmail:**
```bash
MAIL_SERVICE=Gmail
MAIL_HOST=smtp.gmail.com
MAIL_PORT=465
MAIL_SECURE=true
```

**SendGrid:**
```bash
MAIL_SERVICE=SendGrid
MAIL_HOST=smtp.sendgrid.net
MAIL_PORT=465
MAIL_SECURE=true
```

## Access URLs

- **Admin Interface**: `https://blog-admin.yourdomain.com/ghost` (Tailscale VPN required)
- **Public Blog**: `https://blog.yourdomain.com` (publicly accessible)

Admin interface protected by Tailscale VPN. Public blog accessible via secondary network. HTTPS via Traefik. Data persisted in Docker volumes. SMTP required for email functionality.
