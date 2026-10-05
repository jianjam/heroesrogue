from __future__ import annotations

import html
import re

from .constants import STORM_COLORS
from .dynamic_values import DynamicValueResolver
from .models import TooltipFootnote


def normalize_color(value: str) -> str | None:
    if value in STORM_COLORS:
        return STORM_COLORS[value]
    cleaned = value.lstrip("#")
    if re.fullmatch(r"[0-9a-fA-F]{6}", cleaned):
        return f"#{cleaned}"
    return None


def format_dynamic_value(value: float, precision: int | None) -> str:
    if precision is not None:
        return f"{value:.{precision}f}"
    if value.is_integer():
        return str(int(value))
    return f"{value:.4f}".rstrip("0").rstrip(".")


def format_dynamic_variant_footnote(
    ref: str, resolver: DynamicValueResolver
) -> TooltipFootnote | None:
    galaxy_var_match = re.fullmatch(r"\$GalaxyVar:([^$]+)\$", ref)
    if galaxy_var_match is None:
        return None

    variant_group = resolver.resolve_galaxy_var_variants(galaxy_var_match.group(1))
    if variant_group is None or not variant_group.variants:
        return None

    sentences: list[str] = []
    for variant in sorted(
        variant_group.variants,
        key=lambda item: (-item.value, tuple(resolver.resolve_hero_name(hero) for hero in item.heroes)),
    ):
        heroes_text = ", ".join(
            resolver.resolve_hero_name(hero_id) for hero_id in variant.heroes
        )
        sentences.append(
            f"对 {format_dynamic_value(variant.value, None)} 英雄降为：{heroes_text}。"
        )
    return TooltipFootnote(marker="*", text=" ".join(sentences))


def next_footnote_marker(existing_count: int) -> str:
    return "*" * (existing_count + 1)


def convert_storm_markup(
    text: str, resolver: DynamicValueResolver
) -> tuple[str, str, list[TooltipFootnote]]:
    plain_parts: list[str] = []
    html_parts: list[str] = []
    footnotes: list[TooltipFootnote] = []
    footnote_markers: dict[str, str] = {}
    cursor = 0

    def append_text(chunk: str) -> None:
        if not chunk:
            return
        plain_parts.append(chunk)
        html_parts.append(html.escape(chunk))

    for match in re.finditer(r"<[^>]+>", text):
        append_text(text[cursor : match.start()])
        tag = match.group(0)
        cursor = match.end()

        if tag in {"<n/>", "</n>"}:
            plain_parts.append("\n")
            html_parts.append("<br>")
            continue

        if tag.startswith("<c "):
            color_match = re.search(r'val="([^"]+)"', tag)
            color = normalize_color(color_match.group(1)) if color_match else None
            if color:
                html_parts.append(f'<span style="color: {html.escape(color)}">')
            else:
                html_parts.append("<span>")
            continue

        if tag == "</c>":
            html_parts.append("</span>")
            continue

        if tag.startswith("<img "):
            if "StormTalentInTextQuestIcon" in tag:
                plain_parts.append("[Quest] ")
                html_parts.append(
                    '<span class="storm-inline-icon" aria-hidden="true">◆</span>'
                )
            continue

        if tag.startswith("<d "):
            ref_match = re.search(r'ref="([^"]+)"', tag)
            ref = ref_match.group(1) if ref_match else "Dynamic game value"
            precision_match = re.search(r'precision="(\d+)"', tag)
            precision = int(precision_match.group(1)) if precision_match else None
            resolved_value = resolver.resolve_ref(ref)
            if resolved_value is None:
                plain_parts.append("[dynamic]")
                html_parts.append(
                    f'<span class="dynamic-value" title="{html.escape(ref)}">[dynamic]</span>'
                )
            else:
                formatted_value = format_dynamic_value(resolved_value, precision)
                variant_footnote = format_dynamic_variant_footnote(ref, resolver)
                base_value_note = resolver.resolve_base_value_note(ref)
                if base_value_note is not None:
                    variant_footnote = TooltipFootnote(marker="*", text=base_value_note)
                markers: list[str] = []
                if variant_footnote is not None:
                    marker = footnote_markers.get(variant_footnote.text)
                    if marker is None:
                        marker = next_footnote_marker(len(footnotes))
                        footnote_markers[variant_footnote.text] = marker
                        footnotes.append(
                            TooltipFootnote(marker=marker, text=variant_footnote.text)
                        )
                    markers.append(marker)
                marker_suffix = "".join(markers)
                plain_parts.append(f"{formatted_value}{marker_suffix}")
                html_parts.append(
                    html.escape(formatted_value)
                    + "".join(
                        f'<sup class="dynamic-footnote-marker">{html.escape(marker)}</sup>'
                        for marker in markers
                    )
                )
            continue

    append_text(text[cursor:])

    html_text = "".join(html_parts)
    html_text = re.sub(r"(?:<br>\s*){3,}", "<br><br>", html_text)
    plain_text = "".join(plain_parts)
    plain_text = re.sub(r"\n{3,}", "\n\n", plain_text)
    plain_text = re.sub(r"[ \t]+", " ", plain_text).strip()
    return html_text, plain_text, footnotes
