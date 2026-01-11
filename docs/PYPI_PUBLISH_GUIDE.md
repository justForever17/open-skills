
# PyPI 发布指南与版权严重预警

本文档详细说明了如何将 `open-skills` 发布到 PyPI 的流程，并重点强调关于第三方技能（Skills）的法律合规性问题。

## ⚠️ 严重版权预警

**您绝对不能将当前的 `open_skills/skills` 目录发布到 PyPI。**

位于 `open_skills/skills/pptx/LICENSE.txt` 的许可文件明确规定：
> "Use of these materials... is governed by your agreement with Anthropic... users may not... Distribute, sublicense, or transfer these materials to any third party"
> （这些材料的使用...受您与 Anthropic 的协议管辖...用户不得...分发、转授权或转让这些材料给任何第三方）

**在 PyPI 上重新分发这些文件将直接违反 Anthropic 的服务条款并侵犯版权。**

### 推荐方案：“仅发布引擎”模式

1. **仅发布运行器代码**：修改 `MANIFEST.in`（或构建配置）以**排除** `open_skills/skills/*` 目录。
2. **本地加载技能**：更新 `open-skills` 运行器代码，使其从用户的本地目录（例如 `~/.open-skills/skills` 或当前目录）加载技能。
3. **用户指引**：明确告知用户，如果他们有权限，需自行从官方渠道私下下载技能文件，并放入指定文件夹。

---

## 发布“引擎”（仅运行器代码）

如果您剔除了专有内容，仅发布工具本身的流程如下：

### 1. 准备与注册

* 在 [PyPI](https://pypi.org/) 上注册账号。
* 开启双重认证 (2FA)。
* 生成 API Token（权限范围选 "Entire account"）。

### 2. 配置 `pyproject.toml`

确保排除专有数据。

```toml
[project]
name = "open-skills-runner"  # 改名以避免与官方专有内容混淆
version = "0.1.0"
description = "An open-source runner for MCP skills (Engine only)."
readme = "README_zh.md"
requires-python = ">=3.9"
license = { text = "MIT" }
authors = [{ name = "Your Name", email = "you@example.com" }]
dependencies = [
    "mcp>=0.1.0",
    "uvicorn>=0.34.0",
    "docker>=7.1.0"
]

[project.scripts]
open-skills = "open_skills.cli:main"

[tool.hatch.build.targets.wheel]
packages = ["open_skills"]
# 重要：显式排除专有技能目录
exclude = ["open_skills/skills"] 
```

### 3. 构建与上传

```bash
# 安装工具
uv pip install build twine

# 构建（生成 dist/ 文件夹）
python -m build

# 上传（需要您的 API token）
python -m twine upload dist/* --username __token__ --password pypi-xxxx...
```

### 4. 纯引擎包结构 (Pure Engine Structure)

构建上传后的 `open-skills` 包将仅包含核心运行时代码，**不包含**任何预置技能。目录结构如下：

```text
open-skills-0.1.0.tar.gz
├── PKG-INFO
├── README.md
├── pyproject.toml
└── open_skills/
    ├── __init__.py
    ├── cli.py        # 命令行入口
    ├── sandbox.py    # Docker 管理器
    └── skills/       # [EMPTY/EXCLUDED] 此目录被排除
```

用户安装后，必须通过 `--skills-dir` 参数提供这一部分内容。

### 5. 客户端配置 (Client Configuration)

假设包名为 `open-skills`，用户希望使用 S3 功能并挂载本地技能，`mcp_config.json` (Claude Desktop / VS Code) 配置如下：

```json
{
  "mcpServers": {
    "open-skills": {
      "command": "uvx",
      "args": [
        "open-skills",
        "--skills-dir", "/path/to/your/local/skills",  // 必须指定!
        "--work-dir", "/path/to/your/project" 
      ],
      "env": {
        // S3 配置 (可选 - 如果要用 upload_to_s3 工具)
        "S3_ENDPOINT": "https://s3.us-east-1.amazonaws.com",
        "S3_ACCESS_KEY": "YOUR_ACCESS_KEY",
        "S3_SECRET_KEY": "YOUR_SECRET_KEY",
        "S3_BUCKET": "your-bucket-name",
        "S3_REGION": "us-east-1",
        "S3_CUSTOM_DOMAIN": "https://cdn.yourdomain.com"
      }
    }
  }
}
```

> **注意**：`uvx` 会自动创建隔离环境并安装 `open-skills` 包。

### 6. 运行验证 (终极方案)

发布成功后，任何用户都可以通过 `uvx` 运行这个纯引擎，并挂载他们自己的 Skills 目录：

```bash
# 假设用户已经下载了 skills 到本地 ~/my-skills 目录
uvx open-skills --skills-dir ~/my-skills
```

**原理**：

* `uvx` 下载并运行 `open-skills` 包。
* `--skills-dir` 参数通过我们新增的代码，告诉引擎去哪加载 Skill。
* **网络隔离破解**：`uvx` 使用 Stdio 模式与 Cursor/Claude 连接，无需网络端口，完美绕过 Antigravity 的 Localhost 限制！

## 总结

* **绝对不要上传 `skills/` 文件夹。**
* 仅发布 **代码**（运行器）。
* **使用 `--skills-dir` 参数**：让用户在运行时指定版权合规的本地 Skills 路径。
