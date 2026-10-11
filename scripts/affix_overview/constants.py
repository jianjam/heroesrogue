from __future__ import annotations

from pathlib import Path


def _find_repo_root() -> Path:
    """从本文件位置向上搜索仓库根（以 mods/HeroesRogue.StormMod 为标志物）。

    不要写死 parents[N] —— 生成器目录一旦在仓库内挪位置（.workbuddy/ → scripts/）
    层级就会变，写死的数字会静默指向错误路径。用标志物搜索更耐改动。
    """
    for parent in Path(__file__).resolve().parents:
        if (parent / "mods" / "HeroesRogue.StormMod").is_dir():
            return parent
    raise RuntimeError(
        "Unable to locate repository root: no 'mods/HeroesRogue.StormMod' found "
        f"in any parent of {Path(__file__).resolve()}"
    )


ROOT = _find_repo_root()
PACKAGE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = PACKAGE_DIR / "config"
MOD_ROOT = ROOT / "mods" / "HeroesRogue.StormMod"
TEXTURES_DIR = MOD_ROOT / "Base.StormAssets" / "Assets" / "Textures"
ACHIEVEMENT_TEXTURES_DIR = TEXTURES_DIR / "Achievements"
AFFIX_DATA_PATH = MOD_ROOT / "Base.StormData" / "GameData" / "AffixData.xml"
LIB_AFFX_SOURCE_PATH = MOD_ROOT / "Base.StormData" / "LibAffx.galaxy"
LIB_AFFX_HEADER_PATH = MOD_ROOT / "Base.StormData" / "LibAffx_h.galaxy"
AFFIX_TRIGGERS_PATH = MOD_ROOT / "Base.StormData" / "AffixTriggers.galaxy"
GAME_DATA_DIR = MOD_ROOT / "Base.StormData" / "GameData"
# ★ 汉化关键：读 zhCN 而非 enUS（key 与 enUS 一一对应）
STRINGS_PATH = MOD_ROOT / "zhCN.StormData" / "LocalizedData" / "GameStrings.txt"
# ★ 仅用于取**英文名**做排序键，保证与英文站顺序完全一致（不参与任何显示）
ENUS_STRINGS_PATH = MOD_ROOT / "enUS.StormData" / "LocalizedData" / "GameStrings.txt"
DYNAMIC_OVERRIDES_PATH = CONFIG_DIR / "dynamic_overrides.json"
DYNAMIC_BASE_VALUES_PATH = CONFIG_DIR / "dynamic_base_values.json"
HERO_NAME_OVERRIDES_PATH = CONFIG_DIR / "hero_names.json"
MAP_NAME_OVERRIDES_PATH = CONFIG_DIR / "map_names.json"
# ★ 英文侧地图名（2026-10-04 补）：原先英文条件复用中文表 → 英文段落里出现「毁灭之塔」等中文
MAP_NAME_OVERRIDES_EN_PATH = CONFIG_DIR / "map_names_en.json"
AFFIX_OVERVIEW_CONFIG_PATH = CONFIG_DIR / "overview_config.json"
# ★ 「本版本新增/修改」清单。由 scripts/classify_changes.py 对比上游 tag 自动生成，
#   不要手改。缺失时图鉴只是不显示标记，功能不受影响。
VERSION_CHANGES_PATH = CONFIG_DIR / "version_changes.json"

RARITY_ORDER = [
    "Starter",
    "Common",
    "Uncommon",
    "Rare",
    "Epic",
    "Legendary",
    "Milestone",
    "Mythic",
    "Challenge",
]
# ★ 汉化：仅改「显示名」。RARITY_ALIASES / RARITY_ORDER / RARITY_COLORS 的 key
#   必须保持英文——它们用于匹配 mod 源数据里的原始字符串，改了会匹配不到。
RARITY_DISPLAY_NAMES = {
    "Starter": "起始",
    "Common": "普通",
    "Uncommon": "优秀",
    "Rare": "稀有",
    "Epic": "史诗",
    "Legendary": "传说",
    "Milestone": "里程碑",
    "Mythic": "神话",
    "Challenge": "挑战",
}
# ★ 英文显示名（语言切换用）。key 必须与 RARITY_DISPLAY_NAMES 一致。
RARITY_DISPLAY_NAMES_EN = {
    "Starter": "Starter",
    "Common": "Common",
    "Uncommon": "Uncommon",
    "Rare": "Rare",
    "Epic": "Epic",
    "Legendary": "Legendary",
    "Milestone": "Milestone",
    "Mythic": "Mythic",
    "Challenge": "Challenge",
}
RARITY_ALIASES = {
    "starter": "Starter",
    "common": "Common",
    "uncommon": "Uncommon",
    "rare": "Rare",
    "epic": "Epic",
    "legendary": "Legendary",
    "milestone": "Milestone",
    "mythic": "Mythic",
    "mythiccurse": "Mythic",
    "mythic curse": "Mythic",
    "mythic_curse": "Mythic",
    "mythic-curse": "Mythic",
    "challenge": "Challenge",
}
RARITY_COLORS = {
    "Starter": "#e6cc80",
    "Common": "#f2f5f8",
    "Uncommon": "#3de26d",
    "Rare": "#4f95ff",
    "Epic": "#d26dff",
    "Legendary": "#ff9d3a",
    "Milestone": "#01ffff",
    "Mythic": "#d86caf",
    "Challenge": "#e05a28",
}
STORM_COLORS = {
    "#TooltipNumbers": "#ffd96a",
    "#TooltipQuest": "#99d0ff",
}
FIELD_VALUE_ATTRIBUTES = ("String", "Int", "value", "Value")
# key 必须保持英文（用于匹配 mod 源数据），只汉化右侧显示文本
# ★ 右侧不带「仅」前缀：render_affixes 的 hero-tag 分支统一组装成「仅对 X 生效。」
HERO_TAG_LABELS = {
    "mana": "法力英雄",
    "!mana": "非法力英雄",
    "melee": "近战英雄",
    "!melee": "非近战英雄",
    "ranged": "远程英雄",
    "!ranged": "非远程英雄",
    "all": "所有英雄",
    "!all": "无英雄",
    "starter": "起始英雄",
    "!starter": "非起始英雄",
    # ★ 2026-10-11 补：上游 AffixData.xml 的 SlowWalk 用 `mount` 限定
    #   「仅对能骑乘的英雄生效」（判定见 LibAffx.galaxy libAffx_AffixSetHeroUsesMount）。
    #   原先漏了这条映射 → 图鉴直接漏出英文 "生效英雄：mount。"
    "mount": "可骑乘英雄",
    "!mount": "不可骑乘英雄",
}
# ★ 英文侧标签（2026-10-04 补）：原先英文条件也复用上面的中文表，
#   导致图鉴英文段落里出现「仅非起始英雄」等中文。
# ★ 2026-10-11：与中文表对齐去掉 "only" 后缀（hero-tag 英文分支同样统一组装），
#   并补上漏掉的 mount / !mount。
HERO_TAG_LABELS_EN = {
    "mana": "Mana heroes",
    "!mana": "Non-Mana heroes",
    "melee": "Melee heroes",
    "!melee": "Non-Melee heroes",
    "ranged": "Ranged heroes",
    "!ranged": "Non-Ranged heroes",
    "all": "All heroes",
    "!all": "No heroes",
    "starter": "Starter heroes",
    "!starter": "Non-Starter heroes",
    "mount": "Mount-capable heroes",
    "!mount": "Heroes without a mount",
}
GITHUB_URL = "https://github.com/sobbyellow/heroesrogue"
NAV_ITEMS = [
    ("index.html", "恩赐", "boons"),
    ("curses.html", "诅咒", "curses"),
    ("difficulties.html", "难度", "difficulties"),
    ("achievements.html", "成就", "achievements"),
]
FOOTER_NOTE = (
    "本图鉴由程序自动生成，可能存在错误。"
    "Heroes Rogue 为玩家自制项目，与暴雪娱乐无关，亦未获得其认可。"
    "本模组在本地运行，不与暴雪服务器交互。"
    "所有原始游戏素材、角色及知识产权均归暴雪娱乐所有。"
)
