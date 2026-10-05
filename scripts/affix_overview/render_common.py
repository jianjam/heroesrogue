"""双语渲染助手（供 build_spa.py 使用）。

历史背景：这里曾放旧「四页 HTML」方案的整套布局与语言切换代码
（render_page / render_nav / SCROLL_PRESERVE_SCRIPT 等），
已随 SPA 重写全部废弃，现在只保留唯一还被引用的 bilingual()。
"""

from __future__ import annotations


def bilingual(zh_html: str, en_html: str) -> str:
    """输出中英双语内容，**始终同时显示**（不做显示/隐藏切换）。

    排版由页面 CSS 负责：`.lang-zh` 为主行，`.lang-en` 作为副行
    （较小字号 + 弱化颜色）。英侧为空时只留中文。
    """
    if not en_html or en_html == zh_html:
        return f'<span class="lang-zh">{zh_html}</span>'
    return (
        f'<span class="lang-zh">{zh_html}</span>'
        f'<span class="lang-en">{en_html}</span>'
    )
