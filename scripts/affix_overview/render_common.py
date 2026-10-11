"""双语渲染助手（供 build_spa.py 使用）。

历史背景：这里曾放旧「四页 HTML」方案的整套布局与语言切换代码
（render_page / render_nav / SCROLL_PRESERVE_SCRIPT 等），
已随 SPA 重写全部废弃，现在只保留唯一还被引用的 bilingual()。
"""

from __future__ import annotations


def bilingual(zh_html: str, en_html: str, *, dedupe: bool = False) -> str:
    """输出中英双语内容，**始终同时显示**（不做显示/隐藏切换）。

    排版由页面 CSS 负责：`.lang-zh` 为主行，`.lang-en` 作为副行
    （较小字号 + 弱化颜色）。英侧为空时只留中文。

    🔴 **中英同形时是否补英文行，取决于该处是块级还是行内**（2026-10-11 用户定）：

    - **块级（卡片标题、描述）→ 补。** 音译名两边会长得一模一样
      （`D.Va` / `D.Va`）。早期版本在这里判断 `en_html == zh_html` 就只留中文行，
      后果是成就页 D.Va 那张卡片比同列其他卡片少一行、矮一截，
      Masonry 里表现为「就它凹进去一块」。重复一次文案换整列对齐，划算。

    - **行内（chip 小标签）→ 去重，`dedupe=True`。** chip 是单行 inline 布局，
      补一行会变成「专属 D.Va D.Va」；更麻烦的是**同屏 chip 宽度会参差**
      —— 带英文名的都宽一截，不带的正常，本来就齐的一排被撑歪了。
      而且 chip 的中英是「标签名 + 英文对照」，重复没有信息量。

    ⚠️ 别把这条又简化回「内容相同就省一行」—— 高度一致性是块级排版需求，
    与行内标签的紧凑需求是两回事，一个统一的规则必然顾此失彼。
    """
    if not en_html or (dedupe and en_html == zh_html):
        return f'<span class="lang-zh">{zh_html}</span>'
    return (
        f'<span class="lang-zh">{zh_html}</span>'
        f'<span class="lang-en">{en_html}</span>'
    )
