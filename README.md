     1|# 🐦 hermes-feishu-message
     2|
     3|> **Enhanced Feishu (Lark) messaging for Hermes Agent** — CardKit v2 streaming cards, one-card-per-turn, runtime footer, and beautiful markdown rendering.
     4|>
     5|> **增强版飞书消息插件** — CardKit v2 流式卡片、一张一卡、运行时信息栏、Markdown 完美渲染。
     6|
     7|[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
     8|[![Hermes Agent](https://img.shields.io/badge/Hermes%20Agent-Plugin-blue)](https://github.com/NousResearch/hermes-agent)
     9|
    10|---
    11|
    12|## 🤔 Why This Exists / 为什么会有这个仓库
    13|
    14|<div align="center">
    15|
    16||  | Hermes 原版内置飞书 | hermes-feishu-message |
    17||--|-------------------|---------------------|
    18|| **消息格式** | `post` 富文本，不支持宽屏 | CardKit v2 宽屏交互卡片 |
    19|| **Markdown** | 渲染异常，标题显示为粗体 | ✅ H1-H6 正确层级渲染 |
    20|| **卡片数量** | 每条工具调用/消息片段各一张卡片 | ✅ 整个 turn 合并为**一张**卡片 |
    21|| **流式效果** | ❌ 无打字机效果 | ✅ 30ms 频率流式逐字渲染 |
    22|| **工具进度** | 独立消息，刷屏混乱 | ✅ 合并在同一张卡片内 |
    23|| **闭幕 Footer** | ❌ 无 | ✅ `已完成 · model · 2.3s · 1.2K · 42%` |
    24|| **超时恢复** | ❌ 卡片断开后碎片化 | ✅ 300309 自动透明重建 |
    25|
    26|</div>
    27|
    28|### The Problems with Hermes' Native Feishu Integration
    29|
    30|When using Hermes Agent with Feishu out of the box, we found **three critical problems**:
    31|
    32|1. **Markdown 渲染异常** — 飞书内置适配器使用 `post` 消息类型，不支持宽屏布局，标题层级渲染为粗体而非真正的 H1-H6，表格、代码块排版也受限。
    33|
    34|2. **消息混乱** — 每次工具调用（如 `terminal`、`web_search`、`read_file`）都生成独立消息。一次对话可能刷出 10+ 条消息，工具进度和对话内容混杂，阅读体验极差。
    35|
    36|3. **缺少流式反馈和信息栏** — 没有打字机效果，看不到模型在做事的实时状态。完成后没有模型名称、耗时、token 消耗、上下文占比等运行时信息。
    37|
    38|These are NOT problems with Hermes — the framework has a great plugin architecture. The built-in Feishu adapter is just a basic implementation, and it's hard to get a complex PR merged into a firehose of 27,000+ existing PRs.
    39|
    40|So we built **hermes-feishu-message**: a drop-in gateway plugin that replaces the built-in adapter with a CardKit v2 powered version — no fork, no PR waiting, no upstream merge drama.
    41|
    42|### Hermes 原生飞书交互的三大痛点
    43|
    44|开箱即用的 Hermes + 飞书存在三个严重影响体验的问题：
    45|
    46|1. **Markdown 不能正确渲染** — 内置适配器用 `post` 类型发送消息，不支持宽屏模式，标题层级丢失（H1-H4 全变粗体），表格和代码块排版受限。
    47|
    48|2. **工具消息和对话消息太乱** — 每次工具调用都产生一条独立飞书消息，一个 turn 可能刷出十几条，工具输出和对话内容完全混在一起。
    49|
    50|3. **没有流式消息，缺少处理状态/模型/token/耗时信息** — 没有打字机效果，用户不知道模型在干什么。完成后也没有模型名称、响应耗时、token 消耗等运行时元数据。
    51|
    52|这些问题不是 Hermes 框架的问题，框架本身有很好的插件架构——只是飞书内置适配器实现比较基础，而给主仓库提 PR 太难了（27K+ PR 排大队）。
    53|
    54|所以我们做了这个插件：**零侵入、即装即用**，用 CardKit v2 实现了一次升级。
    55|
    56|---
    57|
    58|## ✨ What We Solved / 我们解决了什么
    59|
    60|```
    61|Before (原生)                          After (本插件)
    62|─────────────────────────────────      ─────────────────────────────────
    63|┌──────────────────────┐               ┌──────────────────────────────┐
    64|│ 🔧 Tool: terminal     │               │                              │
    65|│ $ ls /tmp              │               │  📊 这是查询结果…            │
    66|└──────────────────────┘               │                              │
    67|┌──────────────────────┐               │  ┌────────────────────────┐  │
    68|│ 🔧 Tool: web_search   │               │  │ 🔧 工具调用进度         │  │
    69|│ Results: ...          │               │  │ ✓ terminal (0.3s)      │  │
    70|└──────────────────────┘               │  │ ✓ web_search (1.2s)    │  │
    71|┌──────────────────────┐               │  └────────────────────────┘  │
    72|│ 📝 这是查询结果…       │               │                              │
    73|└──────────────────────┘               │  已完成 · deepseek-v4-pro    │
    74|                                       │  · 2.3s · 1.2K · 42%        │
    75|  ↑ 3 条独立消息，混乱                    └──────────────────────────────┘
    76|                                          ↑ 一张干净的卡片，footer 信息完整
    77|```
    78|
    79|### Feature List
    80|
    81|- ✅ **CardKit v2 Streaming Cards** — 打字机效果，30ms 频率逐字渲染
    82|- ✅ **One Card Per Turn** — 整个 turn 合并为一张卡片，工具进度和对话在同一张内
    83|- ✅ **Runtime Footer** — `已完成 · deepseek-v4-pro · 2.3s · 1.2K · 42%`
    84|- ✅ **Wide-Screen Layout** — 宽屏卡片，更舒适的阅读体验
    85|- ✅ **Proper Markdown** — H1-H6 正确层级、表格、代码块、引用块
    86|- ✅ **Timeout Recovery** — 卡片 300309 超时自动透明重建，用户无感
    87|- ✅ **Fallback Chain** — interactive → post → text 三级降级，发送成功率最高
    88|- ✅ **Zero Config** — 继承内置适配器的所有配置（app_id、app_secret、allowed_users）
    89|
    90|---
    91|
    92|## 📦 Installation / 安装
    93|
    94|### Prerequisites
    95|
    96|- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed and working
    97|- Feishu platform already configured (app_id, app_secret, allowed_users)
    98|- `lark-oapi` Python package
    99|- Gateway running
   100|
   101|### One-Line Install
   102|
   103|```bash
   104|curl -fsSL https://raw.githubusercontent.com/windinternet/hermes-feishu-message/main/install.sh | bash
   105|```
   106|
   107|### Manual Install
   108|
   109|```bash
   110|# 1. Clone the plugin
   111|git clone https://github.com/windinternet/hermes-feishu-message.git \
   112|  ~/.hermes/plugins/hermes-feishu-message
   113|
   114|# 2. (Optional) Apply gateway patches for full footer support
   115|#    These add duration + tokens fields to runtime_footer
   116|cd ~/.hermes/plugins/hermes-feishu-message
   117|bash install.sh
   118|
   119|# 3. Restart the gateway
   120|export XDG_RUNTIME_DIR=/run/user/$(id -u)
   121|systemctl --user restart hermes-gateway
   122|
   123|# 4. Verify
   124|hermes gateway status
   125|# Look for: Feishu (CardKit Enhanced) ✓
   126|```
   127|
   128|### Configuration
   129|
   130|In `~/.hermes/config.yaml`, enable the runtime footer:
   131|
   132|```yaml
   133|display:
   134|  runtime_footer:
   135|    enabled: true
   136|    fields:
   137|      - model
   138|      - duration
   139|      - tokens
   140|      - context_pct
   141|```
   142|
   143|Then `/restart` or restart gateway. You can also toggle with `/footer on` in chat.
   144|
   145|---
   146|
   147|## 🏗️ Architecture / 架构
   148|
   149|```
   150|                      Hermes Gateway
   151|                           │
   152|              ┌────────────┼────────────┐
   153|              │   platform_registry     │
   154|              │  (checks plugins first) │
   155|              └────────────┼────────────┘
   156|                           │
   157|              ┌────────────▼────────────┐
   158|              │  hermes-feishu-message  │  ← our plugin registers here
   159|              │  FeishuCardKitAdapter   │     (same name "feishu" →
   160|              │    extends built-in     │      overrides built-in)
   161|              └────────────┬────────────┘
   162|                           │
   163|        ┌──────────────────┼──────────────────┐
   164|        │                  │                  │
   165|   ┌────▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
   166|   │  send() │      │edit_message()│    │merge_footer │
   167|   │ CardKit │      │ CardKit API  │    │  _into_card │
   168|   │ create  │      │ PUT content  │    │ 已完成 · …  │
   169|   └─────────┘      └─────────────┘    └─────────────┘
   170|```
   171|
   172|The plugin uses Hermes' **platform_registry** system. When the gateway starts, it checks `platform_registry` BEFORE its built-in if/elif chain. We register under the same name `"feishu"`, and the registry's "last writer wins" rule means our adapter replaces the built-in one — no source code patching needed.
   173|
   174|The adapter **subclasses** the built-in `FeishuAdapter`, inheriting all connection handling, media upload, reactions, execution approval, and formatting. We only override the outbound send/edit path.
   175|
   176|---
   177|
   178|## 🔧 Optional: Gateway Patches
   179|
   180|For the full `duration` + `tokens` footer fields, two small patches to the gateway core are needed:
   181|
   182|| Patch | File | What it does |
   183||-------|------|-------------|
   184|| `patches/gateway-run.patch` | `gateway/run.py` | Passes `duration`, `output_tokens`, `input_tokens` to `build_footer_line()` |
   185|| `patches/runtime-footer.patch` | `gateway/runtime_footer.py` | Adds `_format_duration()`, `_format_tokens()`, and new field support |
   186|
   187|These are **optional** — without them, the footer still shows `model · context%`. The CardKit streaming, one-card-per-turn, and markdown rendering work without any patches.
   188|
   189|Apply with:
   190|```bash
   191|cd ~/.hermes/hermes-agent
   192|patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/gateway-run.patch
   193|patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/runtime-footer.patch
   194|```
   195|
   196|---
   197|
   198|## 🤝 Contributing / 贡献
   199|
   200|Welcome! This project is open to everyone. Whether you find a bug, have a feature idea, or want to improve the code — please contribute!
   201|
   202|欢迎贡献！无论你是发现 bug、有功能想法、还是想改进代码，都欢迎参与！
   203|
   204|- **Issues** — 报告 bug、提功能建议 / Bug reports, feature requests
   205|- **PRs** — 修复、优化、新功能 / Fixes, improvements, new features
   206|- **Discussions** — 使用经验分享、最佳实践 / Share experiences, best practices
   207|
   208|### Development Setup
   209|
   210|```bash
   211|git clone https://github.com/windinternet/hermes-feishu-message.git
   212|cd hermes-feishu-message
   213|
   214|# Link to Hermes plugins for live testing
   215|ln -sf "$(pwd)" ~/.hermes/plugins/hermes-feishu-message
   216|
   217|# Restart gateway to pick up changes
   218|export XDG_RUNTIME_DIR=/run/user/$(id -u)
   219|systemctl --user restart hermes-gateway
   220|```
   221|
   222|---
   223|
   224|## 📄 License
   225|
   226|MIT — see [LICENSE](LICENSE)
   227|
   228|---
   229|
   230|## ⭐ Star History
   231|
   232|If this plugin helps you, please give it a ⭐! It helps others discover it.
   233|
   234|如果这个插件对你有帮助，欢迎 Star！让更多人看到。
   235|
   236|---
   237|
   238|**Made with ❤️ by [Yang Quanyao (杨泉耀)](https://github.com/windinternet)**
   239|