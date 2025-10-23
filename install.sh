#!/usr/bin/env bash
#
# Cred Checker Installation Script
# One-command installer for the credential scanning tool
#
# Usage: curl -sSL https://your-repo/install.sh | bash
#        or: ./install.sh
#
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
INSTALL_DIR="${HOME}/.local/bin"
TOOL_DIR="${HOME}/.local/share/cred-checker"
REPO_URL="https://github.com/your-org/cred-checker.git"  # Update this

echo -e "${CYAN}"
cat << "EOF"
╔═══════════════════════════════════════╗
║   Cred Checker Installation Script   ║
║   Version 1.0.0                       ║
╚═══════════════════════════════════════╝
EOF
echo -e "${NC}"

# Helper functions
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_info() {
    echo -e "${CYAN}ℹ${NC} $1"
}

# Check if running with curl | bash
if [ -t 0 ]; then
    INTERACTIVE=true
else
    INTERACTIVE=false
fi

# Step 1: Check Python
print_info "Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed"
    echo "Please install Python 3.8 or higher:"
    echo "  Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "  CentOS/RHEL:   sudo yum install python3 python3-pip"
    echo "  macOS:         brew install python3"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.8"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $REQUIRED_VERSION or higher required (found $PYTHON_VERSION)"
    exit 1
fi

print_success "Python $PYTHON_VERSION found"

# Step 2: Check pip
print_info "Checking pip installation..."
if ! command -v pip3 &> /dev/null; then
    print_warning "pip3 not found, attempting to install..."
    python3 -m ensurepip --default-pip || {
        print_error "Failed to install pip"
        echo "Please install pip manually:"
        echo "  Ubuntu/Debian: sudo apt-get install python3-pip"
        exit 1
    }
fi

print_success "pip3 found"

# Step 3: Check nmap
print_info "Checking nmap installation..."
if ! command -v nmap &> /dev/null; then
    print_warning "nmap is not installed"
    
    # Try to install nmap
    if [ "$EUID" -eq 0 ] || [ "$INTERACTIVE" = true ]; then
        echo -e "${YELLOW}Would you like to install nmap now? [y/N]${NC}"
        read -r response
        if [[ "$response" =~ ^[Yy]$ ]]; then
            if command -v apt-get &> /dev/null; then
                sudo apt-get update && sudo apt-get install -y nmap
            elif command -v yum &> /dev/null; then
                sudo yum install -y nmap
            elif command -v brew &> /dev/null; then
                brew install nmap
            else
                print_error "Could not determine package manager"
                echo "Please install nmap manually:"
                echo "  Ubuntu/Debian: sudo apt-get install nmap"
                echo "  CentOS/RHEL:   sudo yum install nmap"
                echo "  macOS:         brew install nmap"
                exit 1
            fi
        else
            print_warning "Skipping nmap installation. Tool will have limited functionality."
        fi
    else
        print_error "nmap is required but not installed"
        echo "Please install nmap:"
        echo "  Ubuntu/Debian: sudo apt-get install nmap"
        echo "  CentOS/RHEL:   sudo yum install nmap"
        echo "  macOS:         brew install nmap"
        exit 1
    fi
fi

if command -v nmap &> /dev/null; then
    print_success "nmap found"
fi

# Step 4: Create directories
print_info "Creating installation directories..."
mkdir -p "$INSTALL_DIR"
mkdir -p "$TOOL_DIR"
mkdir -p "$TOOL_DIR/data"
mkdir -p "$TOOL_DIR/results"

print_success "Directories created"

# Step 5: Download or copy tool files
print_info "Installing cred-checker..."

if [ -f "cred_checker.py" ]; then
    # Local installation (if running from repo directory)
    print_info "Installing from local directory..."
    cp cred_checker.py "$TOOL_DIR/"
    cp -r data/* "$TOOL_DIR/data/" 2>/dev/null || true
    cp requirements.txt "$TOOL_DIR/" 2>/dev/null || true
else
    # Remote installation
    print_info "Downloading from repository..."
    
    if command -v git &> /dev/null; then
        # Clone the repo
        rm -rf /tmp/cred-checker
        git clone "$REPO_URL" /tmp/cred-checker
        cp /tmp/cred-checker/cred_checker.py "$TOOL_DIR/"
        cp -r /tmp/cred-checker/data/* "$TOOL_DIR/data/" 2>/dev/null || true
        cp /tmp/cred-checker/requirements.txt "$TOOL_DIR/" 2>/dev/null || true
        rm -rf /tmp/cred-checker
    elif command -v wget &> /dev/null; then
        # Download individual files
        wget -O "$TOOL_DIR/cred_checker.py" "https://raw.githubusercontent.com/your-org/cred-checker/main/cred_checker.py"
        wget -O "$TOOL_DIR/requirements.txt" "https://raw.githubusercontent.com/your-org/cred-checker/main/requirements.txt"
    elif command -v curl &> /dev/null; then
        # Download with curl
        curl -sSL -o "$TOOL_DIR/cred_checker.py" "https://raw.githubusercontent.com/your-org/cred-checker/main/cred_checker.py"
        curl -sSL -o "$TOOL_DIR/requirements.txt" "https://raw.githubusercontent.com/your-org/cred-checker/main/requirements.txt"
    else
        print_error "No download tool available (git, wget, or curl required)"
        exit 1
    fi
fi

chmod +x "$TOOL_DIR/cred_checker.py"
print_success "Tool files installed"

# Step 6: Install Python dependencies
print_info "Installing Python dependencies..."

if [ -f "$TOOL_DIR/requirements.txt" ]; then
    pip3 install --user -q -r "$TOOL_DIR/requirements.txt"
else
    # Install minimal dependencies
    pip3 install --user -q rich httpx
fi

print_success "Dependencies installed"

# Step 7: Create executable wrapper
print_info "Creating executable..."

cat > "$INSTALL_DIR/cred-checker" << EOF
#!/usr/bin/env bash
# Cred Checker wrapper script
cd "$TOOL_DIR"
python3 "$TOOL_DIR/cred_checker.py" "\$@"
EOF

chmod +x "$INSTALL_DIR/cred-checker"
print_success "Executable created"

# Step 8: Download nmap script if not exists
print_info "Checking nmap NSE script..."

NSE_SCRIPT_LOCATIONS=(
    "/usr/share/nmap/scripts/http-default-accounts.nse"
    "/usr/local/share/nmap/scripts/http-default-accounts.nse"
)

NSE_FOUND=false
for location in "${NSE_SCRIPT_LOCATIONS[@]}"; do
    if [ -f "$location" ]; then
        NSE_FOUND=true
        break
    fi
done

if [ "$NSE_FOUND" = false ]; then
    print_warning "nmap NSE script not found in standard locations"
    print_info "Downloading http-default-accounts.nse..."
    wget -q -O "$TOOL_DIR/http-default-accounts.nse" \
        "https://raw.githubusercontent.com/nmap/nmap/master/scripts/http-default-accounts.nse" || \
        print_warning "Could not download NSE script. Tool may have limited functionality."
else
    print_success "nmap NSE script found"
fi

# Step 9: Add to PATH if needed
print_info "Checking PATH..."

if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    print_warning "$INSTALL_DIR is not in your PATH"
    
    # Determine shell config file
    if [ -n "$BASH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.bashrc"
    elif [ -n "$ZSH_VERSION" ]; then
        SHELL_CONFIG="$HOME/.zshrc"
    else
        SHELL_CONFIG="$HOME/.profile"
    fi
    
    echo ""
    echo "Add the following line to your $SHELL_CONFIG:"
    echo -e "${CYAN}export PATH=\"\$HOME/.local/bin:\$PATH\"${NC}"
    echo ""
    echo "Then run: source $SHELL_CONFIG"
    echo ""
else
    print_success "Installation directory is in PATH"
fi

# Step 10: Test installation
print_info "Testing installation..."

if "$INSTALL_DIR/cred-checker" --version &> /dev/null; then
    print_success "Installation test passed"
else
    print_warning "Installation test failed, but files are in place"
fi

# Final summary
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║   Installation Complete! ✓            ║${NC}"
echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}Installation Details:${NC}"
echo "  Tool Directory:    $TOOL_DIR"
echo "  Executable:        $INSTALL_DIR/cred-checker"
echo "  Results Directory: $TOOL_DIR/results"
echo ""
echo -e "${CYAN}Quick Start:${NC}"
echo "  cred-checker --doctor                    # Check dependencies"
echo "  cred-checker https://192.168.1.1         # Scan single target"
echo "  cred-checker -f targets.txt              # Scan multiple targets"
echo "  cred-checker --help                      # Show all options"
echo ""
echo -e "${CYAN}First Run:${NC}"
echo "  The tool will automatically download fingerprints on first use."
echo ""

# Check if PATH needs to be updated
if [[ ":$PATH:" != *":$INSTALL_DIR:"* ]]; then
    echo -e "${YELLOW}⚠ Don't forget to add $INSTALL_DIR to your PATH!${NC}"
    echo ""
fi

print_success "Installation complete!"
