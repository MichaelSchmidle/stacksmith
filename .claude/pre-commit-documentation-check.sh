#!/bin/bash

# Pre-commit hook for Claude Code to ensure documentation maintenance and session reflection
# This script runs before git commit commands to validate documentation changes

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${YELLOW}[PRE-COMMIT HOOK] Starting documentation validation and session reflection...${NC}"

# Check if we're in a git repository
if ! git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    echo -e "${RED}[ERROR] Not in a git repository${NC}"
    exit 1
fi

# Get the diff of staged changes
STAGED_CHANGES=$(git diff --cached --name-only)
STAGED_DIFF=$(git diff --cached)

# Function to check if documentation files are properly updated
check_documentation_consistency() {
    echo -e "${YELLOW}[CHECK] Validating documentation consistency...${NC}"
    
    # Check if any service files were modified
    local service_files_modified=false
    local doc_files_modified=false
    
    for file in $STAGED_CHANGES; do
        if [[ "$file" =~ ^[^/]+/docker-compose\.yml$ ]] || [[ "$file" =~ ^[^/]+/.*\.env\.example$ ]]; then
            service_files_modified=true
        fi
        if [[ "$file" =~ README\.md$ ]] || [[ "$file" == "CLAUDE.md" ]]; then
            doc_files_modified=true
        fi
    done
    
    # If service files were modified but no documentation, warn
    if [[ "$service_files_modified" == true ]] && [[ "$doc_files_modified" == false ]]; then
        echo -e "${YELLOW}[WARNING] Service configuration files were modified but no documentation files updated.${NC}"
        echo -e "${YELLOW}Consider updating relevant README.md files or CLAUDE.md if needed.${NC}"
    fi
    
    # Check for common documentation issues
    if echo "$STAGED_DIFF" | grep -q "\.env\.example"; then
        if ! echo "$STAGED_DIFF" | grep -q "README\.md"; then
            echo -e "${YELLOW}[WARNING] .env.example file modified but README.md might need updating too.${NC}"
        fi
    fi
    
    echo -e "${GREEN}[✓] Documentation consistency check completed${NC}"
}

# Function to validate environment file patterns
validate_env_patterns() {
    echo -e "${YELLOW}[CHECK] Validating environment file patterns...${NC}"
    
    # Check for timezone consistency
    if echo "$STAGED_DIFF" | grep -q "TZ="; then
        if echo "$STAGED_DIFF" | grep -q "TZ=" | grep -v "Europe/Zurich"; then
            echo -e "${YELLOW}[WARNING] Non-standard timezone detected. Consider using Europe/Zurich as default.${NC}"
        fi
    fi
    
    # Check for hostname patterns
    if echo "$STAGED_DIFF" | grep -q "HOSTNAME="; then
        if echo "$STAGED_DIFF" | grep -q "HOSTNAME=.*localhost"; then
            echo -e "${YELLOW}[WARNING] localhost hostnames detected. Ensure these are appropriate for the context.${NC}"
        fi
    fi
    
    echo -e "${GREEN}[✓] Environment file validation completed${NC}"
}

# Function to reflect on session quality and suggest CLAUDE.md improvements
session_reflection() {
    echo -e "${YELLOW}[REFLECTION] Analyzing session quality and CLAUDE.md improvements...${NC}"
    
    # Check if this is a comprehensive change (multiple files)
    local file_count=$(echo "$STAGED_CHANGES" | wc -l)
    
    if [[ $file_count -gt 5 ]]; then
        echo -e "${GREEN}[OBSERVATION] Large changeset detected ($file_count files). Session appears comprehensive.${NC}"
    fi
    
    # Look for patterns that suggest documentation improvements
    if echo "$STAGED_DIFF" | grep -q "README\.md"; then
        echo -e "${GREEN}[OBSERVATION] README.md files updated, indicating good documentation maintenance.${NC}"
    fi
    
    # Check for CLAUDE.md updates
    if echo "$STAGED_CHANGES" | grep -q "CLAUDE\.md"; then
        echo -e "${GREEN}[OBSERVATION] CLAUDE.md updated, showing active documentation improvement.${NC}"
    else
        echo -e "${YELLOW}[REFLECTION] Consider if CLAUDE.md needs updates based on this session:${NC}"
        echo -e "${YELLOW}  - New patterns or workflows discovered?${NC}"
        echo -e "${YELLOW}  - Common issues or troubleshooting steps?${NC}"
        echo -e "${YELLOW}  - Updated deployment or configuration procedures?${NC}"
    fi
    
    # Session collaboration quality reflection
    echo -e "${YELLOW}[REFLECTION] Session collaboration quality:${NC}"
    
    # Check for comprehensive commit messages
    local commit_msg_preview=$(git log --oneline -1 2>/dev/null || echo "")
    if [[ ${#commit_msg_preview} -gt 50 ]]; then
        echo -e "${GREEN}[✓] Commit message appears comprehensive${NC}"
    else
        echo -e "${YELLOW}[SUGGESTION] Consider more detailed commit messages for better traceability${NC}"
    fi
    
    # Check for structured changes
    if echo "$STAGED_CHANGES" | grep -q "docker-compose\.yml" && echo "$STAGED_CHANGES" | grep -q "README\.md"; then
        echo -e "${GREEN}[✓] Good practice: Configuration and documentation updated together${NC}"
    fi
    
    echo -e "${YELLOW}[REFLECTION] Potential CLAUDE.md improvements:${NC}"
    echo -e "${YELLOW}  - Document any new deployment patterns used${NC}"
    echo -e "${YELLOW}  - Add troubleshooting steps for issues encountered${NC}"
    echo -e "${YELLOW}  - Update environment variable standards if changed${NC}"
    echo -e "${YELLOW}  - Include new service integration patterns${NC}"
    
    # Check for testing-related changes
    if echo "$STAGED_DIFF" | grep -q "dev\.example\.com\|127\.0\.0\.1\|local.*test"; then
        echo -e "${GREEN}[✓] Local testing workflow appears to be in use${NC}"
    fi
    
    echo -e "${GREEN}[✓] Session reflection completed${NC}"
}

# Function to validate Docker Compose syntax
validate_docker_compose() {
    echo -e "${YELLOW}[CHECK] Validating Docker Compose files...${NC}"
    
    for file in $STAGED_CHANGES; do
        if [[ "$file" =~ docker-compose\.yml$ ]]; then
            if [[ -f "$file" ]]; then
                # Basic syntax check
                if ! docker-compose -f "$file" config >/dev/null 2>&1; then
                    echo -e "${RED}[ERROR] Docker Compose syntax error in $file${NC}"
                    exit 1
                fi
                
                # Check for deprecated version field
                if grep -q "^version:" "$file"; then
                    echo -e "${YELLOW}[WARNING] Deprecated 'version' field found in $file${NC}"
                fi
            fi
        fi
    done
    
    echo -e "${GREEN}[✓] Docker Compose validation completed${NC}"
}

# Run all checks
check_documentation_consistency
validate_env_patterns
validate_docker_compose
session_reflection

echo -e "${GREEN}[SUCCESS] Pre-commit hook validation completed successfully!${NC}"
echo -e "${GREEN}Proceeding with commit...${NC}"

exit 0