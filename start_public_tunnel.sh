#!/bin/bash
# ============================================================
#  Ozone Hotspot Dashboard — Public URL via Cloudflare Tunnel
# ============================================================
#
#  This gives your PC a temporary https://xxxx.trycloudflare.com URL
#  that anyone (including people outside your office) can open.
#
#  FIRST-TIME SETUP:
#    macOS:   brew install cloudflare/cloudflare/cloudflared
#    Linux:   Download from https://github.com/cloudflare/cloudflared/releases/latest
#
#  USAGE:
#    chmod +x start_public_tunnel.sh   # first time only
#    ./start_public_tunnel.sh
#
# ============================================================

set -e

echo ""
echo "============================================================"
echo "  Ozone Hotspot — Public URL Launcher"
echo "============================================================"
echo ""

# Check that cloudflared is installed
if ! command -v cloudflared >/dev/null 2>&1; then
    echo "[ERROR] cloudflared not installed."
    echo ""
    echo "To install:"
    echo "  macOS:   brew install cloudflare/cloudflare/cloudflared"
    echo "  Linux:   https://github.com/cloudflare/cloudflared/releases/latest"
    echo ""
    exit 1
fi

# Activate venv if present
if [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

echo "[1/2] Starting Streamlit in background..."
streamlit run app.py \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false &
STREAMLIT_PID=$!

# Wait a few seconds for Streamlit to come up
sleep 5

# Stop streamlit when the script exits
trap "kill $STREAMLIT_PID 2>/dev/null" EXIT

echo "[2/2] Starting Cloudflare Tunnel..."
echo ""
echo "Look for 'https://' URL in the output below."
echo "Copy it and share with whoever needs access."
echo ""
echo "============================================================"
echo ""

cloudflared tunnel --url http://localhost:8501
