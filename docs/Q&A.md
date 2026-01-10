# Open Skills 常见问题 (Q&A)

这里汇总了开发者在使用 Open Skills 时最常遇到的问题与核心概念解析。

## ⚙️ 配置与使用

### Q: 必须使用 `pip install -e .` 安装吗？

**A: 不是必须的。**

`install` 主要是为了将 `open-skills` 命令注册到系统路径，方便全局调用。
如果您不想安装，完全可以使用绝对路径直接运行 Python 脚本（只要依赖装好了）：

```bash
# 假设您在项目根目录
python open_skills/cli.py
```

或者使用现代化的 Python 工具 `uv` (推荐):

```bash
uv run open_skills/cli.py
```

### Q: 支持 SSE (Server-Sent Events) 模式吗？

**A: 支持。**

我们使用的 `FastMCP` 框架原生支持 SSE。如果您需要通过 HTTP/SSE 暴露服务（而不是 stdio），可以使用 `uvicorn` 启动：

```bash
# 需要先安装 uvicorn (pip install uvicorn)
# 这里的 'mcp' 是 cli.py 中的变量名
uvicorn open_skills.cli:mcp.sse_app --port 8000
```

这样您就可以通过 `http://localhost:8000/sse` 连接服务了。

**注意**: SSE 模式下，默认的工作区是您**运行命令的当前目录**。如果需要指定其他目录，请设置环境变量 `HOST_WORK_DIR`：

```bash
# PowerShell
$env:HOST_WORK_DIR="E:\Projects\MyTarget"; uvicorn open_skills.cli:mcp.sse_app --port 8000
```

### Q: 为什么 Agent 提示文件生成成功了，但我找不到文件？

**A: 极大概率是因为没有在 MCP 配置中指定 `cwd`。**

如果不设置 `cwd`，Open Skills 默认会以启动它的父进程目录（通常是 VSCode 的安装目录或用户主目录 `C:\Users\xxx`）作为工作区。Agent 生成的文件其实都静静地躺在你的 C 盘用户目录下。

**解决**: 在 MCP 配置文件 (`mcp.json` / `claude_desktop_config.json`) 中显式指定：

```json
"cwd": "E:\\Projects\\你的具体项目路径"
```

### Q: Agent 总是通过相对路径瞎操作，导致找不到文件怎么办？

**A: 现在无需担心！我们内置了“智能适配层 (Smart Adapter)”。**

以前确实需要手动注入指南。但在最新版本中，当 Agent 读取技能的 `SKILL.md` 时，系统会**自动**将脚本中的相对路径（如 `scripts/run.py`）动态替换为容器内的绝对路径（如 `/app/skills/ppt/scripts/run.py`）。

这意味着：即使是很"笨"的模型，也能开箱即用，无需额外提示。

---

## 📦 依赖与环境

### Q: Agent 可以自己安装 Python/Node 依赖吗？

**A: 可以，但我们推荐“开箱即用”模式。**

1. **Batteries Included (推荐)**: 我们的镜像已经预装了 `pandas`, `numpy`, `playwright`, `libreoffice`, `markitdown` 等 90% 的常用重型依赖。Agent 直接 import 即可，速度极快。
2. **动态安装**: 如果确实缺包，Agent 仍然可以执行 `pip install --user <package>`。
    * **注意**: 这是一个 **Guest (非 Root)** 环境，所以不能安装系统级软件（如 `apt-get` 被禁用），但这足以满足绝大多数 Python/Node 需求。

### Q: 这里的 Docker 容器有什么挂载权限？

**A: 权限设计遵循“最小权限 + 路径沙箱”原则。**

我们实现了 **Path Jail (路径越狱防御)**，Agent 的文件操作被严格限制在以下目录：

| 路径 | 权限 | 说明 |
| :--- | :--- | :--- |
| `/app/skills` | **只读 (RO)** | 技能库代码。Agent 只能看，不能改，防止破坏工具。 |
| `/share` | **读写 (RW)** | **工作区**。直接映射到你配置的 `cwd`。这是 Agent 唯一能写文件的地方。 |

---

## � 常见报错 (Troubleshooting)

### Q: 启动时报错 `RuntimeError: Docker image ... not found`？

**A: 这是因为您开启了“极速启动模式”，需要先手动构建镜像。**

为了避免每次启动都在后台偷偷跑几分钟的构建流程，我们现在要求显式构建。请在终端运行一次：

```powershell
docker build -t open-skills:latest open_skills/
```

构建一次即可长期使用。

### Q: 报错 `Security Alert: Access denied to path ...`？

**A: 这是一个安全拦截特性。**

说明 Agent 试图访问允许范围（`/share` 或 `/app/skills`）之外的文件（例如试图读取 `/etc/passwd` 或 `C:\Windows`）。这是预期的安全行为，保护您的主机不受恶意 Prompt 攻击。

### Q: Agent 无法连接我本地运行的数据库 (Connection Refused)？

**A: 请告诉 Agent 使用环境变量 `$HOST_IP`。**

容器内的 `localhost` 指向的是容器自己。为了访问宿主机，我们在启动时自动探测了宿主机 IP 并注入到了环境变量 `HOST_IP` 中。

**正确写法**:

```python
# 错误
db.connect(host="localhost", ...)

# 正确
import os
db.connect(host=os.getenv("HOST_IP"), ...)
```

---

## 💾 数据持久化

### Q: 容器退出后，哪些文件会保留？

**A: 只有“工作区”和“缓存”会保留。**

1. **✅ 会保留**:
    * **您的项目文件 (`/share`)**: 也就是您的 `cwd` 目录。
    * **依赖缓存**: `pip` 和 `npm` 的下载缓存保存在 Docker Volume 中，二次安装极快。
2. **❌ 会消失**:
    * **容器系统变更**: 任何对 `/home/guest` 以外的修改都会在重启后重置，保证环境永远纯净。
