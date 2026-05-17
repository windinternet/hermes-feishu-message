# Install hermes-feishu-message

set -euo pipefail

PLUGIN_DIR="${HOME}/.hermes/plugins/hermes-feishu-message"
HERMES_REPO="${HOME}/.hermes/hermes-agent"
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${GREEN}🐦 hermes-feishu-message installer${NC}"
echo ""

# ── Step 1: Install plugin ─────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [ "$SCRIPT_DIR" != "$PLUGIN_DIR" ]; then
    echo "→ Installing plugin to ${PLUGIN_DIR}..."
    mkdir -p "$(dirname "$PLUGIN_DIR")"
    cp -r "$SCRIPT_DIR" "$PLUGIN_DIR"
    echo -e "  ${GREEN}✓${NC} Plugin installed"
else
    echo -e "  ${GREEN}✓${NC} Already in plugin directory"
fi

# ── Step 2: Check dependencies ─────────────────────────────────────────
echo "→ Checking dependencies..."

if ! python3 -c "import lark_oapi" 2>/dev/null; then
    echo -e "  ${YELLOW}⚠${NC} lark-oapi not found, installing..."
    pip install lark-oapi
fi

if ! python3 -c "from lark_oapi.api.cardkit.v1 import CreateCardRequest" 2>/dev/null; then
    echo -e "  ${RED}✗${NC} lark-oapi installed but CardKit v1 API missing"
    echo "    Try: pip install --upgrade lark-oapi"
    exit 1
fi

echo -e "  ${GREEN}✓${NC} lark-oapi with CardKit support"

# ── Step 3: Gateway patches (optional) ─────────────────────────────────
echo ""
echo "→ Optional: Apply gateway patches for full footer support (duration + tokens)?"
echo "  Without patches, the footer shows: model · context%"
echo "  With patches, the footer shows: model · 2.3s · 1.2K · 42%"
echo ""
read -p "  Apply patches? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    if [ ! -d "$HERMES_REPO" ]; then
        echo -e "  ${RED}✗${NC} Hermes repo not found at $HERMES_REPO"
    else
        echo "  → Applying gateway-run.patch..."
        if patch -p1 -d "$HERMES_REPO" --dry-run < "$PLUGIN_DIR/patches/gateway-run.patch" > /dev/null 2>&1; then
            patch -p1 -d "$HERMES_REPO" < "$PLUGIN_DIR/patches/gateway-run.patch"
            echo -e "    ${GREEN}✓${NC} gateway-run.patch applied"
        else
            echo -e "    ${YELLOW}⚠${NC} gateway-run.patch already applied or doesn't match — skipping"
        fi

        echo "  → Applying runtime-footer.patch..."
        if patch -p1 -d "$HERMES_REPO" --dry-run < "$PLUGIN_DIR/patches/runtime-footer.patch" > /dev/null 2>&1; then
            patch -p1 -d "$HERMES_REPO" < "$PLUGIN_DIR/patches/runtime-footer.patch"
            echo -e "    ${GREEN}✓${NC} runtime-footer.patch applied"
        else
            echo -e "    ${YELLOW}⚠${NC} runtime-footer.patch already applied or doesn't match — skipping"
        fi
    fi
fi

# ── Step 4: Restart gateway ────────────────────────────────────────────
echo ""
echo -e "${GREEN}✓${NC} Installation complete!"
echo ""
echo "  Next steps:"
echo "    1. Enable runtime footer in ~/.hermes/config.yaml:"
echo "       display.runtime_footer.enabled: true"
echo "    2. Restart gateway:"
echo "       export XDG_RUNTIME_DIR=/run/user/\$(id -u)"
echo "       systemctl --user restart hermes-gateway"
echo "    3. Verify:"
echo "       hermes gateway status"
echo ""
read -p "  Restart gateway now? [y/N] " -n 1 -r
echo ""
if [[ $REPLY =~ ^[Yy]$ ]]; then
    export XDG_RUNTIME_DIR="/run/user/$(id -u)"
    systemctl --user restart hermes-gateway
    echo -e "  ${GREEN}✓${NC} Gateway restarted"
fi
