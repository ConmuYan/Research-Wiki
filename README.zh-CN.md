<div align="center">

# Research-Wiki

### 文献驱动的研究生命周期知识库

**不是又一个笔记工具，而是一套长期研究操作系统。**

严格分离「公开文献世界」与「我未发表的研究过程」，仅允许已接收论文作为回流节点。

[![CI](https://img.shields.io/github/actions/workflow/status/your-org/research-wiki/ci.yml?branch=main&label=CI)](./.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![Docs](https://img.shields.io/badge/docs-%F0%9F%93%96-informational)](./docs)
[![Agent-first](https://img.shields.io/badge/agent--first-AGENTS.md-purple)](./AGENTS.md)

[English](./README.md) · [简体中文](./README.zh-CN.md) · [文档](./docs) · [CLI 手册](./docs/cli-reference.md) · [快速开始](#快速开始)

<sub><i><b>Research-Wiki</b> 是 GitHub 上的项目名 · <b>LGRLW</b> 是底层协议名 · <code>lgrlw</code> 是 Python 包与 CLI 入口 — 三者指同一件事的不同角度。</i></sub>

</div>

---

> **当前状态 — v0.1 MVP。** 本版本提供三空间脚手架、五个核心 CLI 命令（`init`、`new-workspace`、`add-literature --manual`、`export-pack`、`lint`）、完整的边界不变量，以及带 SHA-256 manifest 的导出快照。**网络 fetcher**（`--arxiv` / `--doi` / `--ss`）、**PDF → Markdown 转换**、**Promotion 仪式**（`lgrlw promote`）已在 `docs/` 中定义，但计划 v0.2+ 才实现。见 [路线图](#路线图)。

---

## 为什么需要它

大多数研究笔记工具（Zotero、Notion、Obsidian、裸 RAG 管线）把三件本质不同的事混在一起：

1. **公开文献** —— 领域已经发表的东西。
2. **我未发表的研究** —— 我的 idea、方法草图、实验、草稿。
3. **当前正在写的论文** —— 前两者的阶段性产物。

一旦混起来，你的知识库就会缓慢滑向「支撑我这篇论文的叙事」，而不是「领域真实的现状」。几年之后，你之后所有的文献综述、引用规划、Related Work 都会被这种污染悄悄腐蚀。

**Research-Wiki 把这条分界线作为不变量 (invariant) 来执行，而不是靠自觉。**

> 文献库由外部文献持续扩展；
> 研究工作区由文献库指导并通过实验验证逐渐成熟；
> 论文由工作区与带日期的 KB 导出共同生成；
> 被接收后的论文再作为正式文献回流到文献库。

这是一个**长期复利、agent 可操作**的研究知识库所需的最小协议。

---

## 三空间架构

```mermaid
flowchart LR
    subgraph KB["Literature KB（公开）"]
        direction TB
        KB1[Papers]
        KB2[领域结构 Field Structure]
        KB3[证据 / 论断]
        KB4[概念 / 分类法]
    end

    subgraph WS["Research Workspace（私有）"]
        direction TB
        WS1[Idea Sandbox]
        WS2[方法设计]
        WS3[实验]
        WS4[论文草稿]
        WS5[评审 / rebuttal]
    end

    subgraph PR["Promotion Pipeline"]
        direction TB
        PR1[接收记录]
        PR2[最终元数据]
        PR3[回流 KB]
    end

    KB -- "带日期的 export pack" --> WS
    WS -- "仅限已接收论文" --> PR
    PR -- "promote()" --> KB
    WS -. "只读引用" .-> KB
```

| 空间 | 职责 | 谁可以写 | 准入规则 |
|---|---|---|---|
| **Literature KB** | 研究方向的公开文献状态 | 外部采集 + `promote` | 仅已发表 / 已接收 |
| **Research Workspace** | 我的私有研究生成过程 | 我 + 我的 agent | 任意 idea、假设、结果 |
| **Promotion Pipeline** | 回流 KB 的单向闸门 | `lgrlw promote` | `paper_status = accepted` |

**对你自己当前未发表工作而言，KB 是只追加的。** 唯一合法的回流路径是「已接收的论文」。

---

## 九阶段研究生命周期

```mermaid
stateDiagram-v2
    [*] --> S0
    S0: S0 文献调研
    S1: S1 初始 Literature KB
    S2: S2 持续扩展 KB
    S3: S3 Idea 形成
    S4: S4 Idea 定稿
    S5: S5 实验验证
    S6: S6 论文写作
    S7: S7 评审与修稿
    S8: S8 接收后回流 KB

    S0 --> S1
    S1 --> S2
    S2 --> S3
    S3 --> S4
    S4 --> S5
    S5 --> S6
    S6 --> S7
    S7 --> S8: accepted
    S7 --> S5: major revision
    S8 --> S2: 作为新文献加入
    S2 --> S2: 持续采集
```

每个阶段都有明确的目录位置、允许产物清单与一条对应的 lint 规则。详见 [`docs/lifecycle.md`](./docs/lifecycle.md)。

---

## 核心差异

- **边界即代码，不是自觉。** `lgrlw lint` 会在 workspace 意外写入 KB、`status: accepted` 却没有 DOI/arXiv/venue、或者 export 包的 manifest 与实际内容不一致时直接让 CI 失败。
- **Agent-first 设计。** 每个空间都自带一份 [`AGENTS.md`](./templates/literature-kb/00_System/KB_AGENTS.md) *宪法*，供 LLM agent（Claude Code / Cursor / Windsurf / Aider）读取并遵守。详见 [`docs/agents-guide.md`](./docs/agents-guide.md)。
- **带日期的不可变 export pack。** 每份论文草稿都锚定在一个具体的 KB snapshot（`06_Exports/paper_XXX_YYYY-MM-DD/`）上，含签名 manifest，让你的 Related Work 在 KB 持续扩展之后依然可复现。
- **Promotion 是一次仪式，不只是复制**（协议已定义；`lgrlw promote` 在 v0.2 实现）。Promotion 强制要求最终元数据、camera-ready 产物，并基于被接收的贡献重新生成 Field Structure / Evidence Map / Method Taxonomy 条目 —— 把你自己的论文变成领域的一等公民文献。
- **离线、本地优先、Obsidian 兼容。** 纯 Markdown + YAML frontmatter。你的知识不会住在别人的 SaaS 上。
- **小而类型化、带测试的核心。** Python 3.10+、pydantic v2、Typer。没有数据库，没有 lock-in。`httpx` 仅在 v0.2 引入（网络 fetcher 落地时）。

---

## 快速开始

### 安装

```bash
pip install lgrlw                     # 发布到 PyPI 后
# 或安装开发版：
pip install git+https://github.com/your-org/research-wiki.git
```

或者 clone 后以开发模式安装：

```bash
git clone https://github.com/your-org/research-wiki.git
cd research-wiki
pip install -e ".[dev]"
```

### 初始化一个研究方向

```bash
lgrlw init ./my-research --direction "efficient-llm-inference"
```

会创建：

```
my-research/
├── literature-kb/          # 公开文献，对你在研工作只追加
├── research-workspaces/    # 你的 idea、方法、论文草稿
└── .lgrlw.toml             # 项目配置
```

### 添加一篇文献到 KB（v0.1：仅手录）

> `--arxiv` / `--doi` / `--ss` 的网络抓取计划 v0.2 交付。MVP 仅接受全字段的手录；`--arxiv 2310.11511` 类标识符在 v0.1 仅作为元数据字段记录，不会联网。

```bash
lgrlw add-literature --manual \
  --title "Self-RAG: Learning to Retrieve, Generate, and Critique through Self-Reflection" \
  --authors "Akari Asai, Zeqiu Wu, Yizhong Wang, Avirup Sil, Hannaneh Hajishirzi" \
  --year 2023 \
  --venue "ICLR 2024" \
  --arxiv 2310.11511 \
  --tags "rag,llm,retrieval"
```

产物：`literature-kb/02_Literature/Papers/<slug>.md` 论文卡，以及 `literature-kb/01_Raw/metadata/<slug>.json` 元数据快照。BibTeX 导出会随 fetcher 一同在 v0.2 提供。

### 新建一个论文工作区

```bash
lgrlw new-workspace paper_001 --kind paper --title "你的工作标题"
```

### 为写作导出一份有据可查的 evidence pack

```bash
lgrlw export-pack paper_001
# → literature-kb/06_Exports/paper_001_2026-05-02/（不可变、含哈希）
# → 复制到 research-workspaces/paper_001/01_KB_Exports/
```

### 检查边界不变量

```bash
lgrlw lint
# ✓ frontmatter schema
# ✓ workspace 没有泄漏到 literature-kb/
# ✓ 每个 export_manifest.json 与其内容一致
# ✓ 每篇 accepted paper 都有完整最终元数据
```

### 接收后回流（计划，v0.2）

`lgrlw promote <workspace>` 将校验 `paper_status = accepted`、最终 title/authors/venue/year、DOI 或 arXiv、camera-ready 产物；通过后生成新的 Paper 页面、Claim 条目和 taxonomy 更新，并在 `00_System/log.md` 写入 promotion 记录。v0.1 MVP 仅提供仪式规范（[`docs/promotion-protocol.md`](./docs/promotion-protocol.md)），不提供命令。

v0.1 已有命令的完整说明见 [`docs/cli-reference.md`](./docs/cli-reference.md)。

---

## 仓库结构

```
research-wiki/
├── src/lgrlw/              # Python 包与 CLI
│   ├── cli.py              # Typer 入口
│   ├── commands/           # init / add-literature / export-pack / promote / lint / ...
│   ├── fetchers/           # arxiv · openalex · semantic_scholar · crossref
│   ├── lint/               # boundary · schema · links
│   ├── schemas.py          # pydantic v2 frontmatter 模型
│   └── render/             # Jinja paper card 渲染
├── templates/
│   ├── literature-kb/      # KB 骨架 + 00_System/*.md 协议文档
│   └── research-workspace/ # paper_template/ + idea_template/
├── schemas/                # 与 pydantic 模型对应的 JSON Schema
├── docs/
│   ├── architecture.md
│   ├── lifecycle.md        # 9 阶段状态机详解
│   ├── boundary-rules.md   # 什么可以跨越、什么不能
│   ├── export-protocol.md  # snapshot 如何构建
│   ├── promotion-protocol.md
│   ├── agents-guide.md     # LLM agent 行为规范
│   └── cli-reference.md
├── examples/
│   └── demo_direction/     # 小型已填充的 KB，用于快速参观
├── tests/                  # pytest 套件
└── AGENTS.md               # 顶层宪法
```

---

## 你在签署的约定

写入 `literature-kb/` 仅允许来自：

1. `lgrlw add-literature`（外部文献）
2. `lgrlw promote`（你自己的已接收论文）
3. 手动维护 Field Structure / Evidence Map 中对 **已经在 KB 内** 的论文的引用

其他任何写入 —— idea、假设、实验日志、contribution 草稿、rebuttal 笔记、未被接收的论断 —— 一律属于 `research-workspaces/<project>/`。

`lgrlw lint` 会强制检查这一点，CI 会强制检查 lint。边界完整策略（含 reviewer 新提文献、你明确纳入的 preprint 等特殊情况）详见 [`docs/boundary-rules.md`](./docs/boundary-rules.md)。

---

## 路线图

**v0.1 — 已交付（本地 MVP 闭环，无网络）**

- [x] 三空间脚手架模板（`literature-kb/`、`research-workspaces/`）
- [x] CLI：`init`、`new-workspace`、`add-literature --manual`、`export-pack`、`lint`
- [x] Boundary + schema + manifest lint（只能持续变严）
- [x] 带 SHA-256 manifest 的不可变 export pack
- [x] 可直接 lint / export-pack 的 `examples/demo_direction/`

**v0.2 — 计划中**

- [ ] `lgrlw promote` 接收仪式（规范已在 `docs/promotion-protocol.md`）
- [ ] `lgrlw.fetchers` 下的网络 fetcher：arXiv、OpenAlex、Crossref、Semantic Scholar
- [ ] `add-literature --arxiv / --doi / --ss`，带 `respx` mock 测试
- [ ] BibTeX 与论文卡并行导出

**后续**

- [ ] MinerU PDF→Markdown 集成（插件）
- [ ] Zotero 双向同步（插件）
- [ ] Obsidian graph / Dataview 辅助
- [ ] MCP server（`query_kb`, `add_literature`, `export_pack`, `promote`, `lint_boundary`）
- [ ] 只读 Web dashboard（taxonomy、evidence map）
- [ ] 多方向 monorepo 支持

另见 [open issues](https://github.com/your-org/research-wiki/issues) 与 [`CHANGELOG.md`](./CHANGELOG.md)。

---

## 贡献

欢迎 PR，特别是：边界语义细化、新 fetcher、新 lint 规则、针对具体 LLM 的 agent 提示词。请先阅读 [`CONTRIBUTING.md`](./CONTRIBUTING.md) 与 [`CODE_OF_CONDUCT.md`](./CODE_OF_CONDUCT.md)。

## 致谢

「持续复利的 wiki 胜过一次性 RAG」这条论断属于 AJ Calegari 关于 LLM 复利知识库的写作。本项目在此之上贡献了**严格边界纪律**与**接收后回流的仪式化 promotion**两部分。

## 许可证

[MIT](./LICENSE) © 2026 LGRLW contributors.
