# Open Skills 依赖管理设计方案 (Dependency Management Design)

> **现状**: 目前 Open Skills 使用“电池内置 (Batteries Included)”策略，在 Dockerfile 中预装了常用库 (Pandas, pptx, docx 等)。
> **问题**: 当引入需要特殊依赖 (如 `scipy`, `ffmpeg`) 的新 Skill 时，运行会失败。
> **目标**: 构建一套既快又灵活，且兼容 Anthropic 原生 Skill 结构的依赖管理系统。

---

## 1. 调研分析 (Research)

### Anthropic/Claude Code 模式

* **预装环境**: 提供一个包含标准科学计算库 (Numpy, Pandas) 的基础环境。
* **动态安装**: 允许 Agent 在运行时检测到 `ModuleNotFoundError` 后，自动执行 `pip install package`。
* **沙盒网络**: 沙盒有受限的网络访问权限，专门用于拉取 PyPI 包。

### 我们当前的痛点

* `Dockerfile` 更新麻烦：每次加包都要重新 build。
* Skill 移植困难：原生 Skill (如 `pptx`) 并没有 `requirements.txt`，它们假设环境就绪。

---

## 2. 核心设计：混合依赖策略 (Hybrid Strategy)

我们采用 **"胖底座 + 动态补丁"** 的策略。

### 层级一：通用底座 (The Fat Base)

保持当前的 `Dockerfile`，但将其定位为 **"覆盖 90% 场景"** 的通用层。

* 预装：`pandas`, `numpy`, `python-docx`, `python-pptx`, `beautifulsoup4`, `requests`, `pillow`。
* **优势**: 启动快，大部分官方 Skill 直接可用。

### 层级二：技能级显式依赖 (Skill-Level Explicit)

支持在 Skill 目录下放置标准 `requirements.txt`。

* **触发时机**: 当 Agent 调用 `manage_skills(action="inspect")` 时（实际上我们在 "Smart Adapter" 层做）。
* **动作**: 自动检测该 Skill 目录下是否存在 `requirements.txt`。如果存在，且尚未安装，则在后台静默执行 `pip install`。
* **持久化**: 利用 Docker Volume 缓存 `pip` 目录，避免同类依赖重复下载。

### 层级三：Agent 动态修复 (Agent Dynamic Fix)

赋予 Agent 自主权（这也是 Claude Code 的做法）。

* **Prompt 增强**: 在 `AGENT_GUIDE.md` 中增加指引 —— "如果运行脚本报错 `ModuleNotFoundError`，你有权使用 `execute_command('pip install <库名>')` 进行修复。"
* **优势**: 能够处理那些没有声明依赖的“野路子” Skill。

---

## 3. 实施路线图 (Roadmap)

### 阶段一：镜像优化 (Image Optimization)

* [ ] 调整 `Dockerfile`，增加 `ffmpeg` 等系统级依赖（很多多媒体 Skill 需要）。
* [ ] 配置 `pip` 镜像源（国内加速），提升动态安装速度。

### 阶段二：运行时增强 (Runtime Enhancement)

* [ ] **智能加载器 (`sandbox.py`)**:
  * 在 `_start_sandbox` 后，增加 `_check_skill_requirements` 逻辑。
  * 扫描 `/app/skills/*/requirements.txt` 并自动安装（可选，或按需）。

### 阶段三：Agent 赋能

* [ ] 更新 `AGENT_GUIDE.md`，教会 Agent 遇到 `ImportError` 时的自救 SOP。

---

## 4. 推荐方案 (Actionable Proposal)

鉴于官方 Skill (如您现在的 `pptx`) 大多依赖环境预装，**目前最快见效的方案是**：

1. **扩充 Dockerfile**: 把 `temp_dep_analysis` 里扫描到的常用库都加进去。
2. **教会 Agent 自救**: 只要网络通，Agent 自己能解决剩下的 10%。

这避免了复杂的工程开发，用 AI 的智能弥补工程的刚性。
