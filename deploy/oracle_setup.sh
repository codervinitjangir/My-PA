#!/bin/bash
set -e

echo "==========================================================="
echo "  JARVIS Oracle Cloud A1.Flex Setup (Oracle Linux 9)       "
echo "==========================================================="

# 1. System Updates and Python 3.11
echo "[1/4] Updating system and installing Python 3.11..."
sudo dnf update -y
sudo dnf install -y python3.11 python3.11-devel git curl gcc gcc-c++ wget

# 2. Install Node.js and PM2
echo "[2/4] Installing Node.js and PM2..."
if ! command -v pm2 &> /dev/null; then
    curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
    sudo dnf install -y nodejs
    sudo npm install -g pm2
else
    echo "PM2 is already installed."
fi

# 3. Clone Repository
echo "[3/4] Setting up Repository..."
if [ ! -d "Jarvis" ]; then
    echo "Please enter your Git repository URL (e.g. https://github.com/username/Jarvis.git):"
    read REPO_URL
    git clone "$REPO_URL" Jarvis
else
    echo "Jarvis directory already exists."
fi

cd Jarvis

# 4. Setup Python Virtual Environment and Install Dependencies
echo "[4/4] Creating virtual environment and installing full requirements.txt..."
python3.11 -m venv venv
source venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

echo "==========================================================="
echo " Setup Complete! "
echo " Next Steps:"
echo " 1. SCP your credentials.json and database/google_token.json to the Jarvis folder."
echo " 2. Follow deploy/ORACLE_README.md to configure the firewall and start via PM2."
echo "==========================================================="
