# OpenMemory MCP - AI Memory Management

Privacy-first AI memory layer for MCP clients. Provides persistent memory across Claude Desktop, Cursor, Windsurf, and other MCP clients.

## Components
- **FastAPI backend** (port 8765) with MCP server
- **React frontend** (port 3000) for memory management
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
- **MCP Server**: http://localhost:8765 (for MCP clients)

## Configuration

**Required**:
- `OPENMEMORY_HOSTNAME`: Public hostname
- `OPENAI_API_KEY`: OpenAI API key for embeddings
- `POSTGRES_PASSWORD`: Secure database password

## MCP Client Setup

### Claude Desktop
```json
{
  "mcpServers": {
    "openmemory": {
      "command": "npx",
      "args": ["@openmemory/mcp-client"],
      "env": {
        "OPENMEMORY_API_URL": "http://localhost:8765"
      }
    }
  }
}
```

### Other MCP Clients
Connect to: `http://localhost:8765`

## Memory Operations

**MCP Tools**: `add_memories`, `search_memory`, `list_memories`, `delete_all_memories`

**API Endpoints**: `/health`, `/api/memories` (GET/POST/DELETE), `/api/memories/search`

Tailscale VPN access. Uses custom-built images from mem0ai/mem0 repository. Data persisted in Docker volumes. Local storage only except for OpenAI API.