# 深度对比报告: Open Skills vs Claude Code/Computer Use

本报告基于当前代码库 `apps/open-skills` 与 Claude Code (Anthropic Research) 的公开架构细节进行对比。我们将以**批判性**的视角，审视 Open Skills 的完成度、设计缺陷与潜在风险。

## 1. 核心架构对比 (Architecture)

| 特性 | **Open Skills (当前)** | **Claude Code (标杆)** | **差距/缺陷** |
| :--- | :--- | :--- | :--- |
| **运行时环境** | **Docker 容器** (Python 3.11 Slim) | **云端沙盒** (Ubuntu MicroVM / Firecracker) | **中** - Docker 对于本地开发足够，但在安全性上不如 MicroVM。 |
| **隔离级别** | **进程级** (Linux Namespaces) | **硬件虚拟化级** (KVM/Firecracker) | **大** - 恶意 Agent 更容易逃逸 Docker 容器 (Kernel Exploit)。 |
| **文件系统** | **Bind Mount** (直接映射宿主目录) | **Virtual FS + Proxy** (虚拟文件系统) | **大** - Open Skills 对宿主文件拥有完全读写权，`rm -rf /share` 就能删光用户项目。Claude Code 通常限制在特定子目录。 |
| **多语言支持** | **Polyglot** (Python + Node.js) | **Polyglot** (Python, Node, Bash) | **持平** - 我们刚刚补齐了 Node.js 支持。 |

## 2. 依赖管理对比 (Dependency Management)

| 特性 | **Open Skills** | **Claude Code** | **点评** |
| :--- | :--- | :--- | :--- |
| **基础镜像** | **Fat Image** (预装 Pandas, Node等) | **Curated Env** (预装 500+ 常用库) | **持平** - 策略一致，都是为了减少冷启动。 |
| **动态安装** | **Agent 自主** (`pip install`) | **受控安装** (Guided pip/npm) | **Open Skills 更狂野**。Claude 可能会由 Orchestrator 接管安装过程，而我们直接把 Root 权限给了 Agent，让它自己修。这很灵活，但也很危险。 |
| **环境重置** | **重启即焚** (容器无状态) | **会话级隔离** | **一致**。这是沙盒设计的核心。 |
| **缓存机制** | **Docker Volume** (持久化) | **云端缓存层** | **一致**。我们必须这样做，否则用户体验太差。 |

## 3. 安全性批判 (Critical Security Review)

这是 Open Skills 目前最薄弱的环节：

1. **网络权限过大**:
    * **现状**: 使用 `network_mode="bridge"`。
    * **风险**: Agent 可以扫描你内网的其他设备，或者变成肉鸡攻击外部网络。
    * **Claude**: 严格的 Allowlist (白名单)，仅允许访问 PyPI, NPM, GitHub 等特定域名。

2. **文件权限失控**:
    * **现状**: `/share` 挂载为 `rw` (读写)。
    * **风险**: 没有任何 `chroot` 或路径检查。Agent 可以读取/修改挂载点下的任何文件。如果用户不小心把 `C:/` 挂载进去了，后果不堪设想。
    * **Claude**: 严格限制在 `/workspace` 下，且有 OS 级的权限管控 (Bubblewrap/Seatbelt)。

3. **Root 权限滥用**:
    * **现状**: 容器内默认是 `root` 用户。
    * **风险**: 配合 `ENV PIP_BREAK_SYSTEM_PACKAGES=1`，Agent 实际上掌控了容器的一切。虽然容器是临时的，但这增加了 Docker 逃逸的风险。
    * **Claude**: 肯定是 Non-Root 运行，通过 `sudo` (或模拟 sudo) 执行特定受限命令。

## 4. 总结与建议

**完成度评分**: **60%** (可用，但不安全)

**Open Skills 目前是一个“好用的开发工具”，但绝对不是一个“安全的生产环境”。**

* 它完美实现了**"让 Agent 跑代码"**的核心需求，且在**多语言支持**和**依赖自修复**上做得非常出色（甚至比一些受限的云端环境更灵活）。
* 但在**纵深防御 (Defense in Depth)** 上几乎是裸奔。

**改进路线 (Roadmap Recommendation)**:

1. **网络层**: 引入简单的 HTTP Proxy 或 DNS Filter，限制 Agent 只能访问包管理器域名。
2. **用户层**: 在 Dockerfile 里创建 `agent` 用户，默认非 Root 运行。仅在安装依赖时允许提权（或者预设好 sudoers）。
3. **文件层**: 在 `main.py` (MCP层) 增加路径检查中间件，禁止 Agent 访问 `../` 等越权路径，虽然 Docker 已经隔离了，但多一层检查总是好的。
