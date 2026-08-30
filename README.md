# Chenggang Wang Academic Website

这是一个使用 Hugo 构建并通过 GitHub Pages 发布的个人学术网站。本文件说明更新不同网站内容时应编辑哪个文件。

## 快速索引

| 要更新的内容 | 主要编辑文件 |
| --- | --- |
| 姓名、职位、学校、地址、电话、邮箱、外部链接 | `config.toml` |
| 顶部导航菜单 | `config.toml` 中的 `[menu]` |
| 首页个人简介 | `layouts/index.html` |
| 首页研究方向 | `content/research_interests/index.md` |
| Biography | `content/bio/_index.md` |
| 新闻 | `data/news.yml` |
| 论文及首页精选论文 | `data/publications.yml` |
| Teaching | `content/teaching/_index.md` |
| Services | `content/services/_index.md` |
| Cipher Lab 名称和全称 | `config.toml` |
| Cipher Lab 研究方向、经费、项目、成员和 Alumni | `data/lab.yml` |
| 图片 | `static/images/` |
| Google Scholar 统计数据 | 自动更新，见下文 |
| 全站样式 | `static/css/main.css` |

## 个人信息和首页

### 基本个人信息

编辑 `config.toml` 中的 `[params]`：

- `name`：姓名
- `position`：职位
- `affliation`：学院或机构名称。当前代码使用这个拼写，请不要改成其他键名
- `university`：学校
- `address`：地址
- `phone`：电话
- `email`：邮箱
- `cv`：Curriculum Vitae 按钮链接
- `github`：GitHub 按钮链接
- `google_scholar`：Google Scholar 页面链接
- `selfImage`：首页头像路径

首页头像文件目前是：

```text
static/images/self.jpg
```

首页的研究简介句子和页面结构位于：

```text
layouts/index.html
```

首页研究方向位于：

```text
content/research_interests/index.md
```

### 导航菜单

编辑 `config.toml` 中的 `[menu]`。每个菜单项包含：

- `name`：菜单显示文字
- `url`：页面地址
- `weight`：菜单顺序，数字越小越靠前

## Biography

Biography 页面内容位于：

```text
content/bio/_index.md
```

正文使用 Markdown。`description` 是页面标题右侧的简短说明，`kicker` 是标题上方的小标题。

## 新闻

所有新闻只在下面这个文件中维护：

```text
data/news.yml
```

每条新闻格式如下：

```yaml
- date: "2026-08-30"
  display_date: "08/2026"
  text: "News content goes here."
```

- `date` 用于自动排序，格式必须为 `YYYY-MM-DD`
- `display_date` 是网页上显示的日期
- `text` 是新闻正文
- 首页自动显示日期最新的 5 条新闻
- `/news/` 页面自动显示全部新闻

不要在首页或 News 页面重复添加新闻。

## 论文

所有论文只在下面这个文件中维护：

```text
data/publications.yml
```

论文分类定义在 `sections` 中，论文条目位于 `items` 中：

```yaml
- section: "conference"
  selected: true
  year: 2026
  citation: "Complete publication citation."
```

- `section` 必须与 `sections` 中的 `key` 一致，例如 `conference`、`journal`、`workshop` 或 `patent`
- `selected: true` 表示该论文同时显示在首页 Selected Publications
- `selected: false` 表示该论文只显示在完整 Publications 页面
- `year` 是论文年份
- `citation` 是完整引用信息

Publications 页面的说明文字位于：

```text
content/pubs/_index.md
```

`.github/workflows/import-publications.yml` 是一个旧的 BibTeX 导入工作流。它会生成 `content/publication/`，但当前网站的论文页面读取的是 `data/publications.yml`，因此目前不要依赖该工作流更新网站论文。

## Teaching

课程信息位于：

```text
content/teaching/_index.md
```

使用 Markdown 标题区分学校，使用项目列表添加课程。

## Services

学术服务信息位于：

```text
content/services/_index.md
```

目前包括 Conference TPC、Session Chair 和 Journal Reviews。

## Cipher Lab

### 实验室名称

编辑 `config.toml`：

```toml
lab_name = "Cipher Lab"
lab_full_name = "Cyber Intelligence for Privacy Hardening against Emerging Risks"
```

Logo 和实验室全称的页面结构位于 `layouts/lab/list.html`，样式位于 `static/css/main.css`。普通内容更新一般不需要修改这两个文件。

### 实验室内容

实验室的主要内容统一位于：

```text
data/lab.yml
```

对应关系如下：

| YAML 区域 | 页面内容 |
| --- | --- |
| `pis` | Principal Investigator |
| `thrusts` | Lab Thrust |
| `funding` | Funding |
| `projects` | Current Projects |
| `members` | Current Members |
| `alumni` | Alumni |

项目示例：

```yaml
- title: "Project title"
  image: "/images/project-image.png"
  description: "Project description."
```

项目在网页上的顺序与 `data/lab.yml` 中的顺序完全一致。要调整顺序，只需移动整个项目条目。

成员示例：

```yaml
- name: "Student Name"
  role: "MS Student"
```

Alumni 可以额外添加当前去向：

```yaml
- name: "Alumni Name"
  note: "Now pursuing a master's degree at OUPI."
  role: "Undergraduate Student"
```

## 图片

所有网站图片放在：

```text
static/images/
```

在 YAML 或配置文件中使用以下格式引用：

```text
/images/filename.png
```

注意：

- 文件名区分大小写，GitHub Pages 上必须完全匹配
- 项目图片建议使用 4:3 横向图片
- 替换图片时可以保留原文件名，这样不需要修改数据文件
- 不要把需要发布的图片只放在电脑其他目录中

## Google Scholar 自动更新

Google Scholar 数据保存在：

```text
data/scholar.yml
```

通常不需要手工修改。自动更新由以下文件负责：

```text
scripts/update_scholar_stats.py
.github/workflows/update-scholar-stats.yml
```

GitHub Actions 每周运行一次，也可以在 GitHub 的 Actions 页面手动运行 `Update Google Scholar Stats`。

## 页面结构和样式

只有需要修改设计时才编辑以下文件：

- `static/css/main.css`：全站和 Cipher Lab 样式
- `layouts/index.html`：首页结构
- `layouts/partials/header.html`：全站导航栏
- `layouts/partials/footer.html`：全站页脚
- `layouts/partials/news_list.html`：新闻列表结构
- `layouts/partials/publications_list.html`：论文列表结构
- `layouts/lab/list.html`：Cipher Lab 页面结构

普通文字、新闻、论文、项目和成员更新应优先修改 `content/` 或 `data/`，不要直接修改布局文件。

## 本地预览

在项目根目录运行：

```bash
hugo server
```

然后访问：

```text
http://localhost:1313/
```

正式构建检查：

```bash
hugo --cleanDestinationDir --minify
```

## 发布到 GitHub Pages

提交并推送到 GitHub 的 `main` 分支后，`.github/workflows/` 中的 GitHub Actions 会自动构建并发布网站。

不要手工修改 `public/`。该目录是 Hugo 自动生成的，每次构建都可能被覆盖。

推荐更新流程：

1. 修改对应的 `content/`、`data/`、`config.toml` 或图片文件。
2. 使用 `hugo server` 本地检查。
3. 使用 `hugo --cleanDestinationDir --minify` 确认构建成功。
4. 提交修改并推送到 `main` 分支。
