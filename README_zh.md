<div align="center">

# Open Skills

### Secure, Standardized, "Copy-Paste" Compatible Agent Skills Runtime

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![MCP Status](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-Sandboxed-2496ED)](https://www.docker.com/)

[English](README.md) | [简体中文](README_zh.md)

</div>

---

> **"Open Skills"** 是为了解决直接运行 Agent 代码带来的安全与依赖噩梦而生。我们将 Anthropic 强大的 Skills 协议完美复刻，并将其封装在一个**安全、隔离、开箱即用**的 Docker 沙盒中。

## 🚀 核心使命 (Mission)

Open Skills 是一个基于 [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 的通用技能运行时。它旨在让任何支持 MCP 的 AI 应用（如 Claude Desktop, Cursor, Windsurf）能够安全地执行复杂任务，同时解决两大痛点：

1. **依赖地狱**: 不再需要为每个脚本配置复杂的 Python 环境。
2. **安全隐患**: 彻底杜绝 AI 修改系统文件或执行恶意代码的风险。

## ✨ 核心特性 (Features)

| 特性 | 说明 |
| :--- | :--- |
| **📦 开箱即用 (Out of the Box)** | **Copy-Paste 兼容性**。直接复制 [anthropics/skills](https://github.com/anthropics/skills) 的文件夹，无需修改一行代码即可运行。智能适配层会自动处理路径映射。 |
| **🛡️ 沙盒隔离 (Sandbox Security)** | 所有代码均运行在**Docker 容器**中。Agent 只能访问隔离的 `/share` 目录，宿主机系统绝对安全。 |
| **🔋 全能环境 (Batteries Included)** | 预装 Pandas, Numpy, Playwright, LibreOffice 等主流依赖。告别 `pip install` 的烦恼，专注于任务本身。 |

## 📂 目录与架构

```text
open-skills/
├── open_skills/               # [Core] 核心逻辑包
│   ├── cli.py                 # MCP Server 入口
│   ├── sandbox.py             # Docker 容器管理器
│   ├── Dockerfile             # 全能镜像定义
│   └── skills/                # 技能库 (在这里放入你的 Skills)
├── README.md                  # 本文档
└── AGENT_GUIDE.md             # [Prompt] 让 Agent 更聪明的操作手册
```

## 🛠️ 工具集 (Toolbox)

连接 Open Skills MCP 服务后，您的 Agent 将获得以下超能力：

- 📚 **`manage_skills`**: **技能向导**。列出并查看可用技能的详细文档（自动注入沙盒路径）。
- 💻 **`execute_command`**: **执行引擎**。在安全容器内运行 Bash 命令（Python, Node, Shell 等）。
- 📂 **`read_file` / `write_file`**: **文件操作**。在工作区 (`cwd`) 安全地读写文件。
- ☁️ **`upload_to_s3` / `download_from_s3`**: **云端传输**。配置 .env 后即可实现文件与 S3 的互传。

## 💡 最佳实践

### 让 Agent "变聪明"

有时候 Agent 搞不清沙盒和宿主机的关系。我们提供了一个 **Prompt 秘籍**。在对话时，请告诉 Agent：

> "请阅读项目根目录下的 **`AGENT_GUIDE.md`**，然后帮我处理..."

**这能解决：**

1. **空间感知**: 明确 `/share` 对应当前目录。
2. **标准流程**: 强制执行 "查文档 -> 写代码 -> 跑测试" 的 SOP。
3. **权限自信**: 赋予 Agent 敢于在沙盒内执行命令的信心。

### ⚠️ 关于"元技能" (Meta-Skills)

**请勿在生产环境使用** `skill-creator` 等让 AI 自己写技能的工具。

- **风险**: 绕过安全审查。
- **建议**: **人工审查代码，AI 执行操作**。

## ⚡ 快速开始 (Quick Start)

### 1. 构建镜像 (Build Image)

这是**必选**步骤。为了极速启动，必须预先构建镜像：

```powershell
docker build -t open-skills:latest open_skills/
```

### 2. 安装 (Install)

```powershell
cd apps/open-skills
pip install -e .
```

### 3. 配置 MCP (Configure)

**关键点**: 必须显式指定 `cwd` (当前工作目录)，否则生成的文件会跑到用户主目录去！

#### Windows (Claude Desktop / VSCode)

在 `claude_desktop_config.json` 中添加：

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "python",
      "args": ["-m", "open_skills.cli"],
      "cwd": "E:\\Projects\\YourCurrentProject" 
    }
  }
}
```

#### macOS / Linux

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "python3",
      "args": ["-m", "open_skills.cli"],
      "cwd": "/home/user/projects/your-project"
    }
  }
}
```

---

<div align="center">
Made with ❤️ for the Agentic Future
</div>
