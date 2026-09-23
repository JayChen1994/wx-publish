import pytest

from app.infrastructure.crawler.html_page import CrawlBlocked, HtmlArticleCrawler

WECHAT_HTML = """
<html><head><title>备用标题</title></head><body>
<h1 id="activity-name">减脂期如何安排训练</h1>
<div id="js_name">健身笔记</div>
<div id="js_content">
  <p>先把热量缺口控制在合理区间。</p>
  <h2>训练安排</h2>
  <p>每周三次力量训练，两次有氧。</p>
  <script>var x = 1;</script>
</div>
<div>阅读 10万+ 点赞 2300</div>
</body></html>
"""

LOGIN_WALL_HTML = "<html><body><div>请登录后查看</div></body></html>"


def test_parses_wechat_article_structure() -> None:
    item = HtmlArticleCrawler()._parse("https://mp.weixin.qq.com/s/abc", WECHAT_HTML)

    assert item.title == "减脂期如何安排训练"
    assert item.author == "健身笔记"
    assert "<h2>训练安排</h2>" in item.body_html
    assert "var x = 1" not in item.body_html
    assert "阅读 10万" in item.metrics


def test_keeps_wechat_images_from_data_src() -> None:
    html = """
    <html><body>
    <h1 id="activity-name">标题</h1>
    <div id="js_name">作者</div>
    <div id="js_content">
      <p>正文</p>
      <img data-src="https://mmbiz.qpic.cn/demo.jpg" src="" />
    </div>
    </body></html>
    """
    item = HtmlArticleCrawler()._parse("https://mp.weixin.qq.com/s/abc", html)
    assert 'src="https://mmbiz.qpic.cn/demo.jpg"' in item.body_html


def test_rejects_page_without_extractable_body() -> None:
    with pytest.raises(CrawlBlocked):
        HtmlArticleCrawler()._parse("https://example.com/a", LOGIN_WALL_HTML)


def test_collects_only_same_host_links() -> None:
    html = """
    <a href="/article/1">一</a>
    <a href="https://www.toutiao.com/article/2">二</a>
    <a href="https://other.com/x">外站</a>
    """
    links = HtmlArticleCrawler()._collect_links("https://www.toutiao.com/hot", html)

    assert links == [
        "https://www.toutiao.com/article/1",
        "https://www.toutiao.com/article/2",
    ]
