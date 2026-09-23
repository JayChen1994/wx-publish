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
uvicorn app.main:app --reload --port 8000

# 前端
cd frontend
npm install
npm run dev
```

浏览器打开 http://localhost:5173 。

复制 `.env.example` 为仓库根目录 `.env`，填入公众号和 LLM 凭证。**不要把密钥提交到 git。** 若密钥曾出现在聊天记录中，请先轮换再配置。

LLM 使用 OpenAI 兼容的 `/chat/completions` 接口。润色会生成微信公众号兼容 HTML，清洗危险标签，并把稿件退回待审状态，必须人工复核后再次审核。

## 发布策略

- `AUTO_PUBLISH=false`（默认）：审核通过后只创建微信草稿。
- `AUTO_PUBLISH=true`：审核通过并点击发布后调用发表接口。

系统按 `source_url` 去重，并在正文侧回写原文链接（`content_source_url`）。今日头条、小红书和微信公众号没有供任意抓取高赞文章的统一公开接口，应接入官方/已授权数据服务，或人工提交公开链接及热度数据。未获全文授权时只保存元数据、摘要与编辑新增内容。
