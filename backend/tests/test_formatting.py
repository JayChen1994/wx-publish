from app.domain.formatting import normalize_body, plain_summary
from app.infrastructure.sanitize import drop_dangerous_blocks, sanitize_wechat_html


def test_plain_text_becomes_paragraphs_and_headings() -> None:
    pasted = "减脂三原则\n\n先把热量缺口控制在合理区间，不要一上来就断碳。\n训练安排\n每周三次力量训练。"

    html = normalize_body(pasted)

    assert html.startswith("<h2>减脂三原则</h2>")
    assert "<h2>训练安排</h2>" in html
    assert "<p>先把热量缺口控制在合理区间，不要一上来就断碳。</p>" in html


def test_existing_html_is_left_alone() -> None:
    assert normalize_body("<p>已经是 HTML</p>") == "<p>已经是 HTML</p>"


def test_plain_text_is_escaped() -> None:
    assert "&lt;3" in normalize_body("心率区间 <3 分钟内拉不上去，说明强度不够。")


def test_sanitizer_strips_scripts_and_events() -> None:
    dirty = '<p onclick="steal()">正文</p><script>alert(1)</script><iframe src="x"></iframe>'

    clean = sanitize_wechat_html(dirty)

    assert clean == "<p>正文</p>"


def test_sanitizer_keeps_wechat_layout_tags() -> None:
    html = '<h2>小标题</h2><p><strong>重点</strong></p><a href="https://a.com">原文</a>'

    assert sanitize_wechat_html(html) == html


def test_sanitizer_preserves_lazy_loaded_remote_image() -> None:
    html = (
        '<p>图前</p><img data-src="https://mmbiz.qpic.cn/demo.jpg" '
        'onerror="steal()" alt="动作示范"><p>图后</p>'
    )

    clean = sanitize_wechat_html(html)

    assert 'src="https://mmbiz.qpic.cn/demo.jpg"' in clean
    assert 'alt="动作示范"' in clean
    assert "data-src" not in clean
    assert "onerror" not in clean


def test_sanitizer_preserves_localized_media_image() -> None:
    html = (
        '<p>图前</p><img src="/media/3e7f67fc7554f46d.jpg" alt="示范"><p>图后</p>'
    )

    clean = sanitize_wechat_html(html)

    assert 'src="/media/3e7f67fc7554f46d.jpg"' in clean
    assert clean.count("<img") == 1


def test_sanitizer_drops_non_remote_image() -> None:
    html = '<p>正文</p><img src="data:image/png;base64,abc">'

    assert sanitize_wechat_html(html) == "<p>正文</p>"


def test_pasted_text_with_script_still_gets_paragraphs() -> None:
    pasted = "减脂三原则\n先把热量缺口控制在合理区间。<script>alert(1)</script>"

    html = sanitize_wechat_html(normalize_body(drop_dangerous_blocks(pasted)))

    assert html == "<h2>减脂三原则</h2><p>先把热量缺口控制在合理区间。</p>"


def test_summary_strips_tags() -> None:
    assert plain_summary("<h2>标题</h2><p>正文</p>") == "标题正文"
