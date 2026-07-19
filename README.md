# Biofigure Affinity SVG

[![validate](https://github.com/JackLee992/biofigure-affinity-svg/actions/workflows/validate.yml/badge.svg)](https://github.com/JackLee992/biofigure-affinity-svg/actions/workflows/validate.yml)

把生物医学与科研机制图转换为可在 **Affinity** 中按语义分组编辑，同时默认画面仍与原图保持像素一致的双态 SVG。

项目既是一个可直接安装的 Codex Skill，也提供一套独立 Python CLI。它支持：

- 对已有 PNG/JPEG 科研图进行语义分组复刻；
- 按器官、细胞、受体、神经、箭头等分组生成新图；
- 先生成整图，再反向拆分成可编辑素材；
- 只替换指定分组，不重建无关内容；
- 输出 Affinity 与 Adobe Illustrator 可打开的单文件 SVG；
- 在 Windows、macOS 和 Linux 上使用同一份 Manifest 与命令行工作流。

## 为什么是“双态 SVG”

位图科研图的像素级一致性和自由编辑通常互相冲突。本项目把它们放在同一个 SVG 中：

- **精确态**：默认显示从原图提取的无损区域，负责像素一致性。
- **编辑态**：默认隐藏，包含透明生物素材、可编辑文字和矢量神经线/箭头。

打开文件时看到的是精确态；需要修改某类对象时，再切换对应的编辑层。

## 固定九层结构

每个正式导出的 SVG 都包含以下九个顶层图层，并保持固定顺序：

| 图层 | 默认状态 | 用途 |
| --- | --- | --- |
| `00-background` | 显示 | 可修改的画布背景 |
| `01-exact-base` | 显示 | 移除语义对象后的精确底图 |
| `10-exact-assets` | 显示 | 原图中的器官、细胞、脑区等精确素材 |
| `20-exact-connectors` | 显示 | 原图中的箭头、神经线和抑制线 |
| `30-exact-text` | 显示 | 原图文字的精确像素版本 |
| `40-live-text` | 隐藏 | 可直接修改字符的 SVG 文字 |
| `50-vector-connectors` | 隐藏 | 可编辑节点、颜色和箭头端点的 SVG 路径 |
| `60-clean-assets` | 隐藏 | 去背景后的透明语义素材 |
| `90-reference` | 隐藏 | 完整原图参照 |

在 Affinity 中编辑时建议成对切换：

- 改文字：隐藏 `30-exact-text`，显示 `40-live-text`；
- 改箭头或神经线：隐藏 `20-exact-connectors`，显示 `50-vector-connectors`；
- 移动或替换生物素材：隐藏 `10-exact-assets`，显示 `60-clean-assets`。

## 安装为 Codex Skill

### Windows PowerShell

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.codex\skills" | Out-Null
git clone https://github.com/JackLee992/biofigure-affinity-svg.git "$env:USERPROFILE\.codex\skills\biofigure-affinity-svg"
Set-Location "$env:USERPROFILE\.codex\skills\biofigure-affinity-svg"
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe scripts\biofigure.py doctor
```

Windows 安装不依赖 Bash、可执行位或符号链接。

### macOS / Linux

```bash
mkdir -p ~/.codex/skills
git clone https://github.com/JackLee992/biofigure-affinity-svg.git ~/.codex/skills/biofigure-affinity-svg
cd ~/.codex/skills/biofigure-affinity-svg
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python scripts/biofigure.py doctor
```

安装后，可以在 Codex 中直接提出类似请求：

```text
使用 $biofigure-affinity-svg，把这张生物医学机制图按语义分组复刻成像素一致、可在 Affinity 中编辑的 SVG。
```

## 仅使用 CLI

也可以把仓库克隆到任意工作目录，不安装为 Codex Skill：

### Windows PowerShell

```powershell
git clone https://github.com/JackLee992/biofigure-affinity-svg.git
Set-Location biofigure-affinity-svg
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
```

### macOS / Linux

```bash
git clone https://github.com/JackLee992/biofigure-affinity-svg.git
cd biofigure-affinity-svg
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

下面的示例统一使用 `python scripts/biofigure.py`。如果系统 Python 没有依赖，请替换为对应虚拟环境中的 Python：

- Windows：`.venv\Scripts\python.exe`
- macOS/Linux：`.venv/bin/python`

## 快速开始：复刻已有科研图

### 1. 初始化项目

```text
python scripts/biofigure.py init work/my-figure --name my-figure --source original.png
```

项目会保存一份不可变的源图，并生成 `project.yaml`。

### 2. 提交语义分组建议

准备一个 UTF-8 JSON 文件：

```json
[
  {
    "id": "panel-c.drg",
    "kind": "biological-asset",
    "label": "DRG",
    "panel": "panel-c",
    "bbox": [308, 746, 64, 62],
    "z_index": 40,
    "background": "#f7f9f7",
    "tolerance": 8
  },
  {
    "id": "panel-c.brain-gut-nerve",
    "kind": "connector",
    "label": "Brain–gut afferent nerve",
    "panel": "panel-c",
    "bbox": [168, 642, 456, 298],
    "z_index": 80,
    "background": "#f7f9f7",
    "tolerance": 8
  }
]
```

应用建议：

```text
python scripts/biofigure.py suggest work/my-figure --candidates candidates.json
```

检查：

- `work/my-figure/review/numbered.png`
- `work/my-figure/review/group-report.json`

分组只是自动建议。在人工确认前，不应进行正式编译。

### 3. 调整并批准分组

```text
python scripts/biofigure.py split work/my-figure panel-c.network --replacements split.json
python scripts/biofigure.py merge work/my-figure panel-c.drg panel-c.nerve --replacement merged.json
python scripts/biofigure.py rename work/my-figure panel-c.line panel-c.brain-gut-nerve
python scripts/biofigure.py approve work/my-figure
```

任何拆分、合并、重命名或素材替换都会把 Manifest 恢复为草稿状态，需要重新人工确认和批准。

### 4. 提取、编译与验证

```text
python scripts/biofigure.py extract work/my-figure
python scripts/biofigure.py compile work/my-figure
python scripts/biofigure.py render work/my-figure
python scripts/biofigure.py qa work/my-figure
```

主要输出：

- `exports/affinity.svg`：最终双态 SVG；
- `exports/preview.png`：浏览器渲染预览；
- `review/qa-report.json`：结构与像素差异报告；
- `groups/clean/`：透明语义素材；
- `build/exact/`：精确像素素材。

## 从空白画布生成新图

```text
python scripts/biofigure.py init work/new-figure --name new-figure --width 1448 --height 1086 --background "#ffffff"
```

可选择两种路线：

1. **分组优先**：先定义器官、细胞、受体、箭头等分组，再分别生成和放置素材；
2. **整图优先**：先生成完整构图作为参照，再通过相同的建议、审核和拆分流程建立语义分组。

详细策略见 [references/generation-workflows.md](references/generation-workflows.md)。

## 替换单个分组

先查看目标：

```text
python scripts/biofigure.py inspect work/my-figure --group panel-c.drg
```

替换准备好的 PNG：

```text
python scripts/biofigure.py replace work/my-figure panel-c.drg corrected-drg.png
```

或者登记生成素材及其提示词：

```text
python scripts/biofigure.py generate work/my-figure panel-c.drg generated-drg.png --prompt "scientific DRG illustration, transparent background"
```

增量构建只处理目标分组及其依赖，不覆盖其他用户素材。

## Affinity 正式验收

自动测试不能替代真实软件导入。正式交付前应在 Affinity 中完成以下操作：

1. 打开 `exports/affinity.svg`；
2. 确认存在九个命名顶层图层；
3. 选中一个命名语义分组；
4. 移动 1 px 并成功撤销；
5. 切换三类编辑层的显示状态；
6. 修改一个 live text 对象的字符；
7. 重新打开原始 SVG。

把实际操作结果和 Affinity 版本写入 `review/affinity-check.json`，然后运行：

```text
python scripts/biofigure.py qa work/my-figure --require-affinity
```

只有该命令通过后，才应声明这次导出完成了 Affinity 导入验收。完整检查表见 [references/qa.md](references/qa.md)。

## Windows 兼容性

仓库的 GitHub Actions 会在以下环境运行完整测试：

- Windows / Python 3.9、3.12；
- macOS / Python 3.9、3.12；
- Ubuntu / Python 3.9、3.12。

Windows 工作流覆盖：

- `pathlib` 路径处理与 `/` 分隔的项目相对路径；
- 文件名包含中文、空格的项目；
- UTF-8、UTF-8 BOM 和 CRLF；
- Chrome 与 Microsoft Edge 的标准安装位置；
- 不使用 `shell=True`、Bash 或 Unix 专用工具；
- 中文/英文跨平台字体回退链。

live text 使用：

```text
Arial, Microsoft YaHei, PingFang SC, Hiragino Sans GB, sans-serif
```

由于字体替换可能改变文字几何尺寸，默认精确态始终保留原始文字像素。Windows 上的 Affinity 实际 GUI 导入仍应按项目执行上述人工验收。

## Adobe Illustrator

导出文件使用标准 SVG `<g>`、`<text>`、`<path>` 和内嵌 PNG。Illustrator 可以打开并编辑这些对象，但本项目的正式发布门槛以 Affinity 的九层导入检查为准；不同 Illustrator 版本可能把 Inkscape 命名层显示为普通命名组。

## Manifest 与路径约束

`project.yaml` 是语义身份、坐标、文字、连接线和 QA 策略的唯一事实来源。

- 所有路径必须相对于项目目录；
- Manifest 中统一使用 `/`，不能保存 Windows 或 macOS 绝对路径；
- 分组 ID 使用稳定的小写点号命名，例如 `panel-c.drg`；
- ID 一旦被文字、连接线或下游修改引用，就应视为公共接口。

完整字段说明见 [references/manifest-schema.md](references/manifest-schema.md)。

## 开发与验证

```text
python scripts/validate_repo.py
python -m pytest -q
```

官方 Codex Skill 结构可使用 `quick_validate.py` 进一步验证。当前 CI 配置见 [.github/workflows/validate.yml](.github/workflows/validate.yml)。

## 进一步阅读

- [SKILL.md](SKILL.md)：Codex 执行工作流；
- [Manifest schema](references/manifest-schema.md)：项目数据结构；
- [Affinity SVG contract](references/affinity-contract.md)：九层双态契约；
- [Generation workflows](references/generation-workflows.md)：分组生成与整图拆分；
- [QA and release gates](references/qa.md)：自动与人工验收门槛。
