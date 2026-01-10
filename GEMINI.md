# Open Skills Initialization & Implementation Manifesto

> 本文档基于对 `anthropics/skills` 和 `agentskills.io` 的深度调研，以及本项目现有的 MCP + Sandbox 架构，旨在确立一个通用的、安全的、多环境兼容的 Agent Skills 运行时标准。

## 1. 项目愿景 (Vision)

打造一个**开源的、标准化的 MCP Skills 容器**。
核心目标是实现 **"Copy-Paste Compatibility"**：

* 用户只需将 `anthropics/skills` 或符合 `agentskills.io` 标准的官方/社区技能文件夹复制到本项目的 `skills/` 目录下。
* 无需修改任何代码，支持 MCP 的 Agent 即可在任何环境（Windows/Mac/Linux）中安全地发现、理解并执行这些技能。

## 2. 标准对齐 (Standards Alignment)

基于 [AgentSkills.io](https://agentskills.io) 和 [anthropics/skills](https://github.com/anthropics/skills) 的架构，我们必须严格遵循以下规范：

### 2.1 技能结构 (Skill Structure)

每个技能必须是一个独立的文件夹，包含核心的 `SKILL.md`：

```text
skills/
└── <skill_name>/
    ├── SKILL.md          # 核心定义（Prompt + Metadata）
    ├── scripts/          # 执行脚本 (Python/Node)
    └── assets/           # 静态资源
```

### 2.2 渐进式披露 (Progressive Disclosure)

为了节省上下文，必须实现三层加载机制：

1. **Level 1 (Discovery)**: 仅读取 `SKILL.md` 的 YAML Frontmatter (Name, Description) 暴露给 Agent。
2. **Level 2 (Activation)**: 当 Agent 决定使用某技能时，通过 `inspect_skill` 工具加载完整的 `SKILL.md` 内容 (Instructions)。
3. **Level 3 (Execution)**: 只有在真正执行脚本时，才挂载资源并运行代码。

## 3. 核心架构设计 (Architecture)

采用 **Host-Guest 模型**，结合 MCP 协议与 Docker 沙盒。

### System Overview

```mermaid
graph TD
    Client[AI Agent (Claude/Cursor)] -- MCP Protocol --> Host[Host: Open Skills MCP Server]
    Host -- Docker SDK --> Sandbox[Guest: Docker Container]
    
    subgraph "Filesystem Mapping"
        UserProject[User Project (CWD)] <==> |Bind Mount /share| ContainerShare[/share]
        SkillLib[Local Skills Lib] <==> |Bind Mount /app/skills| ContainerSkills[/app/skills]
    end
```

### 3.1 Host Side (MCP Server)

* **职责**:
  * 作为 MCP Server 响应 Agent 请求。
  * 解析 `skills/` 目录下的 Metadata。
  * 管理 Docker 容器生命周期。
  * **路径转译 (Path Translation)**: 解决 Windows/Linux 路径差异（解决 Issue #5）。host 路径 `C:\Projects\Code` <-> container 路径 `/share`。
* **工具暴露**:
  * `manage_skills`: `list` (Level 1), `inspect` (Level 2)。
  * `execute_command`: 在容器内执行命令 (Level 3)。

### 3.2 Guest Side (Sandbox)

* **环境**: 定制的 Linux Docker 镜像。
* **依赖**: 预装常用库 (`pandas`, `numpy`, `playwright`, `libreoffice`, `markitdown`) 以覆盖 90% 的官方技能需求（解决 Issue #2）。
* **权限**:
  * **Workdir**: 锁定在 `/share`。
  * **User**: 推荐切换为非 Root 用户 `guest` 运行（解决 Issue #3），但需保留 `sudo` 或 `pip --user` 能力以应对 Self-Healing。

## 4. 关键技术方案 (Implementation Strategy)

### 4.1 "Copy-Paste" 兼容层的实现 (The Adapter)

为解决官方写法与本地环境的差异（如官方可能假设直接在 host 运行），我们需要一个**中间件层**：

1. **路径注入 (Context Injection)**:
    * 官方脚本常包含相对路径引用（如 `scripts/util.py`）。
    * **方案**: 在执行 `execute_command` 前，自动注入环境变量 `SKILL_ROOT=/app/skills/<skill_name>`。
    * **方案**: 劫持 `SKILL.md` 读取，将其中引用的 `scripts/...` 自动替换为绝对路径 `/app/skills/<skill_name>/scripts/...`。

2. **依赖自愈 (Dependency Self-Healing)**:
    * 技能可能依赖未预装的库。
    * **方案**: 系统 Prompt (`AGENT_GUIDE.md`) 指导 Agent 在 `ImportError` 时自动执行 `pip install`。

### 4.2 跨平台文件系统 (Universal Filesystem)

* **Issue**: Windows Host与 Linux Container 路径格式不兼容。
* **Fix**:
  * 所有传递给 Docker 的路径必须经由 `pathlib.Path(p).resolve().as_posix()` 处理。
  * 在 Host 端维护一个 `PathMapper`，负责将 Agent 看到的 `/share` 路径转回 Host 的实际路径用于调试或日志。

### 4.3 安全隔离 (Security Sandbox)

* **Network**: 默认禁止容器外网访问，除非用户显式通过 ENV 开启白名单。
* **Filesystem**:
  * `skills/` 目录在容器内设为 **只读 (Read-Only)**，防止恶意修改技能代码。
  * `/share` 目录为 **读写 (Read-Write)**，但仅限于当前工作区绑定。

## 5. 待办事项与路线图 (Roadmap & Issues)

基于 `docs/ISSUES_AND_SOLUTIONS.md` 的优先级排序：

* [ ] **Phase 1: 核心稳固 (P0/P1)**
  * [ ] 修复路径注入漏洞 (`cli.py` 正则检查)。
  * [ ] 完善 Dockerfile 预装核心依赖 (`markitdown`, `libreoffice`)。
  * [ ] 实施镜像构建优化（Pre-built images）。

* [ ] **Phase 2: 体验升级 (P2/P3)**
  * [ ] 实现 `pathlib` 路径硬转换，彻底解决 Windows 反斜杠问题。
  * [ ] 增强 `manage_skills` 工具，自动注入绝对路径。
  * [ ] 实现宿主机网络探测 (`host.docker.internal` 注入)。

* [ ] **Phase 3: 上下游集成**
  * [ ] CI/CD 自动拉取 `agentskills.io` 官方库进行兼容性测试。
  * [ ] 发布到 MCP Registry。

## 6. 总结 (Conclusion)

Open Skills 不仅仅是一个运行环境，它是一个**协议适配器**。它抹平了 OS 差异、依赖差异和安全边界，让 Agent 能够像使用内置工具一样，安全、通过标准协议调用任意复杂的外部技能。
