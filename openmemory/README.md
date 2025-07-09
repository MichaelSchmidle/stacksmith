# OpenMemory MCP - AI Memory Management

Privacy-first AI memory layer for MCP clients. Provides persistent memory across Claude Desktop, Cursor, Windsurf, and other MCP clients.

## Components
- **FastAPI backend** with MCP server (accessible via Traefik)
- **React frontend** for memory management (accessible via Traefik)
- **Qdrant vector database** for semantic memory
- **PostgreSQL database** for relational data

## Features
- **Privacy-first**: All data stored locally
- **MCP Integration**: Compatible with Claude Desktop, Cursor, Windsurf
- **Semantic Memory**: Vector embeddings for intelligent retrieval
- **Web Dashboard**: Intuitive memory management UI

## Prerequisites
- Traefik reverse proxy
- OpenAI API key for embeddings

## Quick Start

```bash
cp openmemory/.env.example openmemory/.env
# Edit with your hostname and OpenAI API key

docker compose -f traefik/docker-compose.yml -f openmemory/docker-compose.yml up -d
```

## Access
- **Web Interface**: https://mem.yourdomain.com (via Tailscale)
- **API Documentation**: https://mem.yourdomain.com/api/docs
- **MCP Server**: https://mem.yourdomain.com/mcp (for MCP clients)

## Configuration

**Required**:
- `OPENMEMORY_HOSTNAME`: Public hostname
- `OPENAI_API_KEY`: OpenAI API key for embeddings
- `POSTGRES_PASSWORD`: Secure database password

**Optional**:
- `USER`: User identifier for memory storage (defaults to 'stacksmith')

## MCP Client Setup

### Claude Desktop (via OpenMemory Install)
```bash
npx @openmemory/install local https://mem.yourdomain.com/mcp/claude/sse/your-user-id --client claude
```

### Manual MCP Configuration
```json
{
  "mcpServers": {
    "openmemory": {
      "command": "npx",
      "args": ["-y", "supergateway", "--sse", "https://mem.yourdomain.com/mcp/claude/sse/your-user-id"]
    }
  }
}
```

## Memory Operations

**MCP Tools**: `add_memories`, `search_memory`, `list_memories`, `delete_all_memories`

**API Endpoints**: `/v1/memories` (GET/POST/DELETE), `/v1/memories/search`, `/v1/apps`, `/v1/config`

Tailscale VPN access. Uses custom-built images from mem0ai/mem0 repository (latest stable release). Data persisted in Docker volumes. Local storage only except for OpenAI API.