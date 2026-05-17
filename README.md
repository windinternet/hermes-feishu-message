# 🐦 hermes-feishu-message

> **Enhanced Feishu (Lark) messaging for Hermes Agent** — CardKit v2 streaming cards, one-card-per-turn, runtime footer, and beautiful markdown rendering.
>
> **增强版飞书消息插件** — CardKit v2 流式卡片、一张一卡、运行时信息栏、Markdown 完美渲染。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Hermes%20Agent-Plugin-blue)](https://github.com/NousResearch/hermes-agent)

---

## 🤔 Why This Exists / 为什么会有这个仓库

<div align="center">

|  | Hermes 原版内置飞书 | hermes-feishu-message |
|--|-------------------|---------------------|
| **消息格式** | `post` 富文本，不支持宽屏 | CardKit v2 宽屏交互卡片 |
| **Markdown** | 渲染异常，标题显示为粗体 | ✅ H1-H6 正确层级渲染 |
| **卡片数量** | 每条工具调用/消息片段各一张卡片 | ✅ 整个 turn 合并为**一张**卡片 |
| **流式效果** | ❌ 无打字机效果 | ✅ 30ms 频率流式逐字渲染 |
| **工具进度** | 独立消息，刷屏混乱 | ✅ 合并在同一张卡片内 |
| **闭幕 Footer** | ❌ 无 | ✅ `已完成 · model · 2.3s · 1.2K · 42%` |
| **超时恢复** | ❌ 卡片断开后碎片化 | ✅ 300309 自动透明重建 |

</div>

### The Problems with Hermes' Native Feishu Integration

When using Hermes Agent with Feishu out of the box, we found **three critical problems**:

1. **Markdown 渲染异常** — 飞书内置适配器使用 `post` 消息类型，不支持宽屏布局，标题层级渲染为粗体而非真正的 H1-H6，表格、代码块排版也受限。

2. **消息混乱** — 每次工具调用（如 `terminal`、`web_search`、`read_file`）都生成独立消息。一次对话可能刷出 10+ 条消息，工具进度和对话内容混杂，阅读体验极差。

3. **缺少流式反馈和信息栏** — 没有打字机效果，看不到模型在做事的实时状态。完成后没有模型名称、耗时、token 消耗、上下文占比等运行时信息。

These are NOT problems with Hermes — the framework has a great plugin architecture. The built-in Feishu adapter is just a basic implementation, and it's hard to get a complex PR merged into a firehose of 27,000+ existing PRs.

So we built **hermes-feishu-message**: a drop-in gateway plugin that replaces the built-in adapter with a CardKit v2 powered version — no fork, no PR waiting, no upstream merge drama.

### Hermes 原生飞书交互的三大痛点

开箱即用的 Hermes + 飞书存在三个严重影响体验的问题：

1. **Markdown 不能正确渲染** — 内置适配器用 `post` 类型发送消息，不支持宽屏模式，标题层级丢失（H1-H4 全变粗体），表格和代码块排版受限。

2. **工具消息和对话消息太乱** — 每次工具调用都产生一条独立飞书消息，一个 turn 可能刷出十几条，工具输出和对话内容完全混在一起。

3. **没有流式消息，缺少处理状态/模型/token/耗时信息** — 没有打字机效果，用户不知道模型在干什么。完成后也没有模型名称、响应耗时、token 消耗等运行时元数据。

这些问题不是 Hermes 框架的问题，框架本身有很好的插件架构——只是飞书内置适配器实现比较基础，而给主仓库提 PR 太难了（27K+ PR 排大队）。

所以我们做了这个插件：**零侵入、即装即用**，用 CardKit v2 实现了一次升级。

---

## ✨ What We Solved / 我们解决了什么

```
Before (原生)                          After (本插件)
─────────────────────────────────      ─────────────────────────────────
┌──────────────────────┐               ┌──────────────────────────────┐
│ Tool: terminal        │               │                              │
│ $ ls /tmp              │               │  这是查询结果…              │
└──────────────────────┘               │                              │
┌──────────────────────┐               │  ┌────────────────────────┐  │
│ Tool: web_search       │               │  │ 工具调用进度            │  │
│ Results: ...          │               │  │ terminal (0.3s)         │  │
└──────────────────────┘               │  │ web_search (1.2s)       │  │
┌──────────────────────┐               │  └────────────────────────┘  │
│ 这是查询结果…           │               │                              │
└──────────────────────┘               │  已完成 · deepseek-v4-pro    │
                                       │  · 2.3s · 1.2K · 42%        │
  ↑ 3 条独立消息，混乱                    └──────────────────────────────┘
                                          ↑ 一张干净的卡片，footer 信息完整
```

### Feature List

- ✅ **CardKit v2 Streaming Cards** — 打字机效果，30ms 频率逐字渲染
- ✅ **One Card Per Turn** — 整个 turn 合并为一张卡片，工具进度和对话在同一张内
- ✅ **Runtime Footer** — `已完成 · deepseek-v4-pro · 2.3s · 1.2K · 42%`
- ✅ **Wide-Screen Layout** — 宽屏卡片，更舒适的阅读体验
- ✅ **Proper Markdown** — H1-H6 正确层级、表格、代码块、引用块
- ✅ **Timeout Recovery** — 卡片 300309 超时自动透明重建，用户无感
- ✅ **Fallback Chain** — interactive → post → text 三级降级，发送成功率最高
- ✅ **Zero Config** — 继承内置适配器的所有配置（app_id、app_secret、allowed_users）

---

## 📦 Installation / 安装

### Prerequisites

- [Hermes Agent](https://github.com/NousResearch/hermes-agent) installed and working
- Feishu platform already configured (app_id, app_secret, allowed_users)
- `lark-oapi` Python package
- Gateway running

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/windinternet/hermes-feishu-message/main/install.sh | bash
```

### Manual Install

```bash
# 1. Clone the plugin
git clone https://github.com/windinternet/hermes-feishu-message.git \
  ~/.hermes/plugins/hermes-feishu-message

# 2. (Optional) Apply gateway patches for full footer support
cd ~/.hermes/plugins/hermes-feishu-message
bash install.sh

# 3. Restart the gateway
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart hermes-gateway

# 4. Verify
hermes gateway status
# Look for: Feishu (CardKit Enhanced) ✓
```

### Configuration

In `~/.hermes/config.yaml`, enable the runtime footer:

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

Then `/restart` or restart gateway. You can also toggle with `/footer on` in chat.

---

## 🏗️ Architecture / 架构

```
                      Hermes Gateway
                           │
              ┌────────────┼────────────┐
              │   platform_registry     │
              │  (checks plugins first) │
              └────────────┼────────────┘
                           │
              ┌────────────▼────────────┐
              │  hermes-feishu-message  │  ← our plugin registers here
              │  FeishuCardKitAdapter   │     (same name "feishu" →
              │    extends built-in     │      overrides built-in)
              └────────────┬────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
   │  send() │      │edit_message()│    │merge_footer │
   │ CardKit │      │ CardKit API  │    │  _into_card │
   │ create  │      │ PUT content  │    │ 已完成 · …  │
   └─────────┘      └─────────────┘    └─────────────┘
```

The plugin uses Hermes' **platform_registry** system. When the gateway starts, it checks `platform_registry` BEFORE its built-in if/elif chain. We register under the same name `"feishu"`, and the registry's "last writer wins" rule means our adapter replaces the built-in one — no source code patching needed.

The adapter **subclasses** the built-in `FeishuAdapter`, inheriting all connection handling, media upload, reactions, execution approval, and formatting. We only override the outbound send/edit path.

---

## 🔧 Optional: Gateway Patches

For the full `duration` + `tokens` footer fields, two small patches to the gateway core are needed:

| Patch | File | What it does |
|-------|------|-------------|
| `patches/gateway-run.patch` | `gateway/run.py` | Passes `duration`, `output_tokens`, `input_tokens` to `build_footer_line()` |
| `patches/runtime-footer.patch` | `gateway/runtime_footer.py` | Adds `_format_duration()`, `_format_tokens()`, and new field support |

These are **optional** — without them, the footer still shows `model · context%`. The CardKit streaming, one-card-per-turn, and markdown rendering work without any patches.

Apply with:
```bash
cd ~/.hermes/hermes-agent
patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/gateway-run.patch
patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/runtime-footer.patch
```

---

## 🤝 Contributing / 贡献

Welcome! This project is open to everyone. Whether you find a bug, have a feature idea, or want to improve the code — please contribute!

欢迎贡献！无论你是发现 bug、有功能想法、还是想改进代码，都欢迎参与！

- **Issues** — 报告 bug、提功能建议 / Bug reports, feature requests
- **PRs** — 修复、优化、新功能 / Fixes, improvements, new features
- **Discussions** — 使用经验分享、最佳实践 / Share experiences, best practices

### Development Setup

```bash
git clone https://github.com/windinternet/hermes-feishu-message.git
cd hermes-feishu-message

# Link to Hermes plugins for live testing
ln -sf "$(pwd)" ~/.hermes/plugins/hermes-feishu-message

# Restart gateway to pick up changes
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart hermes-gateway
```

---

## 📄 License

MIT — see [LICENSE](LICENSE)

---

## ⭐ Star History

If this plugin helps you, please give it a ⭐! It helps others discover it.

如果这个插件对你有帮助，欢迎 Star！让更多人看到。

---

**Made with ❤️ by [windinternet](https://github.com/windinternet)**
