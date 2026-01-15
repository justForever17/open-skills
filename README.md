<div align="center">

<a href="https://github.com/justForever17/open-skills"><img src="docs/assets/header.png" width="50%" alt="Open Skills MCP" /></a>

### Plug-and-Play, Secure Sandbox, "Agent Skills" Universal Module

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![MCP Status](https://img.shields.io/badge/MCP-Compatible-green)](https://modelcontextprotocol.io/)
[![Docker](https://img.shields.io/badge/Docker-Sandboxed-2496ED)](https://www.docker.com/)

[English](README.md) | [简体中文](README_zh.md)

</div>

---

> **"Open Skills"** was born to solve the dependency hell where Claude Code's Skills functionality might fail in various differentiated environments, and the security risks of running unknown community Skill code directly on the local machine. I have perfectly replicated Anthropic's powerful Skills protocol as a plug-and-play MCP mode and encapsulated it in a **secure, isolated, out-of-the-box** Docker sandbox, allowing you to enjoy the power of Skills in any AI application that supports MCP.

<div align="center">
  <a href="https://x.com/omg3moon7/status/2011264287961145524">
    <img src="https://img.shields.io/badge/X-Watch_Demo_Video-000000?logo=x&style=for-the-badge" alt="Watch Demo Video" />
  </a>
  <br/>
  <br/>
  <img src="docs/assets/Demonstration.png" width="100%" style="border-radius: 12px; box-shadow: 0 10px 30px rgba(0,0,0,0.2);" alt="Open Skills Demonstration" />
</div>

## 🚀 Mission

**Open Skills is NOT a specific "Skill", but a true universal "Agent Skills" module.**

Following Anthropic's release of Claude Code, its powerful "Skills" extension mechanism left a strong impression. However, these Skills are currently limited to the official Claude Code CLI tool. **Open Skills** was born to break this wall, replicating Anthropic's Skills protocol as a generic **MCP (Model Context Protocol)** service.

This means: You can now directly load and run the community's rich Skills resources in **Trae**, **Windsurf**, or any MCP-supported AI application with a workspace-less environment, while enjoying enterprise-grade Docker sandbox isolation.

### 🆚 Comparison (Claude Code vs Open Skills)

| Feature | Claude Code (Official CLI) | Open Skills (MCP Server) |
| :--- | :--- | :--- |
| **Positioning** | Official Terminal Agent Tool | Generic MCP Protocol Extension Service |
| **Environment** | Limited to officially supported AI tools | **Any MCP-supported Tool (NoteGen, Windsurf, etc)** |
| **Skills Source** | Official/Local Skills Folder | Perfectly Compatible with Official Skills Structure (Copy-Paste) |
| **Runtime** | Runs directly on Host (Risky) | **Docker Isolated Sandbox (Absolutely Safe)** |
| **Dependencies** | Requires local pip/npm install | **Sandbox Pre-installed + Temporary Install (Zero Pollution)** |
| **Context Loading** | Progressive (Metadata -> Content) | **Progressive (manage_skills: list -> inspect)** |

### 🛠️ How it works

Open Skills is not simply "executing scripts", but a complete replication of the Agent Skills lifecycle:

1. **Discovery**: Attributes to `manage_skills` tool to read Skill header metadata, allowing the Agent to know "what capabilities I have" with minimal Token consumption.
2. **Progressive Loading**: When the Agent decides to use a skill, it calls `manage_skills` again to retrieve the full SOP (Standard Operating Procedure) and script instructions, mirroring the official "Progressive Disclosure" mechanism.
3. **Execution**: The Skill documentation (`SKILL.md`) itself serves as a high-quality execution plan. The Agent follows the document steps strictly within the Docker sandbox calling `execute_command` to complete tasks.

This design perfectly solves two major pain points:

1. **Dependency Hell**: No more need to configure complex Python environments for every script, or have an agent install a massive amount of unknown dependency packages on your local machine due to execution failures. The sandbox comes pre-installed with necessary dependencies and grants the agent temporary permission to install packages, purifying your local environment.

2. **Security Risks**: Completely eliminate the risk of AI modifying system files or executing malicious code. The sandbox environment mounts your /skills (read-only) directory and workspace /share (read-write) directory. Malicious code runs within the sandbox environment and cannot modify or read important files outside of the local workspace.

## ✨ Features

| Feature | Description |
| :--- | :--- |
| **📦 Out of the Box** | **Copy-Paste Compatibility**. Simply copy folders from [anthropics/skills](https://github.com/anthropics/skills) or community Skills without modifying a single line of code. The smart adapter handles path mapping automatically. |
| **🛡️ Sandbox Security** | All code runs inside a **Docker Container** that is disposed of after use. Agents can only access the mounted /skills and /share directories, keeping your host system absolutely safe. |
| **🔋 Batteries Included** | Pre-installed with mainstream dependencies like Python, Node, Pandas, Numpy, LibreOffice, etc. Say goodbye to pip/npm install troubles and focus on the task. |

## 🔐 Architecture & Design

Open Skills is carefully designed to balance security and usability:

### 1. The Agent Model

The Agent runs as a **`agent` (uid=1000)** user inside the container, not Root.

* **Permission Boundary**: The capability to destroy the system (e.g., apt-get, rm -rf /bin) is stripped, but all permissions for creative work (code read/write, script execution, pip/npm install) are retained.
* **File Ownership**: The agent user has full read/write access to the /share workspace via Docker mounting. This ensures files generated by the Agent are owned by a regular user on the host, preventing "root user only" file locking issues.

### 2. Smart Node.js Setup

To solve the classic deadlock where "Agent wants to install a package but lacks permission", we used an **Environment Injection** design:

* **Seamless Installation**: Configured NPM_CONFIG_PREFIX="/share/.npm-global". When the Agent executes npm install package, the package is automatically installed under /share where it has write permissions. The Agent thinks it's installing globally, but it's actually installing locally—**Zero Config, Zero Error**.

## 📂 Directory & Architecture

```text
open-skills/
├── open_skills/               # [Core] Core logic package
│   ├── cli.py                 # MCP Server entry point
│   ├── sandbox.py             # Docker container manager
│   ├── Dockerfile             # Batteries-included image definition
│    ├── skills/                # Skills Library (Only for dev; UVX mounts any dir via args)
├── docs/                      # [Docs] Documentation & Guides
│   ├── EN/                    # English Documentation
│   └── ZH/                    # Chinese Documentation
├── README.md                  # English Documentation
├── README_zh.md               # Chinese Documentation
└── LICENSE                    # MIT License
```

## 🛠️ Toolbox

Once connected to the Open Skills MCP service, your Agent gains the following superpowers:

* 📚 **`manage_skills`**: **Skills Librarian**. Adopts a **Progressive Loading** mechanism: first reads the header descriptions of all Skills to let the Agent quickly perceive capabilities (list), then reads the full documentation as execution SOP upon selection (inspect). The Skill documentation itself IS the plan, so no extra planning mode is needed.
* 💻 **`execute_command`**: **Execution Engine**. Run Bash commands (Python, Node, Shell, etc.) inside the secure container.
* 📂 **`read_file` / `write_file`**: **File Operations**. Securely read and write files in the workspace (read_file supports pagination).
* 🧱 **`append_file`**: **Large File Append**. Append content in chunks to bypass LLM output token limits.
* ☁️ **`upload_to_s3` / `download_from_s3`**: **Cloud Transfer**. After configuring .env, the agent can automatically transfer files to and from S3.
* 👀 **`list_directory`**: **Environment Perception**. Securely list directory contents in the workspace, needed for non-IDE environments.

## 💡 Best Practices

### Adapting Agents to the Sandbox Environment

Since we have completely decoupled the system-level execution environment of Skills and redesigned the sandbox mechanism, I suggest adding a **Prompt Secret** to your Agent Prompt to help it better master skills and the sandbox environment. (Optional, enable if you feel MCP service performance is suboptimal)

[Agent Guide (MD)](docs/EN/AGENT_PROMPT.md) > Insert this prompt into your original System Prompt.

**This solves:**

1. **Spatial Awareness**: Clarifies that /share corresponds to the current directory.
2. **Standard Procedure**: Enforces the SOP of "Read Docs -> Write Code -> Run Tests".
3. **Permission Confidence**: Gives the Agent confidence to execute commands within the sandbox.

### ⚠️ About "Meta-Skills"

**Please test in the sandbox environment before transferring.** Tools like skill-creator that let AI write skills generate Skills , That you need to manually transfer from the workspace to the /skills directory.

* **Risk**: AI-generated scripts have uncertainties; running them directly on the local machine may pose risks.
* **Recommendation**: **Human reviews code, AI executes operations**.

## ⚡ Quick Start

### 1. Prerequisites

Since Open Skills runs in a secure, isolated Docker sandbox, this is a **mandatory** step:

1. Install and start [Docker Desktop](https://www.docker.com/products/docker-desktop/).
    > **v0.2.2 Update**: **Lazy Connection** is supported. You can start the MCP service without Docker (entering Offline Mode), and connect to Docker only when the Agent actually executes a task. This prevents IDE crashes caused by service startup failures.
2. Prepare the Image (**Choose One**):

    * **Option A: Pull Official Image (Recommended)**

        ```powershell
        docker pull forever17/open-skills:latest
        ```

    * **Option B: Build Manually (For Developers)**

        Manually modify the Dockerfile to pre-install your most used dependency packages, then rebuild the image.

        ```powershell
        # Run in the source code directory
        docker build -t open-skills:latest open_skills/
        ```

### 2. Configuration

We **strongly recommend** using uvx (no need to manually install Python environment) to run directly.

#### 🚀 Recommended Configuration (via uvx)

Add to your mcp_config.json (Google Antigravity) or any AI tool that supports the MCP protocol:

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "uvx",
      "args": [
        "--from", "open-skills-mcp", "open-skills",
        "--skills-dir", "E:\\Your_Projects\\skills",  // [Required] Mount local Skills directory
        "--work-dir", "E:\\Your_Projects\\workspace"      // [Required] Specify workspace directory
      ],
      "env": {
        // [Optional] If S3 features are needed
        "S3_BUCKET": "your_bucket",
        "S3_REGION": "default",
        "S3_ENDPOINT": "https://***.com",
        "S3_CUSTOM_DOMAIN": "https://***.com",
        "S3_ACCESS_KEY": "your_key",
        "S3_SECRET_KEY": "your_secret"
      }
    }
  }
}
```

* **Parameters are Mandatory**: "--skills-dir" Mount local Skills directory (Any location) **Required**, "--work-dir" Manually specify your workspace directory (Must match your IDE workspace) **Required**.

* **Known Limitation**: When running with "uvx", closing the IDE might not correctly propagate the exit signal, leaving the Docker container running. If this happens, please manually run "docker rm -f open-skills-sandbox" or delete it via Docker Desktop.

* **IDE Task Mode**: It is recommended NOT to use Planning, Task, or Spec based Agent task modes. These modes enforce a defined task flow. Skills need to be executed strictly according to SKILL.md. **SKILL.md IS the definition of the Plan** that must be strictly adhered to and does not need to be redefined. This is often the culprit when Agents in Claude Code occasionally fail to follow the **SKILL.md** flow.

---

<details>
<summary><strong>🔧 Development Installation</strong></summary>

If you are a developer and want to run or debug from source code:

### Running Modes

#### Mode A: SSE (Recommended for Development/Debugging)

Start the HTTP service:

```bash
uvicorn open_skills.cli:mcp.sse_app --port 8000
```

SSE Client Configuration:

```json
{
  "mcpServers": {
    "open-skills": {
      "serverUrl": "http://localhost:8000/sse"
    }
  }
}
```

#### Mode B: Stdio (Local Source Run)

If you don't use uvx and want to run the source code directly:

##### Install

```powershell
git clone https://github.com/justForever17/open-skills.git
cd open-skills
pip install -e .
```

**Windows**:

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "python",
      "args": ["-m", "open_skills.cli"],
      "cwd": "E:\\Projects\\open-skills" // Source code directory
    }
  }
}
```

**macOS / Linux**:

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "python3",
      "args": ["-m", "open_skills.cli"],
      "cwd": "/path/to/open-skills"
    }
  }
}
```

</details>

---

<div align="center">
Made with ❤️ for the Agentic Future
</div>

## 📄 License

This project is licensed under the [MIT License](LICENSE).

## 💖 Sponsorship

Maintaining open source projects is hard. If you find open-skills helpful, please consider buying me a coffee!

<div align="center">

| Platform | Link | Payment Methods |
| :--- | :--- | :--- |
| **Aifadian (Afdian)** | [![Afdian](https://img.shields.io/badge/Afdian-Support-946ce6?logo=afdian)](https://afdian.com/a/justforever17) | WeChat, Alipay |

</div>
