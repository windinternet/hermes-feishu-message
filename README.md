# 🐦 hermes-feishu-message

> **Enhanced Feishu (Lark) messaging for Hermes Agent** — CardKit v2 streaming cards, one-card-per-turn, runtime footer, and beautiful markdown rendering.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Hermes%20Agent-Plugin-blue)](https://github.com/NousResearch/hermes-agent)

[中文文档](README_CN.md)

---

## 🤔 Why This Exists

When using Hermes Agent with Feishu out of the box, we found **three critical problems**:

1. **Markdown rendering is broken** — The built-in adapter uses `post` message type with no wide-screen layout. Headings degrade to bold text, tables and code blocks are cramped.

2. **Messages are chaos** — Every tool call (`terminal`, `web_search`, `read_file`) produces a separate Feishu message. A single turn can flood the chat with 10+ messages, mixing tool output and conversation content.

3. **No streaming, no metadata** — No typewriter effect. No model name, response duration, token usage, or context percentage when done.

These are NOT problems with Hermes — the framework has a great plugin architecture. The built-in Feishu adapter is just a basic implementation, and getting a complex PR merged into a firehose of 27,000+ existing PRs is nearly impossible.

So we built **hermes-feishu-message**: a drop-in gateway plugin using CardKit v2.

---

## ✨ What It Does

|  | Hermes Built-in | hermes-feishu-message |
|--|----------------|---------------------|
| **Message format** | `post` rich text, no wide-screen | CardKit v2 wide-screen interactive card |
| **Markdown** | Broken (headings → bold) | ✅ H1-H6 proper hierarchy |
| **Card count** | One per tool call / message chunk | ✅ One card per **entire turn** |
| **Streaming** | ❌ None | ✅ 30ms typewriter effect |
| **Tool progress** | Separate messages, chaotic | ✅ Merged into the same card |
| **Runtime footer** | ❌ None | ✅ `Completed · model · 2.3s · 1.2K · 42%` |
| **Timeout recovery** | ❌ Broken fragments | ✅ Auto-rebuild on 300309 |

```
Before (built-in)                      After (this plugin)
───────────────────────────────        ───────────────────────────────
┌────────────────────────┐              ┌──────────────────────────────┐
│ Tool: terminal          │              │                              │
│ $ ls /tmp               │              │  Here are the results…       │
└────────────────────────┘              │                              │
┌────────────────────────┐              │  ┌────────────────────────┐  │
│ Tool: web_search        │              │  │ Tool progress           │  │
│ Results: ...           │              │  │ ✓ terminal (0.3s)       │  │
└────────────────────────┘              │  │ ✓ web_search (1.2s)     │  │
┌────────────────────────┐              │  └────────────────────────┘  │
│ Here are the results…   │              │                              │
└────────────────────────┘              │  Completed · deepseek-v4-pro │
                                        │  · 2.3s · 1.2K · 42%        │
  ↑ 3 separate messages, chaos           └──────────────────────────────┘
                                           ↑ 1 clean card, full footer
```

### Features

- ✅ **CardKit v2 Streaming Cards** — Typewriter effect at 30ms frequency
- ✅ **One Card Per Turn** — Tools + response merged into a single card
- ✅ **Runtime Footer** — `Completed · model · 2.3s · 1.2K · 42%`
- ✅ **Wide-Screen Layout** — More comfortable reading experience
- ✅ **Proper Markdown** — H1-H6, tables, code blocks, blockquotes
- ✅ **Timeout Recovery** — Transparent 300309 auto-rebuild
- ✅ **Fallback Chain** — interactive → post → text, maximum delivery success
- ✅ **Zero Config** — Inherits all built-in adapter settings

---

## 📦 Installation

### Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed
- Feishu platform configured (app_id, app_secret, allowed_users)
- `lark-oapi` Python package
- Gateway running

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/windinternet/hermes-feishu-message/main/install.sh | bash
```

### Manual Install

```bash
git clone https://github.com/windinternet/hermes-feishu-message.git \
  ~/.hermes/plugins/hermes-feishu-message

cd ~/.hermes/plugins/hermes-feishu-message
bash install.sh

# Restart gateway
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart hermes-gateway

# Verify
hermes gateway status
# Look for: Feishu (CardKit Enhanced) ✓
```

### Configuration

In `~/.hermes/config.yaml`:

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

Toggle with `/footer on` in chat.

---

## 🏗️ Architecture

```
                      Hermes Gateway
                           │
              ┌────────────┼────────────┐
              │   platform_registry     │
              │  (plugins checked first) │
              └────────────┼────────────┘
                           │
              ┌────────────▼────────────┐
              │  hermes-feishu-message  │
              │  FeishuCardKitAdapter   │  ← overrides built-in "feishu"
              │    extends built-in     │
              └────────────┬────────────┘
                           │
        ┌──────────────────┼──────────────────┐
   ┌────▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
   │  send() │      │edit_message()│    │merge_footer │
   │ CardKit │      │ CardKit API  │    │  _into_card │
   │ create  │      │ PUT content  │    │ Completed · │
   └─────────┘      └─────────────┘    └─────────────┘
```

Uses Hermes' `platform_registry`. Registering under `"feishu"` replaces the built-in adapter — "last writer wins". No source code patching needed.

Subclasses the built-in `FeishuAdapter`, inheriting all connection handling, media upload, reactions, and execution approval. Only the outbound send/edit path is overridden.

---

## 🔧 Optional: Gateway Patches

For full `duration` + `tokens` footer fields, two optional patches:

| Patch | File | What |
|-------|------|------|
| `patches/gateway-run.patch` | `gateway/run.py` | Passes duration/tokens to footer builder |
| `patches/runtime-footer.patch` | `gateway/runtime_footer.py` | Adds duration/tokens formatting |

Without patches, the footer still shows `model · context%`. CardKit streaming works regardless.

```bash
cd ~/.hermes/hermes-agent
patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/gateway-run.patch
patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/runtime-footer.patch
```

---

## 🤝 Contributing

Issues, PRs, and discussions welcome!

- **Issues** — Bug reports, feature requests
- **PRs** — Fixes, improvements, new features
- **Discussions** — Share experiences, best practices

### Dev Setup

```bash
git clone https://github.com/windinternet/hermes-feishu-message.git
cd hermes-feishu-message
ln -sf "$(pwd)" ~/.hermes/plugins/hermes-feishu-message
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart hermes-gateway
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

**Made with ❤️ by [windinternet](https://github.com/windinternet)**
