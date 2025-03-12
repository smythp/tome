#!/usr/bin/env bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Get the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "$SCRIPT_DIR"

# Ensure dependencies are installed
echo -e "${BLUE}Ensuring test dependencies...${NC}"
uv pip install pytest pynput pyperclip

# Run tests using UV
echo -e "${BLUE}Running tests...${NC}"
uv run -m pytest