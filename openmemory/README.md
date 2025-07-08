# OpenMemory MCP - AI Memory Management

OpenMemory MCP is a privacy-first, local memory layer for AI applications that provides persistent memory across MCP (Model Context Protocol) clients. This implementation integrates seamlessly with Stacksmith's infrastructure.

## Overview

OpenMemory MCP consists of:
- **FastAPI backend** (port 8765) with MCP server functionality
- **React frontend** (port 3000) for memory management and visualization
- **Qdrant vector database** for semantic memory storage
- **PostgreSQL database** for relational data storage

## Features

- **Privacy-First**: All data stored locally in your infrastructure
- **MCP Integration**: Compatible with Claude Desktop, Cursor, Windsurf, and other MCP clients
- **Semantic Memory**: Uses vector embeddings for intelligent memory retrieval
- **Memory Operations**: Add, retrieve, list, and delete memory objects
- **Web Dashboard**: Intuitive UI for memory management
- **Secure Access**: Integrated with Stacksmith's Traefik and Tailscale

## Prerequisites

- Docker and Docker Compose
- Stacksmith infrastructure (Traefik, external network)
- OpenAI API key for embeddings and LLM functionality

## Quick Start

1. **Network Setup** (if not already created):
   ```bash
   docker network create stacksmith
   ```

2. **Environment Configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your specific values
   ```

3. **Deploy OpenMemory**:
   ```bash
   # Deploy with Traefik (uses pre-built images)
   docker compose -f ../traefik/docker-compose.yml -f docker-compose.yml up -d
   
   # Or deploy standalone (without external access)
   docker compose up -d
   ```
   
   **Note**: This deployment uses pre-built Docker images for faster startup.

4. **Access the Service**:
   - **Web Interface**: https://mem.yourdomain.com (via Tailscale)
   - **API Documentation**: https://mem.yourdomain.com/docs (via Tailscale)
   - **MCP Server**: http://localhost:8765 (for MCP client configuration)

## Configuration

### Required Environment Variables

#### Hostname Configuration
```bash
# Public hostname for OpenMemory UI
OPENMEMORY_HOSTNAME=mem.example.com
```

#### AI Provider Configuration
```bash
# OpenAI API key (required for embeddings and LLM functionality)
OPENAI_API_KEY=your-openai-api-key-here
```

#### Database Configuration
```bash
# PostgreSQL database settings
POSTGRES_DB=openmemory
POSTGRES_USER=openmemory
POSTGRES_PASSWORD=secure-random-password-here
```

### Optional Environment Variables

#### User Configuration
```bash
# User ID and Group ID for file permissions
PUID=1000
PGID=1000
```

#### Timezone
```bash
# Timezone for container logs and scheduling
TZ=America/New_York
```

## MCP Client Configuration

### Claude Desktop
Add to your Claude Desktop configuration:
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
Configure your MCP client to connect to:
- **Server URL**: `http://localhost:8765`
- **Protocol**: HTTP
- **Port**: 8765

## Memory Operations

### Available MCP Tools
- `add_memories`: Store new memories with context
- `search_memory`: Retrieve memories based on semantic similarity
- `list_memories`: List all stored memories
- `delete_all_memories`: Clear all memories (use with caution)

### API Endpoints
- `GET /health`: Health check
- `POST /api/memories`: Add new memory
- `GET /api/memories`: List memories
- `POST /api/memories/search`: Search memories
- `DELETE /api/memories`: Delete all memories

## Service Architecture

### Container Structure
```
stacksmith_openmemory_api       # OpenMemory MCP server (port 8765)
├── stacksmith_openmemory_qdrant # Qdrant vector database (port 6333)
└── stacksmith_openmemory_postgres # PostgreSQL database (port 5432)
```

### Network Configuration
- **External Network**: `stacksmith` (shared with Traefik)
- **Service Discovery**: Automatic via Docker DNS
- **Health Checks**: All services include health monitoring

### Data Persistence
- **Qdrant Data**: `openmemory-qdrant-data` named volume
- **PostgreSQL Data**: `openmemory-postgres-data` named volume
- **Backup**: Use standard Docker volume backup procedures

## Security Considerations

### Access Control
- **Primary Access**: Tailscale VPN (websecure-tailscale entrypoint)
- **Local API**: Available on localhost:8765 for MCP clients
- **Authentication**: Handled by Traefik middleware

### Data Privacy
- **Local Storage**: All data remains in your infrastructure
- **No External Dependencies**: Except for OpenAI API for embeddings
- **Encrypted Transit**: HTTPS via Traefik with Let's Encrypt

### API Key Security
- **Environment Variables**: Store API keys securely
- **No Logging**: API keys not logged in container outputs
- **Rotation**: Regularly rotate OpenAI API keys

## Maintenance

### Updates
```bash
# Pull latest images
docker compose pull

# Restart services with updated images
docker compose up -d
```

### Backup
```bash
# Backup Qdrant data
docker run --rm -v openmemory-qdrant-data:/data -v $(pwd):/backup alpine tar czf /backup/qdrant-backup.tar.gz /data

# Backup PostgreSQL data
docker run --rm -v openmemory-postgres-data:/data -v $(pwd):/backup alpine tar czf /backup/postgres-backup.tar.gz /data
```

### Restore
```bash
# Restore Qdrant data
docker run --rm -v openmemory-qdrant-data:/data -v $(pwd):/backup alpine tar xzf /backup/qdrant-backup.tar.gz -C /

# Restore PostgreSQL data
docker run --rm -v openmemory-postgres-data:/data -v $(pwd):/backup alpine tar xzf /backup/postgres-backup.tar.gz -C /
```

### Logs
```bash
# View all service logs
docker compose logs -f

# View specific service logs
docker compose logs -f openmemory-api
docker compose logs -f openmemory-ui
```

## Troubleshooting

### Common Issues

#### OpenAI API Key Issues
- **Symptom**: API errors or embedding failures
- **Solution**: Verify API key validity and sufficient credits

#### Database Connection Issues
- **Symptom**: API service fails to start
- **Solution**: Check PostgreSQL container health and credentials

#### Memory Retrieval Issues
- **Symptom**: Search returns no results
- **Solution**: Verify Qdrant container is running and accessible

#### MCP Client Connection Issues
- **Symptom**: MCP client cannot connect
- **Solution**: Ensure localhost:8765 is accessible from client

### Health Checks
```bash
# Check all service health
docker compose ps

# Test API health
curl http://localhost:8765/health

# Test Qdrant health
curl http://localhost:6333/health
```

### Reset Data
```bash
# Stop services
docker compose down

# Remove volumes (WARNING: This deletes all data)
docker volume rm openmemory-qdrant-data openmemory-postgres-data

# Restart services
docker compose up -d
```

## Integration with Stacksmith

### Deployment Patterns
```bash
# Deploy with core infrastructure
docker compose -f ../docker-compose.yml -f ../traefik/docker-compose.yml -f docker-compose.yml up -d

# Deploy multiple services
docker compose -f ../traefik/docker-compose.yml -f docker-compose.yml -f ../other-service/docker-compose.yml up -d
```

### Traefik Integration
- **Automatic SSL**: Let's Encrypt certificates via Traefik
- **Service Discovery**: Automatic routing based on hostname
- **Security Headers**: Applied via Traefik middleware

### Monitoring
- **Health Checks**: Integrated with Docker health monitoring
- **Logs**: Centralized logging via Docker
- **Metrics**: Available through Docker stats

## Resources

- **OpenMemory GitHub**: https://github.com/mem0ai/mem0/tree/main/openmemory
- **Mem0 Documentation**: https://docs.mem0.ai/
- **Model Context Protocol**: https://modelcontextprotocol.io/
- **Stacksmith**: https://github.com/MichaelSchmidle/stacksmith

## Support

For issues specific to:
- **OpenMemory MCP**: https://github.com/mem0ai/mem0/issues
- **Stacksmith Integration**: https://github.com/MichaelSchmidle/stacksmith/issues
- **General Questions**: Check the documentation or create an issue