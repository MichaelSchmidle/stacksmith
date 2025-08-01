# OpenMemory MCP Stack

OpenMemory MCP is a memory management service that provides persistent context and memory capabilities for AI applications. This stack combines Qdrant vector database for storage with the OpenMemory MCP server for intelligent memory operations.

## Features

- **Persistent Memory**: Long-term context storage and retrieval for AI applications
- **Vector Database**: Qdrant for efficient similarity search and storage
- **MCP Protocol**: Model Context Protocol for standardized AI memory interactions
- **OpenAI Integration**: Compatible with OpenAI API for memory-enhanced conversations
- **Scalable Storage**: Designed for growing memory and context requirements

## Services

- **OpenMemory MCP**: Memory management server (`mem0/openmemory-mcp:latest`)
- **Qdrant**: Vector database for memory storage (`qdrant/qdrant:latest`)

## Quick Start

### Prerequisites

Ensure the external network exists:
```bash
docker network create stacksmith
```

### Environment Configuration

1. Copy the environment template:
```bash
cp openmemory/.env.example openmemory/.env
```

2. Edit `openmemory/.env` with your configuration:
```bash
# OpenMemory Configuration
OPENMEMORY_HOSTNAME=mem.yourdomain.com

# User Configuration - Set your username
OPENMEMORY_USER=yourusername

# OpenAI Configuration - Required for memory operations
OPENAI_API_KEY=sk-your-openai-api-key-here

# System Configuration
PUID=1000
PGID=1000
TZ=Europe/Zurich
```

### Deployment

Deploy the OpenMemory stack:
```bash
docker compose -f openmemory/docker-compose.yml up -d
```

Deploy with Traefik (recommended):
```bash
docker compose -f traefik/docker-compose.yml -f openmemory/docker-compose.yml up -d
```

## Usage

1. **Access Service**: Navigate to your configured hostname (e.g., `https://mem.yourdomain.com`)

2. **MCP Integration**: Configure your AI client to use the OpenMemory MCP server:
   - Server endpoint: `https://mem.yourdomain.com`
   - Protocol: Model Context Protocol (MCP)

3. **Memory Operations**: The service provides:
   - Context storage and retrieval
   - Semantic memory search
   - Conversation history persistence
   - Cross-session memory continuity

## Configuration

### OpenAI API Key
The service requires a valid OpenAI API key for memory processing and embeddings. Obtain your key from the OpenAI dashboard and set it in the environment configuration.

### User Configuration
Set the `OPENMEMORY_USER` variable to your desired username for memory isolation and organization.

### Qdrant Database
The Qdrant vector database runs on port 6333 internally and stores memory data in the `openmemory-storage` volume for persistence.

## Security Notes

- OpenAI API key required for operation
- Memory data stored locally in Docker volumes
- Access via Tailscale VPN when using Traefik integration
- HTTPS enforcement via Traefik with Let's Encrypt certificates

## Troubleshooting

### Service Not Starting
- Verify OpenAI API key is valid and set correctly
- Check that the stacksmith network exists
- Ensure no port conflicts on 8765 (Qdrant runs internally only)

### Memory Not Persisting
- Verify the openmemory-storage volume is properly mounted
- Check Qdrant logs for database connection issues
- Ensure proper PUID/PGID permissions for volume access

### API Connection Issues
- Verify network connectivity between services
- Check that QDRANT_HOST points to the correct service name
- Ensure internal network communication is working