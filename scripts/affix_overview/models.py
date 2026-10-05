from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AffixCondition:
    key: str
    label: str
    value: str
    search_text: str


@dataclass(frozen=True)
class TooltipFootnote:
    marker: str
    text: str


@dataclass
class AffixRecord:
    affix_id: str
    name: str
    tooltip_html: str
    tooltip_plain: str
    tooltip_footnotes: list[TooltipFootnote]
    rarity: str
    max_stacks: int
    icon_name: str
    icon_url: str
    negative: bool
    hero_specific: str
    has_hero_condition: bool
    conditions: list[AffixCondition]
    uses_placeholder: bool
    # ★ 双语切换用：英文原文（仅在需要时填充，中文版运行时为 None）
    name_en: str = ""
    tooltip_html_en: str = ""
    hero_specific_en: str = ""
    conditions_en: list[AffixCondition] | None = None


@dataclass
class DifficultyRecord:
    difficulty_value: int
    label: str
    localized_name_key: str
    localized_tooltip_key: str
    tooltip_html: str
    tooltip_plain: str
    name_en: str = ""
    tooltip_html_en: str = ""


@dataclass
class AchievementRecord:
    achievement_id: str
    name: str
    tooltip_html: str
    tooltip_plain: str
    icon_url: str
    uses_placeholder: bool
    name_en: str = ""
    tooltip_html_en: str = ""
