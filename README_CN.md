# 🐦 hermes-feishu-message

> **增强版飞书消息插件** — CardKit v2 流式卡片、一张一卡、运行时信息栏、Markdown 完美渲染。

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Hermes Agent](https://img.shields.io/badge/Hermes%20Agent-Plugin-blue)](https://github.com/NousResearch/hermes-agent)

[English Documentation](README.md)

---

## 🤔 为什么会有这个仓库

开箱即用的 Hermes + 飞书，存在**三个严重影响体验的问题**：

1. **Markdown 不能正确渲染** — 内置适配器用 `post` 类型发送消息，不支持宽屏模式，标题层级丢失（H1-H4 全变粗体），表格和代码块排版受限。

2. **工具消息和对话消息太乱** — 每次工具调用（`terminal`、`web_search`、`read_file`）都产生一条独立飞书消息。一个 turn 可能刷出十几条，工具输出和对话内容完全混在一起。

3. **没有流式消息，缺少处理状态/模型/token/耗时信息** — 没有打字机效果，看不到模型在干嘛。完成后也没有模型名称、响应耗时、token 消耗等运行时元数据。

这不是 Hermes 框架的问题——框架本身有很好的插件架构，只是飞书内置适配器实现比较基础。而给主仓库提 PR 近乎不可能（27K+ PR 排大队）。

所以我们做了 **hermes-feishu-message**：一个即装即用的 gateway 插件，用 CardKit v2 全部重写。

---

## ✨ 我们解决了什么

|  | Hermes 原版内置 | hermes-feishu-message |
|--|----------------|---------------------|
| **消息格式** | `post` 富文本，不支持宽屏 | CardKit v2 宽屏交互卡片 |
| **Markdown** | 渲染异常，标题显示为粗体 | ✅ H1-H6 正确层级渲染 |
| **卡片数量** | 每条工具调用/消息片段各一张 | ✅ 整个 turn 合并为**一张**卡片 |
| **流式效果** | ❌ 无打字机效果 | ✅ 30ms 频率流式逐字渲染 |
| **工具进度** | 独立消息，刷屏混乱 | ✅ 合并在同一张卡片内 |
| **闭幕 Footer** | ❌ 无 | ✅ `已完成 · model · 2.3s · 1.2K · 42%` |
| **超时恢复** | ❌ 卡片断开后碎片化 | ✅ 300309 自动透明重建 |

```
Before (原生)                              After (本插件)
───────────────────────────────        ───────────────────────────────
┌────────────────────────┐              ┌──────────────────────────────┐
│ Tool: terminal          │              │                              │
│ $ ls /tmp               │              │  这是查询结果…               │
└────────────────────────┘              │                              │
┌────────────────────────┐              │  ┌────────────────────────┐  │
│ Tool: web_search        │              │  │ 工具调用进度             │  │
│ Results: ...           │              │  │ ✓ terminal (0.3s)       │  │
└────────────────────────┘              │  │ ✓ web_search (1.2s)     │  │
┌────────────────────────┐              │  └────────────────────────┘  │
│ 这是查询结果…            │              │                              │
└────────────────────────┘              │  已完成 · deepseek-v4-pro    │
                                        │  · 2.3s · 1.2K · 42%        │
  ↑ 3 条独立消息，混乱                     └──────────────────────────────┘
                                           ↑ 一张干净的卡片，footer 信息完整
```

### 功能清单

- ✅ **CardKit v2 流式卡片** — 打字机效果，30ms 频率逐字渲染
- ✅ **一张卡片一个 turn** — 工具进度和对话合并为一张卡片
- ✅ **运行时 Footer** — `已完成 · 模型 · 2.3s · 1.2K · 42%`
- ✅ **宽屏布局** — 更舒适的阅读体验
- ✅ **Markdown 完美渲染** — H1-H6 正确层级、表格、代码块、引用块
- ✅ **超时自动恢复** — 300309 透明重建，用户无感
- ✅ **三级降级** — interactive → post → text，发送成功率最高
- ✅ **零配置** — 继承内置适配器的所有设置

---

## 📦 安装

### 前置条件

- 已安装 [Hermes Agent](https://github.com/NousResearch/hermes-agent)
- 飞书平台已配置（app_id、app_secret、allowed_users）
- `lark-oapi` Python 包
- Gateway 正在运行

### 一行安装

```bash
curl -fsSL https://raw.githubusercontent.com/windinternet/hermes-feishu-message/main/install.sh | bash
```

### 手动安装

```bash
git clone https://github.com/windinternet/hermes-feishu-message.git \
  ~/.hermes/plugins/hermes-feishu-message

cd ~/.hermes/plugins/hermes-feishu-message
bash install.sh

# 重启网关
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart hermes-gateway

# 验证
hermes gateway status
# 看到：Feishu (CardKit Enhanced) ✓
```

### 配置

在 `~/.hermes/config.yaml` 中：

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

也可以在聊天中输入 `/footer on` 开关。

---

## 🏗️ 架构

```
                      Hermes Gateway
                           │
              ┌────────────┼────────────┐
              │   platform_registry     │
              │   (优先查插件)            │
              └────────────┼────────────┘
                           │
              ┌────────────▼────────────┐
              │  hermes-feishu-message  │
              │  FeishuCardKitAdapter   │  ← 同名 "feishu" 覆盖内置
              │    继承内置适配器         │
              └────────────┬────────────┘
                           │
        ┌──────────────────┼──────────────────┐
   ┌────▼────┐      ┌──────▼──────┐    ┌──────▼──────┐
   │  send() │      │edit_message()│    │merge_footer │
   │ CardKit │      │ CardKit API  │    │  _into_card │
   │ 创建卡片 │      │ PUT content  │    │ 已完成 · …  │
   └─────────┘      └─────────────┘    └─────────────┘
```

利用 Hermes 的 `platform_registry` 机制，以同名 `"feishu"` 注册，利用 "last writer wins" 规则替换内置适配器——**不需要修改 Hermes 源码**。

**子类化**内置 `FeishuAdapter`，继承全部连接处理、媒体上传、reaction、执行审批等功能，只覆盖外发消息的 send/edit 路径。

---

## 🔧 可选：Gateway 补丁

要显示完整的 `耗时` + `tokens` footer 信息，需要两个可选补丁：

| 补丁 | 文件 | 作用 |
|------|------|------|
| `patches/gateway-run.patch` | `gateway/run.py` | 将 duration/tokens 传入 footer 构建器 |
| `patches/runtime-footer.patch` | `gateway/runtime_footer.py` | 添加耗时/token 格式化函数和字段支持 |

不装补丁也能用，footer 只显示 `模型 · 上下文%`。CardKit 流式卡片完全不受影响。

```bash
cd ~/.hermes/hermes-agent
patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/gateway-run.patch
patch -p1 < ~/.hermes/plugins/hermes-feishu-message/patches/runtime-footer.patch
```

---

## 🤝 贡献

欢迎贡献！无论你是发现 bug、有功能想法、还是想改进代码，都欢迎参与！

- **Issues** — 报告 bug、提功能建议
- **PRs** — 修复、优化、新功能
- **Discussions** — 使用经验分享、最佳实践

### 开发环境

```bash
git clone https://github.com/windinternet/hermes-feishu-message.git
cd hermes-feishu-message
ln -sf "$(pwd)" ~/.hermes/plugins/hermes-feishu-message
export XDG_RUNTIME_DIR=/run/user/$(id -u)
systemctl --user restart hermes-gateway
```

---

## 📄 许可证

MIT — 详见 [LICENSE](LICENSE)

---

**Made with ❤️ by [windinternet](https://github.com/windinternet)**
