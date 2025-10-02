#!/bin/bash

# Nitter Session Token Creator
# This script helps create session tokens for Nitter to avoid rate limiting issues
# Based on: https://github.com/zedeus/nitter/wiki/Creating-session-tokens

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}=== Nitter Session Token Creator ===${NC}"
echo ""
echo "This script will help you create session tokens for Nitter to avoid rate limiting."
echo "You'll need:"
echo "1. A Twitter/X account username and password"
echo "2. 2FA secret (if you have 2FA enabled)"
echo ""
echo "Note: 2FA secret should be the base32-encoded secret from your authenticator app"
echo "      (not the 6-digit code, but the secret key used to generate codes)"
echo "      Valid characters: A-Z and 2-7 (no 0, 1, 8, 9, O, I, L)"
echo "      Example: ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
echo ""

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    echo -e "${RED}Error: Virtual environment not found at ../venv${NC}"
    echo "Please run this script from the scripts directory"
    exit 1
fi

# Activate virtual environment
source ../venv/bin/activate

# Check if required packages are installed
echo -e "${YELLOW}Checking dependencies...${NC}"
python -c "import pyotp, requests" 2>/dev/null || {
    echo -e "${YELLOW}Installing required packages...${NC}"
    pip install pyotp requests
}

echo ""
echo -e "${GREEN}Dependencies ready!${NC}"
echo ""

# Get user input
read -p "Enter your Twitter/X username: " username
read -s -p "Enter your Twitter/X password: " password
echo ""
read -p "Enter your 2FA secret (leave empty if no 2FA): " otp_secret

# Set output path
output_path="../sessions.jsonl"

echo ""
echo -e "${YELLOW}Creating session token...${NC}"
echo "Username: $username"
echo "Output file: $output_path"
echo ""

# Run the session creation script
if [ -z "$otp_secret" ]; then
    # No 2FA
    python get_session.py "$username" "$password" "" "$output_path"
else
    # With 2FA
    python get_session.py "$username" "$password" "$otp_secret" "$output_path"
fi

echo ""
echo -e "${GREEN}Session token created successfully!${NC}"
echo ""
echo "Next steps:"
echo "1. Restart your Nitter Docker container: docker-compose restart nitter"
echo "2. Test the RSS feeds to ensure they're working"
echo "3. Run your pipeline again"
echo ""
echo -e "${BLUE}Session file location: $output_path${NC}"
