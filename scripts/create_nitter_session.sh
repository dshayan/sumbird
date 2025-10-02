#!/bin/bash

# Nitter Session Token Creator
# This script helps create session tokens for Nitter to avoid rate limiting issues
# Based on: https://github.com/zedeus/nitter/wiki/Creating-session-tokens

set -e

# Function to print output with consistent formatting
print_info() {
    echo "[INFO] $1"
}

print_warning() {
    echo "[WARNING] $1" >&2
}

print_error() {
    echo "[ERROR] $1" >&2
}

print_info "Nitter Session Token Creator"
echo ""
print_info "This script will help you create session tokens for Nitter to avoid rate limiting."
print_info "You'll need:"
print_info "1. A Twitter/X account username and password"
print_info "2. 2FA secret (if you have 2FA enabled)"
echo ""
print_info "Note: 2FA secret should be the base32-encoded secret from your authenticator app"
print_info "      (not the 6-digit code, but the secret key used to generate codes)"
print_info "      Valid characters: A-Z and 2-7 (no 0, 1, 8, 9, O, I, L)"
print_info "      Example: ABCDEFGHIJKLMNOPQRSTUVWXYZ234567"
echo ""

# Check if virtual environment exists
if [ ! -d "../venv" ]; then
    print_error "Virtual environment not found at ../venv"
    print_info "Please run this script from the scripts directory"
    exit 1
fi

# Activate virtual environment
source ../venv/bin/activate

# Check if required packages are installed
print_info "Checking dependencies..."
python -c "import pyotp, requests" 2>/dev/null || {
    print_info "Installing required packages..."
    pip install pyotp requests
}

echo ""
print_info "Dependencies ready!"
echo ""

# Get user input
read -p "Enter your Twitter/X username: " username
read -s -p "Enter your Twitter/X password: " password
echo ""
read -p "Enter your 2FA secret (leave empty if no 2FA): " otp_secret

# Set output path
output_path="../sessions.jsonl"

echo ""
print_info "Creating session token..."
print_info "Username: $username"
print_info "Output file: $output_path"
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
print_info "Session token created successfully!"
echo ""
print_info "Next steps:"
print_info "1. Restart your Nitter Docker container: docker-compose restart nitter"
print_info "2. Test the RSS feeds to ensure they're working"
print_info "3. Run your pipeline again"
echo ""
print_info "Session file location: $output_path"
