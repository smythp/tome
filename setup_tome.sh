#!/usr/bin/env bash
set -e

# Colors for output
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo -e "${BLUE}=========================================${NC}"
echo -e "${BLUE}    Tome of Lore Setup with UV    ${NC}"
echo -e "${BLUE}=========================================${NC}"

# Function to check if a command exists
command_exists() {
  command -v "$1" >/dev/null 2>&1
}

# Function to install UV if needed
install_uv() {
  echo -e "${YELLOW}Installing UV...${NC}"
  curl -sSf https://install.determinate.systems/uv | sh -s -- --no-modify-path

  # Add uv to the current PATH for this session
  export PATH="$HOME/.cargo/bin:$PATH"
  
  echo -e "${GREEN}UV installed successfully!${NC}"
}

# Check if UV is installed or install it
echo -e "\n${BLUE}Checking for UV...${NC}"
if ! command_exists uv; then
  echo -e "${YELLOW}UV not found.${NC}"
  read -p "Would you like to install UV now? (y/n) " -n 1 -r
  echo
  if [[ $REPLY =~ ^[Yy]$ ]]; then
    install_uv
  else
    echo -e "${RED}UV is required to continue. Exiting.${NC}"
    exit 1
  fi
else
  echo -e "${GREEN}UV is already installed.${NC}"
  UV_VERSION=$(uv --version)
  echo -e "Version: ${YELLOW}$UV_VERSION${NC}"
fi

# Get absolute path to the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DB_PATH="${SCRIPT_DIR}/lore.db"

# Check if the database exists or initialize it
echo -e "\n${BLUE}Checking database...${NC}"
if [ ! -f "$DB_PATH" ]; then
  echo -e "${YELLOW}Database not found. Initializing...${NC}"
  
  # Check if sqlite3 is installed
  if ! command_exists sqlite3; then
    echo -e "${RED}sqlite3 command not found. Please install SQLite.${NC}"
    exit 1
  fi
  
  sqlite3 "$DB_PATH" < "${SCRIPT_DIR}/CREATE.sql"
  echo -e "${GREEN}Database initialized successfully at:${NC}"
  echo -e "${YELLOW}$DB_PATH${NC}"
else
  echo -e "${GREEN}Database already exists at:${NC}"
  echo -e "${YELLOW}$DB_PATH${NC}"
fi

# Install pytest for testing
echo -e "\n${BLUE}Installing pytest for testing...${NC}"
if ! uv pip freeze | grep -q pytest; then
  uv pip install pytest
  echo -e "${GREEN}pytest installed successfully${NC}"
else
  echo -e "${GREEN}pytest already installed${NC}"
fi

# Create runner scripts
cat > "$RUNNER_PATH" << EOF
#!/usr/bin/env bash
set -e

# Get the script directory
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "\$SCRIPT_DIR"

# Run the application using UV
uv run tome.py
EOF

# Create test runner script
TEST_RUNNER_PATH="${SCRIPT_DIR}/run_tests.sh"
cat > "$TEST_RUNNER_PATH" << EOF
#!/usr/bin/env bash
set -e

# Get the script directory
SCRIPT_DIR="\$( cd "\$( dirname "\${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
cd "\$SCRIPT_DIR"

# Run tests using UV
uv run -m pytest
EOF

chmod +x "$TEST_RUNNER_PATH"
echo -e "${GREEN}Test runner script created at:${NC}"
echo -e "${YELLOW}$TEST_RUNNER_PATH${NC}"

chmod +x "$RUNNER_PATH"
echo -e "${GREEN}Runner script created at:${NC}"
echo -e "${YELLOW}$RUNNER_PATH${NC}"

echo -e "\n${GREEN}Setup complete!${NC}"
echo -e "To run Tome of Lore, use: ${YELLOW}./run_tome.sh${NC}"
