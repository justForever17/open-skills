# Open Skills

> "Open Skills" 是我在开发其他项目时的一个突发奇想 —— 如果我们能用标准的 MCP 协议，把 Anthropic 强大的 Agent Skills 完美复刻并运行在一个安全的沙盒里，会怎么样？

**Open Skills** 是一个基于 [MCP (Model Context Protocol)](https://modelcontextprotocol.io/) 的通用技能运行时。它旨在让任何支持 MCP 的 AI 应用能够“开箱即用”地获得执行复杂任务的能力，同时解决了原生脚本在不同环境下的依赖地狱和某些未经验证的skill直接运行在你主环境带来的安全隐患。

## 🚀 核心理念

### 1. 拿来即用 (Out of the Box)

我们通过 **智能适配层 (Smart Adapter)** 实现了对 [anthropics/skills](https://github.com/anthropics/skills) 的原生兼容。你只需要把官方仓库里的技能文件夹复制进来，无需修改任何代码，Agent 就能立刻使用。

### 2. 沙盒安全 (Sandbox Security)

与直接在宿主机运行 Python 脚本不同，Open Skills 默认在一个隔离的 **Docker 容器** 中执行所有技能代码。

- **文件系统隔离**: Agent 只能访问挂载的工作目录 (`/share`)，无法触碰宿主机敏感文件。
- **环境隔离**: 脚本运行在干净的 Linux 环境中，不会污染宿主机的 Python 环境。

### 3. "不折腾"的依赖哲学

我们在 `Dockerfile` 中预装了数据科学、文档处理、Web 自动化等主流依赖（Pandas, Numpy, Playwright 等）。大多数官方技能都能直接运行，无需为每个技能配置繁琐的 `venv`。

## 📂 目录结构

为什么要有个 "open_skills" 文件夹在里面？这是 Python 标准打包规范：

- **外层 `open-skills` (项目根)**: 存放配置 (`pyproject.toml`)、文档 (`README.md`) 和虚拟环境。
- **内层 `open_skills` (源码包)**: 存放实际代码。因为 Python 模块名不支持短横线 `-`，只能用下划线 `_`。

```text
open-skills/                   # [项目根目录] git repo & 配置文件
├── open_skills/               # [Python源码包] 核心代码逻辑
│   ├── __init__.py            # 标识这是一个包
│   ├── cli.py                 # 命令行入口 (open-skills link)
│   ├── sandbox.py             # Docker 管理器
│   ├── Dockerfile             # 镜像定义
│   └── skills/                # 官方技能库 (随包分发)
├── pyproject.toml             # 项目定义与依赖管理
├── README.md                  # 说明文档
└── AGENT_GUIDE.md             # Agent 操作手册
```

## 🛠️ 可用工具 (Tools)

连接此 MCP 服务后，Agent 将获得以下能力：

1. **`manage_skills`**: 技能图书管理员。Agent 可以用它“阅读” `skills/` 目录下的技能说明书。
    - *魔法特性*: 当 Agent 阅读官方技能书时，会自动将相对路径注入为绝对路径，确保在沙盒内正确运行。
2. **`execute_command`**: 在沙盒容器内执行 Bash 命令 (如运行 Python 脚本)。
3. **`read_file` / `write_file`**: 在当前工作区读写文件。
4. **`upload_to_s3` / `download_from_s3`**: 额外的功能拓展，只需要配置 .env 即可打通与 S3 的连接，实现文件的远程传输。

## 🤖 最佳实践：如何让"笨"Agent变聪明

有些模型可能无法通过工具定义直接理解沙盒的文件映射关系。我们为您准备了一个**标准提示词指南**。

在您的 IDE (如 Cursor, Windsurf, VSCode) 中，当您觉得 Agent 犯迷糊时，可以直接引用项目根目录下的 **`AGENT_GUIDE.md`** 文件：

> "请阅读 @AGENT_GUIDE.md ，然后帮我生成一个 PPT。"

**指南文件的核心作用**：

1. **明确空间感知**: 告诉 Agent `/share` 就是当前目录。
2. **强制 SOP**: 规定了 "查技能 -> 读文档 -> 写素材 -> 跑脚本" 的标准动作。
3. **Root 权限确认**: 给 Agent 自信，让它大胆执行命令。

## ⚠️ 关于“元技能” (Meta-Skills) 的重要声明

在 Anthropic 的官方库中，你可能会看到如 `skill-creator` 或 `agent-skill-creator` 这样的“元技能”（即让 AI 自己写代码创建新技能）。

**我们强烈建议：不要在生产环境中使用此类元技能。**

- **安全风险**: 允许 AI 自动编写并持久化可执行代码，等于绕过了安全审查机制。
- **稳定性**: AI 现场生成的脚本往往缺乏测试，容易崩溃。
- **最佳实践**: 请选择市面上成熟的、或你自己验证过的 Skills 复制到 `skills/` 目录。**人工审查代码，AI 执行操作**，这是更稳健的协作模式。

## 快速开始

### 1. 构建镜像 (关键)

由于 Open Skills 采用了 "预构建" 策略以确保极速启动，您必须先构建 Docker 镜像：

```powershell
docker build -t open-skills:latest open_skills/
```

### 2. 安装 (一次性)

```powershell
cd apps/open-skills
pip install -e . # pip uninstall open-skills
```

### 2. 配置 MCP (VSCode / Claude)

由于目前大多数 MCP 客户端 (包括 VSCode 插件和 Claude Desktop) 对沙盒环境的支持不完善，为了确保 Agent 生成的文件能出现在您的项目里，您需要在配置文件中**显式指定工作目录 (`cwd`)**。

#### Windows 配置示例

在 `claude_desktop_config.json` 或 `mcp.json` 中：

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "python",
      "args": ["-m", "open_skills.cli"],
      "cwd": "D:\\Projects\\您的具体项目路径"
    }
  }
}
```

#### macOS / Linux 配置示例

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "python3",
      "args": ["-m", "open_skills.cli"],
      "cwd": "/home/user/projects/your-project-path"
    }
  }
}
```

### 常见问题 Troubleshooting

#### ❓ 为什么 Agent 提示成功，但我找不到生成的文件？

**原因**: 未配置 `cwd`。
**现象**: 如果不配置 `cwd`，Open Skills 通常会默认使用**用户主目录** (`C:\Users\用户名` 或 `~`) 作为工作区。Agent 生成的文件都“流浪”到了那里。
**解决**: 按照上述指南，在配置文件中把 `cwd` 显式设置为您当前的项目路径，然后重启 MCP 服务。
