#!/bin/bash
# ============================================================
#  Ozone Hotspot Dashboard — LAN launcher (macOS / Linux)
# ============================================================
#
#  Starts the Streamlit dashboard and binds it so other
#  computers on the same Wi-Fi / LAN can open it in a browser.
#
#  Usage:
#    chmod +x start_server.sh   # first time only
#    ./start_server.sh
#
# ============================================================

set -e

echo ""
echo "============================================================"
echo "  Ozone Hotspot Dashboard — starting..."
echo "============================================================"
echo ""

# Find local IP (best-effort, works on both macOS and most Linux)
if command -v ipconfig >/dev/null 2>&1; then
    LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null)
fi
if [ -z "$LOCAL_IP" ] && command -v hostname >/dev/null 2>&1; then
    LOCAL_IP=$(hostname -I 2>/dev/null | awk '{print $1}')
fi
if [ -z "$LOCAL_IP" ]; then
    LOCAL_IP="<your-local-ip>"
fi

echo "  On THIS PC:          http://localhost:8501"
echo "  On other PCs (LAN):  http://${LOCAL_IP}:8501"
echo ""
echo "  Tell others to connect to the \"LAN\" URL above."
echo "  Press Ctrl+C to stop the server."
echo ""
echo "============================================================"
echo ""

# Activate virtual environment if present
if [ -f "venv/bin/activate" ]; then
    # shellcheck disable=SC1091
    source venv/bin/activate
fi

streamlit run app.py \
    --server.address 0.0.0.0 \
    --server.port 8501 \
    --server.headless true \
    --browser.gatherUsageStats false
