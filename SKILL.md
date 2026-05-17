     1|---
     2|name: hermes-feishu-message
     3|description: "Enhanced Feishu messaging with CardKit v2 streaming cards, one-card-per-turn consolidation, and runtime footer (model · duration · tokens · %)."
     4|version: 1.0.0
     5|author: Yang Quanyao (杨泉耀)
     6|license: MIT
     7|platforms: [linux, macos, windows]
     8|metadata:
     9|  hermes:
    10|    tags: [feishu, lark, messaging, cardkit, streaming, gateway, plugin]
    11|    homepage: https://github.com/windinternet/hermes-feishu-message
    12|---
    13|
    14|# hermes-feishu-message
    15|
    16|Enhanced Feishu (Lark) messaging plugin for Hermes Agent. Replaces the built-in
    17|Feishu adapter with a CardKit v2 powered version that supports streaming cards,
    18|one-card-per-turn consolidation, proper markdown rendering, and a runtime footer
    19|showing model name, duration, token usage, and context percentage.
    20|
    21|## What This Solves
    22|
    23|Hermes' built-in Feishu adapter has three pain points:
    24|
    25|1. **Markdown doesn't render correctly** — uses `post` message type, no wide-screen
    26|   layout, headings degrade to bold text.
    27|2. **Tool messages and conversation messages are chaotic** — each tool call
    28|   produces a separate Feishu message, flooding the chat.
    29|3. **No streaming, no runtime metadata** — no typewriter effect, no model/duration/
    30|   tokens footer.
    31|
    32|This plugin addresses all three via CardKit v2 streaming interactive cards.
    33|
    34|## Quick Install
    35|
    36|```bash
    37|# One-liner
    38|curl -fsSL https://raw.githubusercontent.com/windinternet/hermes-feishu-message/main/install.sh | bash
    39|
    40|# Or manual
    41|git clone https://github.com/windinternet/hermes-feishu-message.git \
    42|  ~/.hermes/plugins/hermes-feishu-message
    43|
    44|# Restart gateway
    45|export XDG_RUNTIME_DIR=/run/user/$(id -u)
    46|systemctl --user restart hermes-gateway
    47|```
    48|
    49|## Configuration
    50|
    51|In `~/.hermes/config.yaml`:
    52|
    53|```yaml
    54|display:
    55|  runtime_footer:
    56|    enabled: true
    57|    fields:
    58|      - model
    59|      - duration
    60|      - tokens
    61|      - context_pct
    62|```
    63|
    64|## How It Works
    65|
    66|The plugin registers a `FeishuCardKitAdapter` that **subclasses** the built-in
    67|`FeishuAdapter`. It overrides only the outbound send/edit path with CardKit v2
    68|streaming card logic — all other functionality (connection, media, reactions,
    69|execution approval) is inherited unchanged.
    70|
    71|The gateway's `platform_registry` checks plugins BEFORE built-in adapters, and
    72|"last writer wins" — so registering under the same `"feishu"` name replaces
    73|the built-in adapter without any source code modifications.
    74|
    75|## Architecture
    76|
    77|```
    78|send() → CardKit card entity create → streaming_mode: true → typewriter
    79|  ├── Subsequent send() calls → edit_message() → content-update API
    80|  └── Footer detection → _merge_footer_into_card() → close streaming
    81|```
    82|
    83|## Optional Patches
    84|
    85|For full footer support (duration + tokens fields), apply the optional patches:
    86|
    87|```bash
    88|cd ~/.hermes/hermes-agent
    89|patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/gateway-run.patch
    90|patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/runtime-footer.patch
    91|```
    92|
    93|Without patches, footer still works with `model · context%`. CardKit streaming
    94|works regardless.
    95|
    96|## Troubleshooting
    97|
    98|| Symptom | Check |
    99||---------|-------|
   100|| Plugin not loading | `ls ~/.hermes/plugins/hermes-feishu-message/plugin.yaml` |
   101|| CardKit API errors | `pip install --upgrade lark-oapi` |
   102|| Footer not showing | `display.runtime_footer.enabled: true` in config.yaml |
   103|| Gateway still uses old adapter | Check logs for "re-registered" message |
   104|
   105|## Contributing
   106|
   107|Issues, PRs, and discussions welcome at:
   108|https://github.com/windinternet/hermes-feishu-message
   109|