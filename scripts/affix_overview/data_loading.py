from __future__ import annotations

import json
import re
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Mapping

from .constants import (
    AFFIX_DATA_PATH,
    FIELD_VALUE_ATTRIBUTES,
    HERO_TAG_LABELS,
    HERO_TAG_LABELS_EN,
    LIB_AFFX_HEADER_PATH,
    LIB_AFFX_SOURCE_PATH,
    RARITY_ALIASES,
    RARITY_ORDER,
)
from .dynamic_values import DynamicBaseValue, DynamicValueResolver
from .icon_names import icon_file_name
from .markup import convert_storm_markup
from .models import AchievementRecord, AffixCondition, AffixRecord, DifficultyRecord


def load_strings(path: Path) -> dict[str, str]:
    strings: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        strings[key.strip()] = value
    return strings


def load_mod_version(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    match = re.search(r'const string libAffx_version = "([^"]+)";', text)
    if match is None:
        raise RuntimeError(f"Unable to find libAffx_version in {path}")
    return match.group(1)


def load_dynamic_value_overrides(
    path: Path, inline_overrides: list[str]
) -> dict[str, float]:
    overrides: dict[str, float] = {}

    if path.exists():
        raw_data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw_data, dict):
            raise RuntimeError(f"Expected a JSON object in {path}")
        for ref, value in raw_data.items():
            if not isinstance(ref, str) or not isinstance(value, (int, float)):
                raise RuntimeError(
                    f"Invalid dynamic override entry in {path}: {ref!r}={value!r}"
                )
            overrides[ref] = float(value)

    for override in inline_overrides:
        if "=" not in override:
            raise RuntimeError(
                f"Dynamic override must use REF=VALUE syntax: {override!r}"
            )
        ref, value_text = override.rsplit("=", 1)
        ref = ref.strip()
        if not ref:
            raise RuntimeError(f"Dynamic override is missing a ref: {override!r}")
        try:
            overrides[ref] = float(value_text.strip())
        except ValueError as exc:
            raise RuntimeError(
                f"Dynamic override value must be numeric: {override!r}"
            ) from exc

    return overrides


def load_dynamic_base_values(path: Path) -> dict[str, DynamicBaseValue]:
    raw_data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")
    base_values = {}
    for ref, entry in raw_data.items():
        if (
            not isinstance(entry, dict)
            or not isinstance(entry.get("value"), (int, float))
            or isinstance(entry["value"], bool)
            or not isinstance(entry.get("note"), str)
            or not entry["note"].strip()
            or not isinstance(entry.get("source"), str)
            or not entry["source"].strip()
        ):
            raise RuntimeError(f"Invalid dynamic base value in {path}: {ref!r}={entry!r}")
        base_values[ref] = DynamicBaseValue(
            value=float(entry["value"]), note=entry["note"], source=entry["source"]
        )
    return base_values


def load_name_overrides(path: Path, *, label: str) -> dict[str, str]:
    if not path.exists():
        return {}

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")

    overrides: dict[str, str] = {}
    for raw_key, display_name in raw_data.items():
        if not isinstance(raw_key, str) or not isinstance(display_name, str):
            raise RuntimeError(
                f"Invalid {label} override entry in {path}: "
                f"{raw_key!r}={display_name!r}"
            )
        overrides[raw_key] = display_name

    return overrides


def load_hero_name_overrides(path: Path) -> dict[str, str]:
    return load_name_overrides(path, label="hero name")


def load_map_name_overrides(path: Path) -> dict[str, str]:
    return load_name_overrides(path, label="map name")


def load_hidden_affix_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()

    raw_data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw_data, dict):
        raise RuntimeError(f"Expected a JSON object in {path}")

    hidden_affixes = raw_data.get("hidden_affixes", [])
    if not isinstance(hidden_affixes, list) or not all(
        isinstance(affix_id, str) for affix_id in hidden_affixes
    ):
        raise RuntimeError(
            f"Expected {path} to define hidden_affixes as a list of affix ids"
        )

    return {affix_id.strip() for affix_id in hidden_affixes if affix_id.strip()}


def load_version_changes(path: Path) -> dict[str, dict[str, list[str]]]:
    """读「本版本新增/修改」清单。

    返回 {affix_id: {"status": "added"|"modified", "fields": [...]}}。
    文件缺失或格式不对时返回空 dict —— 标记是增强功能，
    不能因为它坏了就让整个图鉴生成失败。
    """
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}

    result: dict[str, dict[str, list[str]]] = {}
    for affix_id in raw.get("added", []) or []:
        if isinstance(affix_id, str) and affix_id.strip():
            result[affix_id.strip()] = {"status": "added", "fields": []}
    modified = raw.get("modified", {}) or {}
    if isinstance(modified, dict):
        for affix_id, fields in modified.items():
            if not isinstance(affix_id, str) or not affix_id.strip():
                continue
            clean = [f for f in fields if isinstance(f, str)] if isinstance(fields, list) else []
            # added 与 modified 同时命中时，以 added 为准（对玩家更醒目）
            if affix_id.strip() in result:
                continue
            result[affix_id.strip()] = {"status": "modified", "fields": clean}
    return result


def load_version_labels(path: Path) -> tuple[str, str]:
    """返回 (对比基准版本, 当前版本)，缺失时 ("", "")。"""
    if not path.exists():
        return "", ""
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "", ""
    if not isinstance(raw, dict):
        return "", ""
    return (
        str(raw.get("baseline_version", "") or ""),
        str(raw.get("version", "") or ""),
    )


def extract_function_body(path: Path, signature: str) -> str:
    text = path.read_text(encoding="utf-8")
    start = text.find(signature)
    if start == -1:
        raise RuntimeError(f"Unable to find {signature} in {path}")

    brace_start = text.find("{", start)
    if brace_start == -1:
        raise RuntimeError(f"Unable to find opening brace for {signature} in {path}")

    depth = 0
    for index in range(brace_start, len(text)):
        char = text[index]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[brace_start + 1 : index]

    raise RuntimeError(f"Unable to find closing brace for {signature} in {path}")


def load_difficulties(
    strings: dict[str, str],
    resolver: DynamicValueResolver,
    strings_en: dict[str, str] | None = None,
) -> list[DifficultyRecord]:
    en_strings: Mapping[str, str] = strings_en or {}
    signatures = (
        "string libAffx_GetDifficultyLabel(int difficulty)",
        "string libAffx_GetDifficulty()",
    )
    body = ""
    for signature in signatures:
        try:
            body = extract_function_body(LIB_AFFX_SOURCE_PATH, signature)
            break
        except RuntimeError:
            continue
    if not body:
        raise RuntimeError(
            f"Unable to extract a difficulty label function from {LIB_AFFX_SOURCE_PATH}"
        )

    matches = re.findall(
        r"(?:libAffx_)?difficulty\s*==\s*([A-Za-z_]\w*|\d+)\s*\)\s*\{\s*"
        r'return\s+" \(([^"\r\n]+)\)";',
        body,
        flags=re.MULTILINE,
    )
    if not matches:
        raise RuntimeError(
            f"Unable to extract difficulty values from {LIB_AFFX_SOURCE_PATH}"
        )

    integer_constants = {
        name: int(value)
        for name, value in re.findall(
            r"\bconst\s+int\s+([A-Za-z_]\w*)\s*=\s*(\d+)\s*;",
            LIB_AFFX_HEADER_PATH.read_text(encoding="utf-8"),
        )
    }
    name_key_by_value = {
        value: key for key, value in strings.items() if key.startswith("Button/Name/")
    }
    # ★ 汉化补丁：原实现拿 galaxy 里的英文 label 去反查 strings 的**值**，
    #   这只在读 enUS 时成立——读 zhCN 时英文 label 匹配不到中文值，
    #   导致 difficulty 的 name/tooltip 全空（页面显示「未找到本地化说明」）。
    #   改为：按 key 后缀（DifficultyNormal 等，英文稳定）直接定位，再取本地化值。
    difficulties: list[DifficultyRecord] = []
    for value_expression, label in matches:
        if value_expression.isdigit():
            difficulty_value = int(value_expression)
        elif value_expression in integer_constants:
            difficulty_value = integer_constants[value_expression]
        else:
            raise RuntimeError(
                f"Unable to resolve difficulty value {value_expression!r} "
                f"from {LIB_AFFX_HEADER_PATH}"
            )
        # label 形如 "Normal"（正则已剥掉括号），拼出稳定的英文 key 后缀
        suffix = label.strip()
        localized_name_key = f"Affix/Name/Difficulty{suffix}"
        if localized_name_key not in strings:
            # 回退：旧逻辑（Button/Name/ 反查）
            localized_name_key = name_key_by_value.get(label, "")
        localized_tooltip_key = (
            localized_name_key.replace("Affix/Name/", "Affix/Tooltip/")
            if localized_name_key
            else ""
        )
        tooltip = strings.get(localized_tooltip_key, "")
        tooltip_html, tooltip_plain, _tooltip_footnotes = convert_storm_markup(
            tooltip, resolver
        )
        # ★ 英文原文（语言切换用）：key 后缀是英文，直接在 enUS 表里查
        suffix = label.strip()
        en_name_key = f"Affix/Name/Difficulty{suffix}"
        en_tooltip_key = f"Affix/Tooltip/Difficulty{suffix}"
        name_en = en_strings.get(en_name_key, "")
        tooltip_en = en_strings.get(en_tooltip_key, "")
        tooltip_html_en = (
            convert_storm_markup(tooltip_en, resolver)[0] if tooltip_en else tooltip_html
        )
        difficulties.append(
            DifficultyRecord(
                difficulty_value=difficulty_value,
                # ★ 用本地化名字覆盖 galaxy 里的英文 label
                label=strings.get(localized_name_key, label),
                localized_name_key=localized_name_key,
                localized_tooltip_key=localized_tooltip_key,
                tooltip_html=tooltip_html,
                tooltip_plain=tooltip_plain,
                name_en=name_en or label,
                tooltip_html_en=tooltip_html_en,
            )
        )

    return sorted(difficulties, key=lambda item: item.difficulty_value)


def load_achievements(
    strings: Mapping[str, str],
    output_dir: Path,
    resolver: DynamicValueResolver,
    strings_en: Mapping[str, str] | None = None,
) -> list[AchievementRecord]:
    achievement_icon_dir = output_dir / "icons" / "achievements"
    placeholder_url = "icons/affix_icon_question_mark.png"
    achievements: list[AchievementRecord] = []
    en_strings: Mapping[str, str] = strings_en or {}

    for name_key, name in strings.items():
        if not name_key.startswith("Achievement/Name/"):
            continue

        achievement_id = name_key.removeprefix("Achievement/Name/")
        tooltip = strings.get(f"Achievement/Tooltip/{achievement_id}")
        if tooltip is None:
            continue

        tooltip_html, tooltip_plain, _tooltip_footnotes = convert_storm_markup(
            tooltip, resolver
        )
        # ★ 英文原文（语言切换用），缺失回落中文
        name_en = en_strings.get(name_key, "") or name
        tooltip_en = en_strings.get(f"Achievement/Tooltip/{achievement_id}", "")
        tooltip_html_en = (
            convert_storm_markup(tooltip_en, resolver)[0] if tooltip_en else tooltip_html
        )
        icon_name = icon_file_name(f"{achievement_id}.dds")
        uses_placeholder = not (achievement_icon_dir / icon_name).exists()
        icon_url = (
            placeholder_url
            if uses_placeholder
            else f"icons/achievements/{icon_name}"
        )
        achievements.append(
            AchievementRecord(
                achievement_id=achievement_id,
                name=name,
                tooltip_html=tooltip_html,
                tooltip_plain=tooltip_plain,
                icon_url=icon_url,
                uses_placeholder=uses_placeholder,
                name_en=name_en,
                tooltip_html_en=tooltip_html_en,
            )
        )

    return achievements


def field_child_value(child: ET.Element) -> str:
    if child.tag == "User":
        return child.attrib.get("Instance", "")
    for attr_name in FIELD_VALUE_ATTRIBUTES:
        if attr_name in child.attrib:
            return child.attrib[attr_name]
    return ""


def instance_fields(instance: ET.Element | None) -> dict[str, str]:
    values: dict[str, str] = {}
    if instance is None:
        return values
    for child in instance:
        field = child.find("Field")
        if field is None or "Index" in field.attrib:
            continue
        field_id = field.attrib.get("Id")
        if not field_id:
            continue
        values[field_id] = field_child_value(child)
    return values


def instance_field_lists(instance: ET.Element | None) -> dict[str, list[str]]:
    values: dict[str, list[str]] = {}
    if instance is None:
        return values
    for child in instance:
        field = child.find("Field")
        if field is None:
            continue
        field_id = field.attrib.get("Id")
        if not field_id:
            continue
        values.setdefault(field_id, []).append(field_child_value(child))
    return values


def is_affix_enabled(fields: dict[str, str]) -> bool:
    enabled_value = fields.get("Enabled", "1").strip()
    return enabled_value not in {"", "0"}


def is_ignored_for_stats(fields: dict[str, str]) -> bool:
    """IgnoredForStats=true 的条目不是玩家可选内容，不该出现在图鉴。

    典型是 3 个难度条目（普通/英雄/神话）。它们 Curse=1，若不过滤就会
    混进「诅咒」列表 —— 但难度本身已有独立视图展示，且这几条的tooltip
    描述的是难度规则，不是诅咒效果。

    🔴 **不能用 NoRoll 判据**：10 条神话诅咒（Sabotage/Citadel/Bleeding…）
    也带 NoRoll=1，但它们是正规游戏内容，必须显示。

    历史上 overview_config.json 曾写死 DifficultyEasy/DifficultyNormal/
    DifficultyHard，但上游 v0.17.x 已把 id 改成
    DifficultyNormal/DifficultyHeroic/DifficultyMythic，导致两个难度漏过滤。
    改用字段判定后，上游再改命名也不会失效。
    """
    value = fields.get("IgnoredForStats", "").strip()
    return value not in {"", "0"}


def parse_int_field(
    raw_value: str | None, *, default: int = 0, empty_value: int = 0
) -> int:
    if raw_value is None:
        return default
    stripped = raw_value.strip()
    if not stripped:
        return empty_value
    try:
        return int(stripped)
    except ValueError as exc:
        raise RuntimeError(f"Expected integer field value, got {raw_value!r}") from exc


def normalize_affix_rarity(raw_rarity: str | None) -> str:
    if raw_rarity is None:
        return "Common"

    stripped = raw_rarity.strip()
    if not stripped:
        return "Common"

    normalized = RARITY_ALIASES.get(stripped.casefold())
    if normalized is not None:
        return normalized

    condensed = re.sub(r"[\s_-]+", "", stripped.casefold())
    normalized = RARITY_ALIASES.get(condensed)
    if normalized is not None:
        return normalized

    return stripped


def affix_is_curse(fields: Mapping[str, str]) -> bool:
    return parse_int_field(fields.get("Curse"), default=0, empty_value=0) > 0


def resolve_icon_url(
    icon_path: str,
    icon_dir: Path,
    cache: dict[str, tuple[str, bool]],
) -> tuple[str, bool]:
    if icon_path in cache:
        return cache[icon_path]

    icon_name = icon_file_name(icon_path)
    if icon_name and (icon_dir / icon_name).exists():
        cache[icon_path] = (f"icons/{icon_name}", False)
    else:
        placeholder_name = "affix_icon_question_mark.png"
        if not (icon_dir / placeholder_name).exists():
            raise RuntimeError(
                f"Icon not found for {icon_path!r} and placeholder {placeholder_name!r} is missing"
            )
        cache[icon_path] = (f"icons/{placeholder_name}", True)
    return cache[icon_path]


def split_semicolon_tags(raw_tags: str) -> list[str]:
    return [tag for tag in (part.strip() for part in raw_tags.split(";")) if tag]


def resolve_affix_name(affix_id: str, strings: Mapping[str, str]) -> str:
    return strings.get(f"Affix/Name/{affix_id}", affix_id)


def resolve_display_name(raw_name: str, overrides: Mapping[str, str]) -> str:
    return overrides.get(raw_name, raw_name)


def append_condition(
    conditions: list[AffixCondition],
    *,
    key: str,
    label: str,
    value: str,
    raw_values: list[str] | None = None,
) -> None:
    search_parts = [label, value]
    if raw_values:
        search_parts.extend(raw_values)
    conditions.append(
        AffixCondition(
            key=key,
            label=label,
            value=value,
            search_text=" ".join(part for part in search_parts if part),
        )
    )


def format_level_condition(min_level: int, max_level: int, lang: str = "zh") -> str:
    # ★ 生成中文文本，render_affixes.render_condition_sentence_html 的分支判断与之配套
    # ★ 2026-04-04 补英文分支：原先只有中文，导致英文段落出现「Appears at 最高 26 级」
    if lang == "en":
        if min_level > 0 and max_level > 0:
            if min_level == max_level:
                return f"level {min_level} only"
            return f"levels {min_level}-{max_level}"
        if min_level > 0:
            return f"level {min_level}+"
        if max_level > 0:
            return f"up to level {max_level}"
        return ""
    if min_level > 0 and max_level > 0:
        if min_level == max_level:
            return f"仅 {min_level} 级"
        return f"{min_level}-{max_level} 级"
    if min_level > 0:
        return f"{min_level} 级以上"
    if max_level > 0:
        return f"最高 {max_level} 级"
    return ""


def build_affix_conditions(
    fields: Mapping[str, str],
    field_lists: Mapping[str, list[str]],
    strings: Mapping[str, str],
    hero_name_overrides: Mapping[str, str],
    map_name_overrides: Mapping[str, str],
    lang: str = "zh",
) -> tuple[list[AffixCondition], str, bool]:
    # ★ lang 决定标签与等级条件用哪套语言（2026-10-04 新增）。
    #   调用方必须为英文侧传入**英文**映射表，否则英文段落会混入中文。
    tag_labels = HERO_TAG_LABELS if lang == "zh" else HERO_TAG_LABELS_EN
    conditions: list[AffixCondition] = []
    hero_specific_raw = fields.get("HeroSpecific", "").strip()
    hero_specific = ""
    has_hero_condition = False

    if hero_specific_raw:
        hero_specific = resolve_display_name(hero_specific_raw, hero_name_overrides)
        append_condition(
            conditions,
            key="hero-specific",
            label="Hero",
            value=f"{hero_specific} only",
            raw_values=[hero_specific_raw, hero_specific],
        )
        has_hero_condition = True
    else:
        hero_tags = split_semicolon_tags(fields.get("HeroTags", ""))
        if hero_tags:
            has_hero_condition = True
            for hero_tag in hero_tags:
                append_condition(
                    conditions,
                    key="hero-tag",
                    label="Heroes",
                    value=tag_labels.get(hero_tag, hero_tag),
                    raw_values=[hero_tag],
                )

        # 同MapsExcluded：按显示名去重，防上游列表出现仅大小写不同的重复项
        excluded_heroes = []
        seen_heroes: set[str] = set()
        for hero_id in field_lists.get("HeroesExcluded", []):
            if not hero_id.strip():
                continue
            display = resolve_display_name(hero_id, hero_name_overrides)
            if display in seen_heroes:
                continue
            seen_heroes.add(display)
            excluded_heroes.append(display)
        if excluded_heroes:
            has_hero_condition = True
            append_condition(
                conditions,
                key="heroes-excluded",
                label="Excludes Heroes",
                value=", ".join(excluded_heroes),
                raw_values=excluded_heroes,
            )

    map_specific_raw = fields.get("MapSpecific", "").strip()
    if map_specific_raw:
        map_name = resolve_display_name(map_specific_raw, map_name_overrides)
        append_condition(
            conditions,
            key="map-specific",
            label="Map",
            value=f"{map_name} only",
            raw_values=[map_specific_raw, map_name],
        )
    else:
        # ★ 去重（2026-10-04）：上游 AffixData.xml 里同一列表可能同时出现
        #   `TowersOfDoom` 与 `TowersofDoom`（仅 o 大小写不同，语义同一张图），
        #   映射成中文后会出现「毁灭之塔, 毁灭之塔」。这里按**映射后的显示名**去重。
        excluded_maps = []
        seen_maps: set[str] = set()
        for map_id in field_lists.get("MapsExcluded", []):
            if not map_id.strip():
                continue
            display = resolve_display_name(map_id, map_name_overrides)
            if display in seen_maps:
                continue
            seen_maps.add(display)
            excluded_maps.append(display)
        if excluded_maps:
            append_condition(
                conditions,
                key="maps-excluded",
                label="Excludes Maps",
                value=", ".join(excluded_maps),
                raw_values=excluded_maps,
            )

    required_affixes = [
        resolve_affix_name(required_affix, strings)
        for required_affix in field_lists.get("AffixesRequired", [])
        if required_affix.strip() and required_affix != "[Default]"
    ]
    if required_affixes:
        append_condition(
            conditions,
            key="affixes-required",
            label="Requires Affixes",
            value=", ".join(required_affixes),
            raw_values=required_affixes,
        )

    excluded_affixes = [
        resolve_affix_name(excluded_affix, strings)
        for excluded_affix in field_lists.get("AffixesExcluded", [])
        if excluded_affix.strip() and excluded_affix != "[Default]"
    ]
    if excluded_affixes:
        append_condition(
            conditions,
            key="affixes-excluded",
            label="Excludes Affixes",
            value=", ".join(excluded_affixes),
            raw_values=excluded_affixes,
        )

    required_talents = [
        talent_id for talent_id in field_lists.get("TalentsRequired", []) if talent_id
    ]
    if required_talents:
        append_condition(
            conditions,
            key="talents-required",
            label="Requires Talents",
            value=", ".join(required_talents),
            raw_values=required_talents,
        )

    level_condition = format_level_condition(
        parse_int_field(fields.get("LevelMin"), default=0, empty_value=0),
        parse_int_field(fields.get("LevelMax"), default=0, empty_value=0),
        lang,
    )
    if level_condition:
        append_condition(
            conditions,
            key="level-range",
            label="Levels",
            value=level_condition,
        )

    return conditions, hero_specific, has_hero_condition


def load_affixes(
    strings: dict[str, str],
    output_dir: Path,
    resolver: DynamicValueResolver,
    hero_name_overrides: Mapping[str, str],
    map_name_overrides: Mapping[str, str],
    strings_en: dict[str, str] | None = None,
    hero_name_overrides_en: Mapping[str, str] | None = None,
    map_name_overrides_en: Mapping[str, str] | None = None,
) -> list[AffixRecord]:
    tree = ET.parse(AFFIX_DATA_PATH)
    affix_user = tree.find(".//CUser[@id='Affix']")
    if affix_user is None:
        raise RuntimeError(f"Unable to find Affix definitions in {AFFIX_DATA_PATH}")

    icon_dir = output_dir / "icons"
    # ★ 英文原文（双语切换用）；缺任一项时英文回落到中文
    en_strings: Mapping[str, str] = strings_en or {}
    en_hero_names: Mapping[str, str] = hero_name_overrides_en or {}
    # ★ 2026-10-04 修复：英文侧原先误传中文地图表，导致英文段落出现「毁灭之塔」等中文。
    #   英文地图表缺失时回落中文表（宁可中文也别空），正常情况下该文件总是存在。
    en_map_names: Mapping[str, str] = map_name_overrides_en or map_name_overrides

    default_instance = affix_user.find("./Instances[@Id='[Default]']")
    default_fields = (
        instance_fields(default_instance) if default_instance is not None else {}
    )
    icon_cache: dict[str, tuple[str, bool]] = {}
    affixes: list[AffixRecord] = []

    for instance in affix_user.findall("./Instances"):
        affix_id = instance.attrib.get("Id", "")
        if not affix_id or affix_id == "[Default]":
            continue

        fields = {**default_fields, **instance_fields(instance)}
        field_lists = instance_field_lists(instance)
        if not is_affix_enabled(fields):
            continue
        if is_ignored_for_stats(fields):
            continue

        name_key = f"Affix/Name/{affix_id}"
        tooltip_key = f"Affix/Tooltip/{affix_id}"
        # ★ 2026-10-10修复：中文缺 key 时整个恩赐被跳过 → 新恩赐/新诅咒完全不进图鉴。
        #   改为中文缺失时回落到英文（英文也缺才跳过），保证图鉴始终收录 mod 里定义的条目。
        name = strings.get(name_key)
        tooltip = strings.get(tooltip_key)
        if name is None:
            name = en_strings.get(name_key, "")
        if tooltip is None:
            tooltip = en_strings.get(tooltip_key, "")
        if not name or not tooltip:
            continue

        tooltip_html, tooltip_plain, tooltip_footnotes = convert_storm_markup(
            tooltip, resolver
        )
        icon_path = fields.get("Icon", default_fields.get("Icon", ""))
        icon_name = icon_file_name(icon_path)
        icon_url, uses_placeholder = resolve_icon_url(
            icon_path,
            icon_dir,
            icon_cache,
        )
        max_stacks = parse_int_field(fields.get("Max"), default=1, empty_value=0)
        negative = affix_is_curse(fields)
        rarity = normalize_affix_rarity(fields.get("Rarity"))
        conditions, hero_specific, has_hero_condition = build_affix_conditions(
            fields,
            field_lists,
            strings,
            hero_name_overrides,
            map_name_overrides,
            "zh",
        )

        # ★ 英文版（供语言切换）；任何一项缺失就整体回落到中文，保证不出现半中半英
        name_en = en_strings.get(name_key, "")
        tooltip_en = en_strings.get(tooltip_key, "")
        conditions_en: list[AffixCondition] = []
        hero_specific_en = ""
        if name_en and tooltip_en:
            tooltip_html_en, _, _ = convert_storm_markup(tooltip_en, resolver)
            conditions_en, hero_specific_en, _ = build_affix_conditions(
                fields,
                field_lists,
                en_strings,
                en_hero_names,
                en_map_names,
                "en",
            )
        else:
            name_en = name
            tooltip_html_en = tooltip_html
            conditions_en = conditions
            hero_specific_en = hero_specific

        affixes.append(
            AffixRecord(
                affix_id=affix_id,
                name=name,
                tooltip_html=tooltip_html,
                tooltip_plain=tooltip_plain,
                tooltip_footnotes=tooltip_footnotes,
                rarity=rarity,
                max_stacks=max_stacks,
                icon_name=icon_name,
                icon_url=icon_url,
                negative=negative,
                hero_specific=hero_specific,
                has_hero_condition=has_hero_condition,
                conditions=conditions,
                uses_placeholder=uses_placeholder,
                name_en=name_en,
                tooltip_html_en=tooltip_html_en,
                hero_specific_en=hero_specific_en,
                conditions_en=conditions_en,
            )
        )

    return sorted(
        affixes,
        key=lambda item: (
            item.negative,
            (
                RARITY_ORDER.index(item.rarity)
                if item.rarity in RARITY_ORDER
                else len(RARITY_ORDER)
            ),
            item.name.lower(),
            item.affix_id.lower(),
        ),
    )
