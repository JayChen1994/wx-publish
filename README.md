# FitLife Publisher

健身减脂 + 人生感悟内容工作台：授权来源采集 → AI 润色排版 → 编辑审核 → 微信公众号草稿/发表。

架构与边界以 [CHARTER.md](./CHARTER.md) 为准。Agent 约束见 `.cursor/rules/`。

## 结构

```
backend/app/domain          实体、状态机、端口
backend/app/application     用例（抓取、审核、发布）
backend/app/infrastructure  SQLite、RSS、微信 API、调度
backend/app/api             FastAPI 适配器
frontend/src/views           Vue3 工作台
```

## 启动

```bash
# 后端
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8010

# 前端
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 。

复制 `.env.example` 为仓库根目录 `.env`，填入公众号和 LLM 凭证。**不要把密钥提交到 git。** 若密钥曾出现在聊天记录中，请先轮换再配置。

LLM 使用 OpenAI 兼容的 `/chat/completions` 接口。润色会生成微信公众号兼容 HTML，清洗危险标签，并把稿件退回待审状态，必须人工复核后再次审核。

## 发布策略

- `AUTO_PUBLISH=false`（**推荐，个人主体公众号只能用这条**）：工具只调用微信 **草稿箱** API，你在 [mp.weixin.qq.com](https://mp.weixin.qq.com) 草稿箱里点「发表」。
- `AUTO_PUBLISH=true`：草稿创建后再调 **发布** API（需企业等主体且开通发布能力；个人号会报 `48001`）。

系统保留原文链接（`content_source_url`）。不落库流程见前端「复制发布」页。

## 采集能力与平台实测

抓取器支持三种来源：RSS、公开列表页（抽链接后逐篇抓）、单篇文章页；另支持在稿件页粘贴链接（可多行批量）即时抓取。抓取默认遵守 robots、按域名限速 2 秒、带超时和自定义 UA。

对你点名的三个平台，实测结论如下：

| 平台 | 实测 |
|---|---|
| 微信公众号 | `robots.txt` 为 `Disallow: /`，文章页 `/s/` 禁止；页面本身也非纯静态 |
| 今日头条 | `/item/`、`/group/`、`/trending/` 被 robots 禁止；`/article/` 返回空 `<body>` 加混淆风控 JS |
| 小红书 | `User-agent: * → Disallow: /`，全站禁止通用爬虫 |

要拿到这些平台的正文，只能执行并通过其风控 JS，属于绕过反爬，本项目不实现。`CRAWL_RESPECT_ROBOTS=false` 只是不再主动按 robots 拦截，**不会**让上述页面变得可抓，合规风险由运营者自行承担。

因此实际可跑通的路径有两条：接入官方或已授权的数据服务；或使用**手动录入**——在稿件页粘贴你有权使用的正文，再走 AI 润色、审核、发布。

### 富文本与图片

从原文正文区域复制后，粘贴到“手动录入”的富文本框：

- 纯文本会自动转成 `<h2>` / `<p>` 段落并剥离脚本、样式。
- 富文本中的 `http/https` 图片会保留，微信常见的 `data-src` 懒加载图片会自动转成 `src`。
- AI 润色前会把图片替换成不可改写的占位符，润色后恢复；模型漏掉占位符时，系统也会补回原图。
- 创建微信草稿前，系统逐张下载原图并调用微信 `media/uploadimg` 转存，然后替换正文 URL；任何一张失败都会停止发布。
- 剪贴板截图及 `blob:` / `data:` 临时图片无法长期保存，请从网页正文复制带远程地址的原图。

例如复制文章后，将原链接
`https://mp.weixin.qq.com/s/wKrkmoeb4N7kce4AQqkPRw`
填入“原文链接”，用于来源追溯和微信 `content_source_url`。
