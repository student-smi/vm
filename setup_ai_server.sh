#!/usr/bin/env bash
# ==============================================================================
# 🚀 OCI Cloud AI Coding Server Auto-Setup Script
# Stack: OmniRoute + Claude Code + RuFlow (Ruflo) Multi-Agent Swarm
# Compatible with Ubuntu 22.04 / 24.04 (ARM64 & x86_64)
# ==============================================================================

set -e

# Colors
GREEN='\033[032m'
BLUE='\033[034m'
YELLOW='\033[1;33m'
RED='\033[031m'
NC='\033[0m'

echo -e "${BLUE}============================================================${NC}"
echo -e "${BLUE}  🤖 Setting Up OmniRoute + Claude Code + RuFlow Server    ${NC}"
echo -e "${BLUE}============================================================${NC}"

# 1. Check Root / Sudo
if [ "$EUID" -ne 0 ]; then
  echo -e "${RED}[ERROR] Please run this script with sudo:${NC}"
  echo -e "        sudo bash $0"
  exit 1
fi

ACTUAL_USER="${SUDO_USER:-$USER}"
USER_HOME=$(eval echo "~$ACTUAL_USER")

echo -e "${YELLOW}👤 Configuring for user: ${ACTUAL_USER} (Home: ${USER_HOME})${NC}"

# 2. Swap Space Check (Crucial for 1GB - 4GB instances)
echo -e "\n${BLUE}💾 [1/6] Checking Virtual Memory / Swap Space...${NC}"
TOTAL_SWAP=$(free -m | awk '/^Swap:/ {print $2}')
if [ "$TOTAL_SWAP" -lt 3000 ]; then
  echo -e "${YELLOW}   Creating 4GB Swap file to prevent Out-Of-Memory errors...${NC}"
  if [ -f /swapfile ]; then
    swapoff /swapfile 2>/dev/null || true
    rm -f /swapfile
  fi
  fallocate -l 4G /swapfile || dd if=/dev/zero of=/swapfile bs=1M count=4096
  chmod 600 /swapfile
  mkswap /swapfile
  swapon /swapfile
  if ! grep -q "/swapfile" /etc/fstab; then
    echo '/swapfile none swap sw 0 0' >> /etc/fstab
  fi
  sysctl vm.swappiness=10
  echo 'vm.swappiness=10' > /etc/sysctl.d/99-swappiness.conf
  echo -e "${GREEN}   ✅ 4GB Swap successfully activated!${NC}"
else
  echo -e "${GREEN}   ✅ Sufficient Swap detected (${TOTAL_SWAP} MB).${NC}"
fi

# 3. System Packages
echo -e "\n${BLUE}📦 [2/6] Updating system packages & installing essentials...${NC}"
apt-get update -y
apt-get install -y curl wget git build-essential python3 python3-pip python3-venv tmux htop jq ufw unzip

# 4. Install Node.js 20 LTS
echo -e "\n${BLUE}⚡ [3/6] Installing Node.js 20 LTS...${NC}"
if ! command -v node >/dev/null 2>&1 || [ "$(node -v | cut -d'.' -f1)" != "v20" ]; then
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt-get install -y nodejs
fi
echo -e "${GREEN}   ✅ Node.js $(node -v) & npm $(npm -v) installed.${NC}"

# 5. Install PM2 (Process Manager to keep OmniRoute running 24/7)
echo -e "\n${BLUE}🔄 [4/6] Installing PM2 Process Manager...${NC}"
npm install -g pm2

# 6. Install OmniRoute, Claude Code, and RuFlow
echo -e "\n${BLUE}🚀 [5/6] Installing OmniRoute, Claude Code & RuFlow...${NC}"
npm install -g omniroute @anthropic-ai/claude-code ruflo

echo -e "${GREEN}   ✅ Global CLI tools installed:${NC}"
echo -e "      - OmniRoute (AI API Gateway)"
echo -e "      - Claude Code (@anthropic-ai/claude-code)"
echo -e "      - RuFlow / Ruflo (Multi-Agent Swarm Framework)"

# Configure Firewall for OmniRoute Dashboard port
echo -e "\n${BLUE}🛡️ [6/6] Configuring Firewall...${NC}"
if command -v ufw >/dev/null 2>&1; then
  ufw allow 22/tcp >/dev/null 2>&1 || true
  ufw allow 20128/tcp >/dev/null 2>&1 || true # OmniRoute UI / API
fi

# Create helper launcher scripts in /usr/local/bin
cat << 'EOF' > /usr/local/bin/start-omniroute
#!/usr/bin/env bash
echo "Starting OmniRoute AI Gateway via PM2 on port 20128..."
pm2 start omniroute --name "omniroute" 2>/dev/null || pm2 restart omniroute
pm2 save
echo "OmniRoute is running in background!"
echo "Dashboard / API Endpoint: http://localhost:20128"
EOF
chmod +x /usr/local/bin/start-omniroute

cat << 'EOF' > /usr/local/bin/ai-status
#!/usr/bin/env bash
echo "=== System Memory ==="
free -h
echo -e "\n=== Running PM2 Services ==="
pm2 list
EOF
chmod +x /usr/local/bin/ai-status

# Start OmniRoute service automatically
su - "$ACTUAL_USER" -c "pm2 start omniroute --name 'omniroute' 2>/dev/null || pm2 restart omniroute 2>/dev/null || true"
su - "$ACTUAL_USER" -c "pm2 save 2>/dev/null || true"

echo -e "\n${GREEN}============================================================${NC}"
echo -e "${GREEN}  🎉 ALL SET! YOUR AI CODING SERVER IS READY! 🎉          ${NC}"
echo -e "${GREEN}============================================================${NC}"
echo -e "  🌐 OmniRoute Web Dashboard:  http://YOUR_VM_IP:20128"
echo -e "  💻 Claude Code:              claude"
echo -e "  🤖 RuFlow Multi-Agent Swarm: ruflo"
echo -e "  📊 Check Status:             ai-status"
echo -e "${GREEN}============================================================${NC}\n"
