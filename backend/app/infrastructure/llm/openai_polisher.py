import json
import re

import bleach
import httpx

from app.core.config import settings
from app.core.errors import PolishFailed
from app.domain.models import Article, PolishedContent


SYSTEM_PROMPT = """你是微信公众号资深编辑。请在不改变事实、不虚构数据和经历的前提下，
将用户提供且有权处理的素材润色成适合微信公众号阅读的文章。
要求：
1. 输出严格 JSON，字段仅有 title、summary、body_html。
2. body_html 使用简洁的微信公众号兼容 HTML，只用 p、h2、h3、strong、blockquote、ul、ol、li、a 标签。
3. 优化结构、节奏和可读性，不复制大段原文，不伪装成原作者的亲身经历。
4. 文末明确写“内容参考”并包含原作者和原始链接。
5. 不输出 Markdown 代码围栏。"""


def _parse_json(content: str) -> dict[str, str]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip())
    try:
        data = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise PolishFailed("LLM 未返回有效 JSON") from exc
    required = ("title", "summary", "body_html")
    if not all(isinstance(data.get(key), str) and data[key].strip() for key in required):
        raise PolishFailed("LLM 返回内容缺少必要字段")
    return data


class OpenAICompatiblePolisher:
    async def polish(self, article: Article, style: str) -> PolishedContent:
        if not settings.llm_configured:
            raise PolishFailed("未配置 LLM_API_KEY")

        source = {
            "title": article.title,
            "summary": article.summary,
            "body_html": article.body_html,
            "author": article.author,
            "source_url": article.source_url,
            "style": style,
        }
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(
                    f"{settings.llm_api_base_url.rstrip('/')}/chat/completions",
                    headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                    json={
                        "model": settings.llm_model,
                        "temperature": 0.4,
                        "messages": [
                            {"role": "system", "content": SYSTEM_PROMPT},
                            {
                                "role": "user",
                                "content": "请处理以下 JSON 素材：\n"
                                + json.dumps(source, ensure_ascii=False),
                            },
                        ],
                    },
                )
                response.raise_for_status()
                payload = response.json()
                content = payload["choices"][0]["message"]["content"]
        except (httpx.HTTPError, KeyError, IndexError, TypeError, ValueError) as exc:
            raise PolishFailed("LLM 服务调用失败，请检查配置或稍后重试") from exc

        data = _parse_json(content)
        return PolishedContent(
            title=data["title"],
            summary=data["summary"],
            body_html=bleach.clean(
                data["body_html"],
                tags=[
                    "p",
                    "h2",
                    "h3",
                    "strong",
                    "blockquote",
                    "ul",
                    "ol",
                    "li",
                    "a",
                ],
                attributes={"a": ["href"]},
                protocols=["http", "https"],
                strip=True,
            ),
        )
