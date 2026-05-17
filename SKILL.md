---
name: hermes-feishu-message
description: "Enhanced Feishu messaging with CardKit v2 streaming cards, one-card-per-turn consolidation, and runtime footer (model · duration · tokens · %)."
version: 1.0.0
author: windinternet
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [feishu, lark, messaging, cardkit, streaming, gateway, plugin]
    homepage: https://github.com/windinternet/hermes-feishu-message
---

# hermes-feishu-message

Enhanced Feishu (Lark) messaging plugin for Hermes Agent. Replaces the built-in
Feishu adapter with a CardKit v2 powered version that supports streaming cards,
one-card-per-turn consolidation, proper markdown rendering, and a runtime footer
showing model name, duration, token usage, and context percentage.

## What This Solves

Hermes' built-in Feishu adapter has three pain points:

1. **Markdown doesn't render correctly** — uses `post` message type, no wide-screen
   layout, headings degrade to bold text.
2. **Tool messages and conversation messages are chaotic** — each tool call
   produces a separate Feishu message, flooding the chat.
3. **No streaming, no runtime metadata** — no typewriter effect, no model/duration/
   tokens footer.

This plugin addresses all three via CardKit v2 streaming interactive cards.

## Quick Install

```bash
curl -fsSL https://raw.githubusercontent.com/windinternet/hermes-feishu-message/main/install.sh | bash

# Or manual
git clone https://github.com/windinternet/hermes-feishu-message.git \
  ~/.hermes/plugins/hermes-feishu-message

# Restart gateway
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart hermes-gateway
```

## Configuration

```yaml
display:
  runtime_footer:
    enabled: true
    fields:
      - model
      - duration
      - tokens
      - context_pct
```

## How It Works

The plugin registers a `FeishuCardKitAdapter` that **subclasses** the built-in
`FeishuAdapter`. It overrides only the outbound send/edit path with CardKit v2
streaming card logic.

The gateway's `platform_registry` checks plugins BEFORE built-in adapters, and
"last writer wins" — so registering under the same `"feishu"` name replaces
the built-in adapter without any source code modifications.

## Optional Patches

```bash
cd ~/.hermes/hermes-agent
patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/gateway-run.patch
patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/runtime-footer.patch
```

## Contributing

Issues, PRs, and discussions welcome at:
https://github.com/windinternet/hermes-feishu-message
