from __future__ import annotations

import html
import re

from .models import AffixRecord


def render_footer_highlight(value: str) -> str:
    return f'<span class="footer-highlight">{html.escape(value)}</span>'


def render_stackability_html(affix: AffixRecord, lang: str = "zh") -> str:
    if lang == "en":
        if affix.max_stacks == 0:
            return "Stacks infinitely."
        if affix.max_stacks == 1:
            return "Doesn't stack."
        return f"Stacks up to {render_footer_highlight(str(affix.max_stacks))}."
    if affix.max_stacks == 0:
        return "可无限叠加。"
    if affix.max_stacks == 1:
        return "不可叠加。"
    return f"最多叠加 {render_footer_highlight(str(affix.max_stacks))} 层。"


def render_mythic_order_html(affix: AffixRecord, lang: str = "zh") -> str:
    if affix.rarity != "Mythic":
        return ""

    match = re.fullmatch(r"Mythic(\d+)", affix.affix_id)
    if match is None:
        return ""

    if lang == "en":
        return f"Mythic {render_footer_highlight(match.group(1))}."
    return f"神话序号 {render_footer_highlight(match.group(1))}。"


def render_condition_sentence_html(
    key: str, value: str, lang: str = "zh"
) -> str:
    if lang == "en":
        highlighted_value = render_footer_highlight(value)
        if key == "hero-specific":
            hero_name = value[:-5] if value.endswith(" only") else value
            return f"Appears for {render_footer_highlight(hero_name)} only."
        if key == "hero-tag":
            return f"Appears for {highlighted_value}."
        if key == "heroes-excluded":
            return f"Does not appear for {highlighted_value}."
        if key == "map-specific":
            map_name = value[:-5] if value.endswith(" only") else value
            return f"Appears on {render_footer_highlight(map_name)} only."
        if key == "maps-excluded":
            return f"Does not appear on {highlighted_value}."
        if key == "affixes-required":
            return f"Requires {highlighted_value}."
        if key == "affixes-excluded":
            return f"Cannot appear with {highlighted_value}."
        if key == "talents-required":
            return f"Requires talents {highlighted_value}."
        if key == "level-range":
            # ★ data_loading.format_level_condition 的英文产出有四种形态，
            #   这里按前缀识别。原先只认 "up to " / " only"，
            #   导致 `levels 1-4` / `level 5+` 掉进兜底分支，
            #   把中文「1-4 级」原样高亮输出（英文段混入中文）。
            #   注意：value 已是英文，此处只做句式组装，不再翻译。
            lower_value = value.lower()
            if lower_value.startswith("up to "):
                return f"Appears {render_footer_highlight(lower_value)} only."
            if lower_value.startswith("levels "):
                return f"Appears at {render_footer_highlight(lower_value)} only."
            if lower_value.endswith("+"):
                return f"Appears at {render_footer_highlight(lower_value[:-1])} and above only."
            if lower_value.endswith(" only"):
                return f"Appears at {highlighted_value}."
            return f"Appears at {highlighted_value} only."
        return render_footer_highlight(
            value if value.endswith(".") else f"{value}."
        )

    # ★ 注意：value 是生成器内部构造的英文中间态（data_loading.py 里拼的 "xxx only"），
    #   这里只汉化最终显示文本，不动内部判断所需的英文后缀。
    highlighted_value = render_footer_highlight(value)
    if key == "hero-specific":
        hero_name = value[:-5] if value.endswith(" only") else value
        return f"仅对 {render_footer_highlight(hero_name)} 生效。"
    if key == "hero-tag":
        return f"生效英雄：{highlighted_value}。"
    if key == "heroes-excluded":
        return f"对 {highlighted_value} 不生效。"
    if key == "map-specific":
        map_name = value[:-5] if value.endswith(" only") else value
        return f"仅在 {render_footer_highlight(map_name)} 出现。"
    if key == "maps-excluded":
        return f"不在 {highlighted_value} 出现。"
    if key == "affixes-required":
        return f"需要 {highlighted_value}。"
    if key == "affixes-excluded":
        return f"不能与 {highlighted_value} 同时出现。"
    if key == "talents-required":
        return f"需要天赋 {highlighted_value}。"
    if key == "level-range":
        # ★ 与 data_loading.format_level_condition 产出的中文文本配套
        if value.startswith("最高 "):
            return f"仅在 {highlighted_value} 出现。"
        if value.endswith(" 级"):
            return f"仅在 {highlighted_value} 出现。"
        return f"出现在 {highlighted_value}。"
    return render_footer_highlight(value if value.endswith(".") else f"{value}.")


def render_footer_summary_html(affix: AffixRecord, lang: str = "zh") -> str:
    conditions = affix.conditions if lang == "zh" else (affix.conditions_en or [])
    parts: list[str] = []
    mythic_order_html = render_mythic_order_html(affix, lang)
    if mythic_order_html:
        parts.append(mythic_order_html)
    parts.append(render_stackability_html(affix, lang))
    parts.extend(
        render_condition_sentence_html(condition.key, condition.value, lang)
        for condition in conditions
    )
    return " ".join(parts)


def render_footer_footnote_text_html(text: str, lang: str = "zh") -> str:
    # Only split on sentence-ending periods so hero names like D.Va and E.T.C.
    # remain intact inside highlighted footnotes.
    sentences = [
        match.group(0).strip()
        for match in re.finditer(r".+?(?:\.(?=\s|$)|$)", text)
        if match.group(0).strip()
    ]
    if not sentences:
        return html.escape(text)

    rendered_sentences: list[str] = []
    for sentence in sentences:
        if lang == "en":
            # 英文原文是 "Reduced to X for Y."，只需给两个值上高亮
            match = re.fullmatch(r"Reduced to (.+?) for (.+)\.", sentence)
            if match is None:
                rendered_sentences.append(html.escape(sentence))
                continue
            reduced_value, heroes = match.groups()
            rendered_sentences.append(
                f"Reduced to {render_footer_highlight(reduced_value)} "
                f"for {render_footer_highlight(heroes)}."
            )
            continue
        # ★ 与 markup.py 中生成的中文句式保持一致：
        #   f"对 {value} 英雄降为：{heroes}。"
        match = re.fullmatch(r"对 (.+?) 英雄降为：(.+)。", sentence)
        if match is None:
            rendered_sentences.append(html.escape(sentence))
            continue
        reduced_value, heroes = match.groups()
        rendered_sentences.append(
            f"对 {render_footer_highlight(reduced_value)} 英雄降为：{render_footer_highlight(heroes)}。"
        )
    return " ".join(rendered_sentences)


def render_footer_footnotes_html(affix: AffixRecord, lang: str = "zh") -> str:
    footnotes = affix.tooltip_footnotes
    if not footnotes:
        return ""

    items = []
    for footnote in footnotes:
        items.append(
            f'<li><span class="footer-footnote-marker">{html.escape(footnote.marker)}</span> {render_footer_footnote_text_html(footnote.text, lang)}</li>'
        )
    return f'<ul class="footer-footnotes">{"".join(items)}</ul>'

