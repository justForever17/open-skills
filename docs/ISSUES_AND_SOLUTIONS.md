# 🛑 Open Skills 问题清单与修复方案 (Prioritized Issues & Solutions)

这份文档基于深度代码审计、"Red Team" 模拟攻击以及多平台适应性分析。所有问题按**严重程度**（Blocker > Critical > High > Medium）排序。

对于每个问题，提供两档建议：

* **【快】(Fastest Fix)**: 5分钟内能改完的临时补丁，解决燃眉之急。
* **【优】(Best Effect)**: 符合工程最佳实践的长期方案，建议排期修改。

---

## 🚨 P0: 阻断性问题 (Showstoppers)

*如果不修复，Agent 根本跑不通核心流程。*

### 1. 路径注入导致脚本执行失败 (Path Injection Failure)

* **现象**: Adapter 简单的字符串替换会导致路径变成 `ooxml//app/skills/...`，Agent 执行 `python .../unpack.py` 时直接找不到文件。
* **影响**: PPTX、Docx 等依赖脚本的复杂技能完全不可用。
* **【快】**: 修改 `main.py`/`cli.py` 的替换逻辑，检测是否已经包含前缀，或者更精准的正则替换。
* **【优】**: **环境变量注入 (Env Injection)**。
  * 在 `SKILL.md` 中约定使用 `$SKILL_ROOT` 变量。
  * 在 `cli.py` 读取技能时，在内容头部自动 prepend 一行：`export SKILL_ROOT=/app/skills/xxx`。
  * Agent 看到的指令变成：`python $SKILL_ROOT/scripts/unpack.py`。这是最健壮的。

### 2. 核心依赖缺失 (Missing Critical Dependencies)

* **现象**: `SKILL.md` 要求用 `markitdown` 和 `libreoffice`，但 Docker 镜像里没装。
* **影响**: 第一次运行技能时直接报错 `Command not found` 或 `ImportError`。
* **【快】**: 在 `AGENT_GUIDE` 里加一句：“如果报错，请自己运行 `pip install` 或 `apt-get install`”。（甩锅给 Agent）
* **【优】**: **更新 Dockerfile**。将 `markitdown`, `libreoffice`, `poppler-utils` 加入预装列表。虽然镜像会变大，但这能换来秒级响应和零报错体验。

---

## 🔥 P1: 安全性高危 (Security Critical)

*如果不修复，用户的主机有被入侵或破坏的风险。*

### 3. Root 权限滥用 (Root Privilege Escalation)

* **现象**: 容器内默认是 `root`，且手动绕过了 system package 保护。
* **影响**: 恶意 Agent (或 Prompt Injection) 可以安装黑客工具、修改容器核心配置，甚至利用 Docker 漏洞逃逸。
* **【快】**: 无。安全问题没有快招。
* **【优】**: **Non-Root User**。
  * 在 Dockerfile 中创建 `guest` 用户。
  * 设置 `USER guest`。
  * 仅对 `apt/yum` 允许 sudo (需配置 sudoers) 或完全禁止 Agent 安装系统级软件，强制只能用 `pip install --user`。

### 4. 文件系统权限过大 (Filesystem Exposure)

* **现象**: `/share` 挂载点具有 RW 权限，且没有任何路径检查。
* **影响**: 如果用户错误配置 `cwd` 为 `C:\`，Agent 可以删除 System32。
* **【快】**: 在 `README` 加红字警告：**“绝对不要把 C 盘根目录设为 cwd”**。
* **【优】**: **路径沙盒化 (Chroot-like Jail)**。
  * 在 `cli.py` 的 `read_file/write_file` 中增加中间件：
  * `if ".." in path or not path.startswith(verified_root): raise PermissionError`
  * 确保 Agent 就算想跳出 `/share` 也会被逻辑拦截。

---

## 🌍 P2: 多环境适应性 (Cross-Platform Compatibility)

*影响 Windows/Linux 跨平台体验的问题。*

### 5. Windows 路径分隔符地狱 (Backslash Hell)

* **现象**: Windows 使用 `\`，Linux (Docker) 使用 `/`。简单的 `os.path.join` 在宿主机生成的路径传给 Docker 可能会乱。
* **影响**: 挂载失败，或者 Agent 在容器里看到奇怪的文件名。
* **【快】**: 在所有涉及 Docker 路径的地方，手动 `.replace('\\', '/')`。
* **【优】**: **使用 `pathlib` 并强制 Posix 转换**。
  * Python 的 `pathlib.Path(p).as_posix()` 是处理这个问题的神器。
  * 在 `sandbox.py` 中统一用 `Path` 对象处理完再转 string 给 Docker SDK。

### 6. 宿主机网络环境差异 (Docker Host Context)

* **现象**: 在 WSL2 内运行 `open-skills` 和在 Powershell 运行，对 localhost 的理解不同。
* **影响**: 如果 Open Skills 需要访问宿主机的其他服务（如 Postgres），`localhost` 可能不通。
* **【快】**: 文档说明：“请使用 `host.docker.internal` 访问宿主机”。
* **【优】**: **自动探测并注入 Host IP**。
  * 脚本在启动容器时自动探测当前的 Docker Host IP，注入为环境变量 `HOST_IP` 给 Agent 使用。

---

## 📉 P3: 效率与体验 (Efficiency & UX)

*不影响功能，但影响“爽”度。*

### 7. 相对路径盲区 (Relative Path Blindness)

* **现象**: Agent 读了 `SKILL.md` 后想读同目录的 `readme.txt`，但它不知道自己在哪个绝对路径。
* **【快】**: 在 System Prompt 里告诉 Agent：“别用相对路径，用 `find` 命令找文件”。
* **【优】**: **Tool 增强**。
  * `inspect_skill` 返回时，不仅返回内容，还在头部注释里写上：`# Location: /app/skills/pptx/SKILL.md`。
  * 或者给 `read_file` 增加 `cwd` 参数的支持。

### 8. 镜像构建时间过长 (Slow Build)

* **现象**: `open-skills` 第一次启动要 build 很久，用户以为死机了。
* **【快】**: 打印更多日志到 stderr：“正在构建，请喝杯咖啡...”。
* **【优】**: **预构建发布 (Pre-built Image)**。
  * CI/CD 流水线构建这就 `ghcr.io/v8chat/open-skills:latest`。
  * 用户端通过 `docker pull` 代替 `docker build`。
