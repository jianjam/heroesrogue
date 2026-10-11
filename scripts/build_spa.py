"""单文件 SPA 生成器 —— Heroes Rogue 中文图鉴

与旧方案（四个独立 HTML）的根本区别：
  **单页、零跳转**。三个视图（恩赐与诅咒 / 成就 / 难度）在同一文档内切换，
  因此不存在「页面跳转 → 浏览器重置视口 → 视觉跳变」这个根本问题。

用法：
    python build_spa.py --output <dir>            # 需 affix_overview 包可导入
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from affix_overview.constants import (  # noqa: E402
    AFFIX_OVERVIEW_CONFIG_PATH,
    CONFIG_DIR,
    DYNAMIC_BASE_VALUES_PATH,
    ENUS_STRINGS_PATH,
    HERO_NAME_OVERRIDES_PATH,
    MAP_NAME_OVERRIDES_EN_PATH,
    MAP_NAME_OVERRIDES_PATH,
    RARITY_COLORS,
    RARITY_DISPLAY_NAMES,
    RARITY_DISPLAY_NAMES_EN,
    RARITY_ORDER,
    ROOT,
    STRINGS_PATH,
    VERSION_CHANGES_PATH,
)
from affix_overview.data_loading import (  # noqa: E402
    load_achievements,
    load_affixes,
    load_difficulties,
    load_dynamic_base_values,
    load_hero_name_overrides,
    load_hidden_affix_ids,
    load_map_name_overrides,
    load_name_overrides,
    load_strings,
    load_version_changes,
    load_version_labels,
)
from affix_overview.dynamic_values import DynamicValueResolver  # noqa: E402
from affix_overview.render_affixes import (  # noqa: E402
    render_footer_footnotes_html,
    render_footer_summary_html,
)
from affix_overview.render_common import bilingual  # noqa: E402


# ---------------------------------------------------------------- 排序
def _en_name_map() -> dict[str, str]:
    """affix_id -> 英文名，用于排序（与官方站顺序一致）。"""
    names: dict[str, str] = {}
    if not ENUS_STRINGS_PATH.exists():
        return names
    prefix = "Affix/Name/"
    for line in ENUS_STRINGS_PATH.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key.startswith(prefix):
            names[key[len(prefix):]] = value.strip()
    return names


def sort_affixes(affixes):
    """完全按英文名排 —— 不按类型，不按稀有度。

    为什么用英文名而不是中文名：
      ① 中文排序依赖 locale/ICU，各平台各浏览器结果可能不同；
        英文 `lower()` 是纯 ASCII 规则，任何环境结果一致 —— 兼容性最好。
      ② 与原版英文站顺序一致，中英玩家看到同一份内容时相对顺序相同。
      ③ 恩赐与诅咒合并后，若按类型/稀有度排就等于人为分块；
        纯字母序对两类一视同仁，才是真正的「公平」。

    affix_id 仅作重名兜底（目前只有 Slivan / SlivanReward 这一对），
    保证顺序确定、可复现。
    """
    en = _en_name_map()

    def key(item):
        return (
            en.get(item.affix_id, item.name).lower(),
            item.affix_id,
        )

    return sorted(affixes, key=key)


# ---------------------------------------------------------------- 卡片渲染
# 恩赐/诅咒的标识色取自游戏内原文，不自造：
#   Label/Name/PickAffix          = <c val="00ff55">Pick a Boon!</c>
#   Label/Name/PickAffixCurse     = <c val="c52020">Pick a Curse!</c>
BOON_COLOR = "#00ff55"
CURSE_COLOR = "#c52020"

#: 「本版本新增/修改」清单，由 main() 在生成前填入。
#: 形如 {"AffixId": {"status": "added"|"modified", "fields": [...]}}
VERSION_CHANGES: dict[str, dict] = {}
#: (对比基准版本, 当前版本)，用于筛选按钮上的说明文字
VERSION_LABELS: tuple[str, str] = ("", "")


def render_affix_card(affix) -> str:
    rarity_color = RARITY_COLORS.get(affix.rarity, "#c8d4e6")
    rarity_zh = RARITY_DISPLAY_NAMES.get(affix.rarity, affix.rarity)
    rarity_en = RARITY_DISPLAY_NAMES_EN.get(affix.rarity, affix.rarity)
    kind_zh, kind_en = ("诅咒", "Curse") if affix.negative else ("恩赐", "Boon")
    kind_color = CURSE_COLOR if affix.negative else BOON_COLOR

    search_blob = " ".join(
        p for p in [
            affix.affix_id, affix.name, affix.name_en, affix.tooltip_plain,
            rarity_zh, rarity_en, kind_zh, kind_en,
            affix.hero_specific, affix.hero_specific_en,
            *(f.text for f in affix.tooltip_footnotes),
            *(c.search_text for c in affix.conditions),
            *(c.search_text for c in (affix.conditions_en or [])),
        ] if p
    ).lower()

    hero_chip = ""
    if affix.hero_specific:
        hero_chip = (
            f'<span class="chip chip-hero" data-hero="{html.escape(affix.hero_specific)}">'
            + bilingual(html.escape(affix.hero_specific), html.escape(affix.hero_specific_en))
            + "</span>"
        )

    notes_zh = render_footer_summary_html(affix, "zh")
    notes_en = render_footer_summary_html(affix, "en")
    foot_zh = render_footer_footnotes_html(affix, "zh")
    foot_en = render_footer_footnotes_html(affix, "en")

    def ul(block: str, cls: str) -> str:
        if not block:
            return ""
        inner = block[block.index(">") + 1: block.rindex("</ul>")]
        return f'<ul class="{cls}">{inner}</ul>'

    footnotes = ul(foot_zh, "fn fn-zh") + ul(foot_en, "fn fn-en")

    # 「本版本新增/修改」角标：无标记数据时不渲染任何东西（含 data-changed），
    # 保证缺配置时页面结构与从前完全一致。
    change = VERSION_CHANGES.get(affix.affix_id)
    change_badge = ""
    data_changed = ""
    if change:
        is_added = change["status"] == "added"
        data_changed = f' data-changed="{change["status"]}"'
        label_zh, label_en = ("新增", "NEW") if is_added else ("更新", "UPDATED")
        ribbon_cls = "ribbon-new" if is_added else "ribbon-mod"
        change_badge = (
            f'<span class="ribbon {ribbon_cls}">{label_zh}<i>{label_en}</i></span>'
        )

    return f"""
<article class="card{' card-curse' if affix.negative else ''}" data-rarity="{html.escape(affix.rarity)}"
         data-curse="{'true' if affix.negative else 'false'}"
         data-hero-only="{'true' if affix.has_hero_condition else 'false'}"{data_changed}
         style="--kind:{kind_color}"
         data-search="{html.escape(search_blob)}">
  <div class="card-head">
    <img class="card-icon" src="{html.escape(affix.icon_url)}" alt="" width="56" height="56">
    <div class="card-labels">
      <span class="chip chip-kind">{kind_zh}<i>{kind_en}</i></span>
      <span class="chip chip-rarity" style="--rc:{html.escape(rarity_color)}">{html.escape(rarity_zh)}<i>{html.escape(rarity_en)}</i></span>{hero_chip}
    </div>{change_badge}
  </div>
  <h3 class="card-name">{bilingual(html.escape(affix.name), html.escape(affix.name_en))}</h3>
  <div class="card-desc">{bilingual(affix.tooltip_html, affix.tooltip_html_en)}</div>
  <div class="card-notes">{bilingual(notes_zh, notes_en)}{footnotes}</div>
</article>""".strip()


# 难度文案里「神话诅咒 / Mythic Curse」是带 <c val="A84987"> 颜色的，
# 点击后应跳到恩赐与诅咒页并锁定「诅咒 + 神话」。这里只把**已带颜色的**
# 那四个（英文）字换成链接，样式沿用原色，不额外加下划线以外的装饰。
_MYTHIC_COLOR_RE = "|".join(
    re.escape(c) for c in ("#A84987", "#a84987")
)

#: 「神话诅咒」这个词本身也从 GameStrings 取（Label/Name/PickAffixCurseMythic），
#: 不在代码里写死译文 —— 上游改词时不必回来改脚本。
MYTHIC_CURSE_ZH = ""
MYTHIC_CURSE_EN = ""


def _load_mythic_curse_labels(zh: dict[str, str], en: dict[str, str]) -> None:
    global MYTHIC_CURSE_ZH, MYTHIC_CURSE_EN
    key = "Label/Name/PickAffixCurseMythic"
    raw_zh = zh.get(key, "")
    raw_en = en.get(key, "")
    # 值里可能带 <c val="A84987">…</c>，只取标签中间的纯文本
    strip = lambda s: re.sub(r"<[^>]+>", "", s).strip()
    MYTHIC_CURSE_ZH = strip(raw_zh)
    MYTHIC_CURSE_EN = strip(raw_en)


def _linkify_mythic_curse(html_text: str, phrase: str) -> str:
    if not html_text or not phrase:
        return html_text
    pattern = re.compile(
        r'(<span style="color: (?:' + _MYTHIC_COLOR_RE + r')">)'
        + re.escape(html.escape(phrase))
        + r"(</span>)"
    )
    return pattern.sub(
        r'\1<a class="xlink" href="#" data-xkind="curse" data-xrarity="Mythic">'
        + html.escape(phrase)
        + r"</a>\2",
        html_text,
    )



def render_difficulty_card(d) -> str:
    search = " ".join(
        p for p in [d.label, d.name_en, d.tooltip_plain, "difficulty", "难度"] if p
    ).lower()
    zh = d.tooltip_html or "<p>未找到本地化说明。</p>"
    en = d.tooltip_html_en or "<p>No localized tooltip found.</p>"
    zh = _linkify_mythic_curse(zh, MYTHIC_CURSE_ZH)
    en = _linkify_mythic_curse(en, MYTHIC_CURSE_EN)
    return f"""
<article class="card card-diff" data-search="{html.escape(search)}">
  <h3 class="card-name">{bilingual(html.escape(d.label), html.escape(d.name_en))}</h3>
  <div class="card-desc">{bilingual(zh, en)}</div>
</article>""".strip()



def render_achievement_card(a) -> str:
    search = " ".join(
        p for p in [a.achievement_id, a.name, a.name_en, a.tooltip_plain, "成就"] if p
    ).lower()
    zh = a.tooltip_html or "未找到本地化说明。"
    en = a.tooltip_html_en or "No localized tooltip found."
    return f"""
<article class="card card-ach" data-search="{html.escape(search)}">
  <img class="ach-icon" src="{html.escape(a.icon_url)}" alt="" width="44" height="44">
  <div class="ach-body">
    <h3 class="card-name card-name-sm">{bilingual(html.escape(a.name), html.escape(a.name_en))}</h3>
    <div class="card-desc card-desc-sm">{bilingual(zh, en)}</div>
  </div>
</article>""".strip()


# ---------------------------------------------------------------- 页面
STYLES = """
*,*::before,*::after { box-sizing: border-box; }

:root {
  --bg: #0b111c;
  --bg-soft: #111a29;
  --panel: #162133;
  --panel-2: #1b283c;
  --line: #26374d;
  --line-soft: #1f2d40;
  --text: #e6eefb;
  --muted: #93a6c0;
  --accent: #4f81b7;
  --radius: 14px;
  --bar-h: 116px;
}

/* ⚠️ 不要给 html 设 scroll-behavior: smooth ——
   切页时 window.scrollTo(0) 会变成 11 帧渐变滚动，
   6000→0 整屏内容"飞上去"，视觉上就是跳变。实测确认。 */
html { /* scroll-behavior 保持 auto */ }

/* ★ 关键修复：滚动条常驻。
   难度页只有 3 张卡、内容不足一屏 → 不出现垂直滚动条；
   恩赐/诅咒/成就页内容多 → 有滚动条。
   浏览器按 `overflow` 占位，有/无滚动条时**视口宽度差 15px 左右**，
   切换视图时整页内容会横向收缩/扩张 —— 这就是"跳变"的真正来源
   （已用有头浏览器确认：难度页 scrollHeight == innerHeight，hasScrollbar=false）。
   强制 `overflow-y: scroll` 后滚动条槽位永久保留，视口宽度恒定。 */
html { overflow-y: scroll; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 15px/1.6 "Segoe UI", "Microsoft YaHei", "PingFang SC", system-ui, sans-serif;
  -webkit-font-smoothing: antialiased;
}

/* 滚动条槽位样式（Windows 常见宽度 17px，这里统一为 12px 减少占用） */
html { scrollbar-width: thin; }
html::-webkit-scrollbar { width: 12px; height: 12px; }
html::-webkit-scrollbar-track { background: #0e1622; }
html::-webkit-scrollbar-thumb {
  background: #2b3f59; border-radius: 6px;
  border: 2px solid #0e1622; background-clip: padding-box;
}
html::-webkit-scrollbar-thumb:hover { background: #3a5573; background-clip: padding-box; }

.wrap { width: min(1560px, 100% - 32px); margin: 0 auto; }

/* ---------------- 顶部（常驻，不随内容滚动）---------------- */
header.top {
  position: sticky;
  top: 0;
  z-index: 30;
  background: rgba(11,17,28,.94);
  backdrop-filter: blur(8px);
  border-bottom: 1px solid var(--line);
}
.top-in { padding: 12px 0 0; }

.brandrow {
  display: flex; align-items: center; gap: 14px; flex-wrap: wrap;
}
.brand {
  margin: 0; font-size: 1.12rem; font-weight: 700; letter-spacing: .01em;
  white-space: nowrap;
}
.brand small {
  display: block; font-size: .68rem; font-weight: 500; color: var(--muted);
  letter-spacing: .06em; text-transform: uppercase;
}
.spacer { flex: 1 1 auto; }

.search {
  flex: 1 1 260px; max-width: 420px; min-width: 180px;
  padding: 8px 12px; border-radius: 10px;
  border: 1px solid var(--line); background: var(--bg-soft); color: var(--text);
  font: inherit; font-size: .9rem;
}
.search::placeholder { color: #6d829e; }
.search:focus { outline: none; border-color: var(--accent); }

.tabs { display: flex; gap: 4px; margin-top: 10px; flex-wrap: wrap; }
.tab {
  appearance: none; border: 0; background: transparent; color: var(--muted);
  font: inherit; cursor: pointer;
  padding: 7px 13px 8px; border-radius: 10px 10px 0 0;
  border-bottom: 2px solid transparent;
  display: inline-flex; align-items: baseline; gap: 6px; line-height: 1.25;
  /* ⚠️ 显式定死 font-weight：按下时若靠 font-weight 变粗，文字会变宽 →
     按钮变宽 → 右侧所有按钮整体右移（选中一个，其余跟着抖一下）。
     选中态只改颜色，不改字重，并锁 min-width 兜底。 */
  font-weight: 500;
  min-width: 9em;
}
/* 数量 */
.tab i { font-style: normal; font-size: .74rem; color: #61748d; }
/* 英文名 */
.tab u {
  text-decoration: none; font-size: .7rem; color: #55698a;
  letter-spacing: .02em; font-weight: 400;
}
.tab:hover { color: var(--text); background: var(--bg-soft); }
.tab:hover u { color: #7c90ac; }
.tab[aria-selected="true"] {
  color: var(--text); background: var(--panel);
  border-bottom-color: var(--accent);
}
.tab[aria-selected="true"] i { color: var(--muted); }
.tab[aria-selected="true"] u { color: #8fa3bd; }

/* ---------------- 主体 ---------------- */
main { padding: 18px 0 64px; }

/* ---- 视图显隐（只在这里定义一次）---- */
main .view { display: none; }
body[data-view="affixes"] #v-affixes,
body[data-view="achievements"] #v-achievements,
body[data-view="difficulties"] #v-difficulties { display: block; }

.toolbar {
  display: flex; flex-direction: column; gap: 7px;
  margin-bottom: 14px;
  padding-bottom: 12px; border-bottom: 1px solid var(--line-soft);
}
/* 筛选区：非恩赐/诅咒页整块隐藏。
   🔴 原设计用 `visibility:hidden` 保留占位高度，是为防「切页时工具条塌陷导致首卡上移」。
      但现在布局已是 Masonry，切页时页面高度本来就会重算变一变，
      占位反而在成就/难度页顶部留出 ~100px 无意义空白 → 直接 display:none。 */
.filters { display: flex; flex-direction: column; gap: 7px; }
body:not([data-view="affixes"]) .filters { display: none; }

.frow { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; }

.fbtn {
  appearance: none; cursor: pointer; font: inherit; font-size: .82rem;
  padding: 5px 12px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--bg-soft); color: var(--muted);
  /* ⚠️ 选中态绝不能改 font-weight / letter-spacing / padding / border-width：
     任何一项让文字变宽，按钮就会变宽，把右边的按钮整体推走（整排抖动）。
     视觉反馈只走 background + border-color + color。 */
  font-weight: 500;
  /* 宽度锁死（ch 单位随字体自适应，不会因换字体而溢出）：
     两行各自统一min-width，一行按钮左对齐、视觉整齐，
     且按下时宽度必然不变。 */
  min-width: 7.2em;
  text-align: center;
}
.frow:first-child .fbtn[data-flag] { min-width: 11em; }
.fbtn i { font-style: normal; font-size: .7rem; opacity: .65; margin-left: 4px; }
.fbtn:hover { color: var(--text); border-color: #35506f; }
.fbtn[aria-pressed="true"] {
  background: var(--accent); border-color: var(--accent); color: #08111d;
}
.fbtn[aria-pressed="true"] i { opacity: .8; }
.fbtn:disabled { opacity: .32; cursor: not-allowed; }
.fbtn:disabled:hover { color: var(--muted); border-color: var(--line); }

/* 类型筛选（恩赐/诅咒）按下时用各自的游戏内标识色，而不是通用蓝 */
.fbtn[data-kind="boon"][aria-pressed="true"] { background: #00ff55; border-color: #00ff55; }
.fbtn[data-kind="curse"][aria-pressed="true"] { background: #c52020; border-color: #c52020; color: #fff; }
.fbtn[data-kind="curse"][aria-pressed="true"] i { opacity: .85; }

/* 「本次更新」筛选：金色，与飘带贴纸同色 */
.fbtn-change[aria-pressed="true"] { background: #d9a441; border-color: #d9a441; }
.fbtn-change .fbtn-n { font-style: normal; font-size: .66rem; opacity: .7; margin-left: 5px; }
.fbtn-change[aria-pressed="true"] .fbtn-n { opacity: .85; }

.count { color: var(--muted); font-size: .85rem; white-space: nowrap; align-self: flex-end; }
.count b { color: var(--text); }

/* ---------------- 积木式（Masonry）布局 ----------------
   原 grid 布局的问题是：一行里被最高的卡片撑出整行高度，
   同排其他卡片下方留下大片白板（实测占整页 25.7%，139 张卡空 150px+）。
   现在改为「每列独立向下填充」，卡片落到当前最矮的那一列，缝隙自动填满。

   实现：不用 CSS masonry（Chrome 仍是实验特性），改 JS 计算每张卡的
   translateY。列数由 JS 按容器宽度算，与原来 auto-fill 的行为一致。

   ⚠️ **卡片间距不在这里设**：.grid 是 display:block，gap 已不生效，
      实际间距由 JS 的 COL_GAP 常量控制（改那个值即可全局生效）。 */
.grid {
  position: relative;      /* 卡片的定位参照 */
  display: block;          /* 覆盖原来的 grid */
}
.grid > .card {
  position: absolute;
  top: 0; left: 0;
  width: 100%;
  /* ⚠️ 不加 transition：筛选时 411 张卡同时滑动会明显卡顿、且快速连点会晃。
     想要反馈的话可以用 .card 短暂 opacity 过渡（不动 position）。 */
}

.card {
  background: var(--panel); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 16px 17px;
  display: flex; flex-direction: column; gap: 11px;
  /* ⚠️ 不用 content-visibility:auto —— 切换视图时浏览器会重新估算
     离屏卡片高度，导致滚动位置/页面高度瞬间变化（同样是"跳变"）。
     510 张卡在现代浏览器上直接渲染也不卡。 */
}
.card.hidden { display: none; }

/* 恩赐 / 诅咒 用左侧色条 + 边框区分（色值取自游戏内原文） */
.card { border-left: 3px solid var(--kind, #26374d); }
.card.card-curse { background: #1a1620; }
.card.card-curse:hover { border-color: color-mix(in srgb, var(--kind) 45%, var(--line)); }

.chip-kind {
  border-color: color-mix(in srgb, var(--kind) 55%, var(--line));
  color: var(--kind);
}
.chip-kind i { color: var(--muted); }

/* ---------------- 本版本新增 / 修改 标记 ----------------
   🔴 用**右上角斜切飘带贴纸**，不要用 chip（chip 和稀有度/类型标签长得一样，
   混在一起很难发现 —— 用户实测反馈过）。飘带是实心色块 + 撕角，
   与左侧色条（--kind）和 chip 体系完全区分开。 */

/* position:relative 让右上角飘带以卡片头部为定位参照 */
.card-head { position: relative; display: flex; gap: 11px; align-items: flex-start; }

.ribbon {
  position: absolute;
  top: 8px; right: -15px;              /* 右移一半，让撕角压出卡片边缘 */
  z-index: 2;
  padding: 3px 16px 3px 10px;
  font-size: .68rem;
  font-weight: 500;
  line-height: 1.5;
  letter-spacing: .02em;
  white-space: nowrap;
  pointer-events: none;
  border-radius: 3px 0 0 3px;
}
.ribbon i { font-style: normal; font-size: .62rem; opacity: .85; margin-left: 4px; }
/* 撕角：右上角切一个小三角 */
.ribbon::after {
  content: "";
  position: absolute; top: 0; right: 0;
  border-width: 0 0 0 6px;
  border-style: solid;
  border-color: transparent transparent transparent currentColor;
  opacity: .55;
}

/* 新增 = 金色；修改 = 青蓝（与恩赐绿 #00ff55 / 诅咒红 #c52020 都不撞，
   且明度/饱和度与那两个拉开，一眼能分出是「状态标记」不是「类型标记」） */
.ribbon-new  { background: #d9a441; color: #1a1206; }
.ribbon-mod  { background: #2f9bb5; color: #f0feff; }

/* 无标记时右上角留白，避免和飘带位置冲突 */

/* 难度文案里的「神话诅咒」跳转链接：保留原色，只加虚线下划线 */
.xlink {
  color: inherit; cursor: pointer;
  text-decoration: underline dotted; text-underline-offset: 3px;
}
.xlink:hover { text-decoration-style: solid; }

.card-icon {
  width: 56px; height: 56px; flex: 0 0 56px;
  border-radius: 11px; border: 1px solid var(--line);
  background: #0d1522; object-fit: cover;
}
.card-labels { display: flex; flex-wrap: wrap; gap: 5px; min-width: 0; }
/* ⚠️ 只给**有飘带**的卡片留右上角空间。
   用 .card-head:has(.ribbon) 而不是给所有卡片加 padding ——
   否则 391 张无标记卡片右上角都空一块，视觉上像漏排版。
   :has() 现代浏览器全支持；不支持时只是少留空位，不影响可读性。 */
.card-head:has(.ribbon) .card-labels { padding-right: 68px; }

.chip {
  display: inline-flex; align-items: baseline; gap: 5px;
  padding: 2px 8px; border-radius: 999px; font-size: .72rem; line-height: 1.7;
  border: 1px solid var(--line); background: var(--bg-soft); color: var(--muted);
  white-space: nowrap;
}
.chip i { font-style: normal; font-size: .66rem; opacity: .62; }
.chip-rarity { border-color: color-mix(in srgb, var(--rc) 55%, var(--line)); color: var(--rc); }
.chip-rarity i { color: var(--muted); }

.card-name { margin: 0; font-size: 1.02rem; line-height: 1.35; font-weight: 650; }
.card-name-sm { font-size: .93rem; }
.card-name .lang-en { font-size: .78rem; font-weight: 500; }

.lang-zh { display: block; }
.lang-en {
  display: block; margin-top: 1px;
  font-size: .84em; line-height: 1.45; color: var(--muted);
  overflow-wrap: anywhere;
}
.chip .lang-zh, .chip .lang-en { display: inline; margin-top: 0; }

.card-desc { font-size: .88rem; color: #d3e0f2; }
.card-desc p { margin: 0 0 .5em; }
.card-desc p:last-child { margin-bottom: 0; }
.card-desc-sm { font-size: .84rem; }
.card-desc .lang-en { color: var(--muted); }

.card-notes {
  margin-top: auto; padding-top: 9px; border-top: 1px solid var(--line-soft);
  font-size: .78rem; color: var(--muted);
}
.card-notes .lang-en { font-size: .95em; }
.card-notes b, .footer-highlight { color: #cfe0f5; font-weight: 600; }
.fn { margin: 5px 0 0; padding-left: 16px; }
.fn li { margin: 2px 0; }
.fn-zh { display: none; }
body.show-en .fn-zh { display: block; }
body:not(.show-en) .fn-en { display: none; }

/* 难度只有 3 张卡：占 3 列（第四格空着），与恩赐页同为 4 列网格 → 布局行为完全一致 */
.card-diff { min-height: 132px; }
.card-ach { flex-direction: row; gap: 11px; align-items: flex-start; }
.ach-icon {
  width: 44px; height: 44px; flex: 0 0 44px; border-radius: 9px;
  border: 1px solid var(--line); background: #0d1522; object-fit: cover;
}
.ach-body { min-width: 0; display: flex; flex-direction: column; gap: 5px; }

.empty { padding: 48px 0; text-align: center; color: var(--muted); }

footer.foot {
  border-top: 1px solid var(--line-soft); margin-top: 26px;
  padding: 16px 0 30px; color: #6f829c; font-size: .78rem; line-height: 1.7;
}
@media (max-width: 640px) {
  .grid { grid-template-columns: 1fr; }
  .search { max-width: none; }
}
"""


def build_html(affixes, difficulties, achievements, version) -> str:
    import time as _t
    build_stamp = _t.strftime("%Y-%m-%d %H:%M:%S")

    n_boon = sum(1 for a in affixes if not a.negative)
    n_curse = len(affixes) - n_boon

    # ---- 第一行：类型（ALL / 恩赐 / 诅咒，单选互斥）+ 限定（复选，AND）
    # 「本次更新」按钮排在「特定英雄」之后，**同一行**（用户 2026-10-10 定，
    # 不另起一行 —— 单独一行会让筛选区变三行、工具条过高）。
    type_chips = [
        '<button class="fbtn" data-kind="all" aria-pressed="true">全部<i>All</i></button>',
        '<button class="fbtn" data-kind="boon" aria-pressed="false">恩赐<i>Boon</i></button>',
        '<button class="fbtn" data-kind="curse" aria-pressed="false">诅咒<i>Curse</i></button>',
        '<button class="fbtn" data-flag="hero" aria-pressed="false">特定英雄<i>Hero-specific</i></button>',
    ]
    # 无清单时（配置缺失）整段不渲染，避免出现一个点了没反应的按钮。
    if VERSION_CHANGES:
        n_added = sum(1 for v in VERSION_CHANGES.values() if v["status"] == "added")
        n_mod = len(VERSION_CHANGES) - n_added
        base_v, cur_v = VERSION_LABELS
        btn_title = (
            f"只显示 {base_v} → {cur_v} 之间新增或数值/效果有改动的条目"
            if base_v else "只显示本版本新增或数值/效果有改动的条目"
        )
        type_chips.append(
            f'<button class="fbtn fbtn-change" data-flag="changed" aria-pressed="false"'
            f' title="{html.escape(btn_title)}">本次更新<i>Updated</i>'
            f'<em class="fbtn-n">{n_added + n_mod}</em></button>'
        )
    type_html = "\n        ".join(type_chips)

    # ---- 第二行：稀有度（复选，同行 OR；跨行与第一行 AND）
    # Starter 排最左：它本身是稀有度，且内容全是恩赐，玩家一眼能看出来。
    present = {a.rarity for a in affixes}
    ordered = [r for r in RARITY_ORDER if r in present]
    ordered += sorted(present - set(ordered))


    rar_chips = [
        f'<button class="fbtn" data-rarity="{html.escape(r)}" aria-pressed="false">'
        f'{html.escape(RARITY_DISPLAY_NAMES.get(r, r))}'
        f'<i>{html.escape(RARITY_DISPLAY_NAMES_EN.get(r, r))}</i></button>'
        for r in ordered
    ]
    rar_html = "\n        ".join(rar_chips)

    total = len(affixes) + len(difficulties) + len(achievements)

    def cards(items, fn):
        return "\n".join(fn(x) for x in items)

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<!-- 每次生成时带时间戳，配合 build 标记 → 浏览器必定重新拉取，不会用旧缓存 -->
<meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
<meta http-equiv="Pragma" content="no-cache">
<meta http-equiv="Expires" content="0">
<!-- 供页脚/调试显示"本页生成于" -->
<script>window.__BUILT_AT = "{build_stamp}";</script>
<title>Heroes Rogue 图鉴 v{html.escape(version)}</title>
<style>{STYLES}</style>
</head>
<body data-view="affixes">
<header class="top">
  <div class="wrap top-in">
    <div class="brandrow">
      <h1 class="brand">Heroes Rogue 图鉴<small>Compendium · v{html.escape(version)}</small></h1>
      <div class="spacer"></div>
      <input id="q" class="search" type="search"
             placeholder="搜索全部内容（支持中英文）…"
             data-ph-en="Search everything (Chinese &amp; English)…"
             aria-label="搜索 / Search">
    </div>
    <nav class="tabs" role="tablist">
      <button class="tab" role="tab" data-go="affixes" aria-selected="true">恩赐与诅咒<i>{len(affixes)}</i><u>Boons &amp; Curses</u></button>
      <button class="tab" role="tab" data-go="achievements" aria-selected="false">成就<i>{len(achievements)}</i><u>Achievements</u></button>
      <button class="tab" role="tab" data-go="difficulties" aria-selected="false">难度<i>{len(difficulties)}</i><u>Difficulties</u></button>
    </nav>
  </div>
</header>

<main class="wrap">
  <div class="toolbar">
    <div class="filters">
      <div class="frow">
        {type_html}
      </div>
      <div class="frow">
        {rar_html}
      </div>
    </div>
    <div class="count" id="count"></div>
  </div>

  <section class="view" id="v-affixes" role="tabpanel" aria-label="恩赐与诅咒">
    <div class="grid">
{cards(affixes, render_affix_card)}
    </div>
  </section>

  <section class="view" id="v-achievements" role="tabpanel" aria-label="成就">
    <div class="grid">
{cards(achievements, render_achievement_card)}
    </div>
  </section>

  <section class="view" id="v-difficulties" role="tabpanel" aria-label="难度">
    <div class="grid">
{cards(difficulties, render_difficulty_card)}
    </div>
  </section>

  <div class="empty" id="empty" hidden>没有匹配的内容</div>

  <footer class="foot">
    本图鉴由程序自动生成，共 {total} 条，可能存在错误。Heroes Rogue 为玩家自制项目，
    与暴雪娱乐无关，亦未获得其认可。本模组在本地运行，不与暴雪服务器交互。
    所有原始游戏素材、角色及知识产权均归暴雪娱乐所有。
    <br>本站点基于 Errorb0t 的<a href="https://errorb0t.github.io/heroesrogue/">英文恩赐/ 诅咒图鉴</a>汉化改进而成，保留其数据与结构。
    <br>Generated programmatically from the Heroes Rogue mod data (v{html.escape(version)}).
    <br><span style="color:#4a5a72">本页生成于 <span id="built-at">{html.escape(build_stamp)}</span></span>
  </footer>
</main>

<script>
(function () {{
  var body = document.body;
  var q = document.getElementById("q");
  var countEl = document.getElementById("count");
  var emptyEl = document.getElementById("empty");
  var tabs = Array.from(document.querySelectorAll(".tab"));
  var kindBtns = Array.from(document.querySelectorAll(".fbtn[data-kind]"));
  var flagBtns = Array.from(document.querySelectorAll(".fbtn[data-flag]"));
  var rarBtns = Array.from(document.querySelectorAll(".fbtn[data-rarity]"));
  var views = {{
    affixes: document.getElementById("v-affixes"),
    achievements: document.getElementById("v-achievements"),
    difficulties: document.getElementById("v-difficulties")
  }};
  var LABEL = {{ affixes: "项恩赐与诅咒", achievements: "项成就", difficulties: "项难度" }};

  // kind: "all" | "boon" | "curse"（单选互斥）
  // flags: hero（复选，与 kind AND）
  // rarities: Set（复选，同组 OR；与上面两组 AND）
  var state = {{
    view: "affixes", q: "", kind: "all",
    flags: new Set(), rarities: new Set()
  }};
  // 每个视图各自缓存卡片列表，避免每次切页重查 DOM
  var cache = {{}};

  function cardsOf(v) {{
    if (!cache[v]) {{
      cache[v] = Array.from(views[v].querySelectorAll(".card"));
    }}
    return cache[v];
  }}

  function matches(card) {{
    // 第一行：类型（单选）
    if (state.kind === "boon" && card.dataset.curse === "true") return false;
    if (state.kind === "curse" && card.dataset.curse !== "true") return false;
    // 第一行：限定（复选 AND）
    if (state.flags.has("hero") && card.dataset.heroOnly !== "true") return false;
    if (state.flags.has("changed") && !card.dataset.changed) return false;
    // 第二行：评级（含 Starter，复选 OR）
    if (state.rarities.size && !state.rarities.has(card.dataset.rarity)) return false;
    // 关键词（卡片 data-search 已含中英双语的 id/名称/描述/条件/类型）
    if (state.q && card.dataset.search.indexOf(state.q) === -1) return false;
    return true;
  }}

  // ---------------- 积木式排版 ----------------
  // 卡片绝对定位，这里给每张算 translateY：按 DOM 顺序（= 英文名字母序）
  // 把卡丢进「当前最矮的那一列」，缝隙自然被后面的卡填满。
  var COL_MIN = 330;   // 与原 grid 的 minmax 下限一致
  // 🔴 卡片间距只有一个真相来源 = 这个值。CSS 里`.grid` 已改 display:block，
  //    gap 不再由浏览器算，全部由 layout() 手动控制 —— 改这里即可全局生效。
  //    别再去 CSS 里找 gap 改（那里留着旧值只是注释参考，改了没用）。
  var COL_GAP = 20;
  var grids = {{
    affixes: document.querySelector("#v-affixes .grid"),
    achievements: document.querySelector("#v-achievements .grid"),
    difficulties: document.querySelector("#v-difficulties .grid")
  }};

  function layout(v) {{
    var grid = grids[v];
    if (!grid) return;
    var width = grid.clientWidth;
    if (!width) return;                     // 容器还没布局（初始帧）→ 下次再算
    // 列数公式与 auto-fill minmax(330px,1fr) 对齐：能放几列就放几列
    var cols = Math.max(1, Math.floor((width + COL_GAP) / (COL_MIN + COL_GAP)));
    var colW = (width - COL_GAP * (cols - 1)) / cols;
    var heights = new Array(cols).fill(0);

    var list = cardsOf(v);
    for (var i = 0; i < list.length; i++) {{
      var card = list[i];
      if (card.classList.contains("hidden")) continue;
      // 找最矮的列（并列时取最左，保持顺序稳定）
      var k = 0;
      for (var c = 1; c < cols; c++) {{
        if (heights[c] < heights[k] - 0.5) k = c;
      }}
      card.style.width = colW + "px";
      card.style.transform = "translate3d(" + (k * (colW + COL_GAP)) + "px," + heights[k] + "px,0)";
      // ⚠️ 必须先定宽再读高度：宽度变了高度才最终确定，顺序反了会拿到旧高度
      heights[k] += card.offsetHeight + COL_GAP;
    }}
    // 容器高度 = 最长列（去掉末尾多余的 gap）。0 张卡时给0，容器自然收起。
    var tallest = 0;
    for (var c2 = 0; c2 < cols; c2++) {{
      if (heights[c2] - COL_GAP > tallest) tallest = heights[c2] - COL_GAP;
    }}
    grid.style.height = tallest + "px";
  }}

  function layoutAll() {{
    Object.keys(grids).forEach(function (v) {{ layout(v); }});
  }}

  function paint() {{
    var list = cardsOf(state.view);
    var n = 0;
    for (var i = 0; i < list.length; i++) {{
      var ok = matches(list[i]);
      list[i].classList.toggle("hidden", !ok);
      if (ok) n++;
    }}
    countEl.innerHTML = "<b>" + n + "</b> / " + list.length + " " + LABEL[state.view];
    emptyEl.hidden = n !== 0;
    // 筛选后立刻重排 → 满足条件的自动上移、填空隙（用户要的行为）
    layout(state.view);
  }}

  function syncButtons() {{
    kindBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(b.dataset.kind === state.kind));
    }});
    flagBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(state.flags.has(b.dataset.flag)));
    }});
    rarBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(state.rarities.has(b.dataset.rarity)));
    }});
  }}

  function resetAffixFilters() {{
    state.kind = "all";
    state.flags.clear();
    state.rarities.clear();
    syncButtons();
  }}

  function switchView(v) {{
    if (state.view === v) return;
    state.view = v;
    body.dataset.view = v;
    tabs.forEach(function (t) {{
      t.setAttribute("aria-selected", String(t.dataset.go === v));
    }});
    // 离开恩赐/诅咒页时清掉筛选，回来时是干净的默认态
    if (v !== "affixes") resetAffixFilters();
    paint();
    // 🔴 新视图刚从 display:none 变可见，此刻读 clientWidth 可能还是 0，
    //   layout() 会直接 return，导致这次切页排版是空的。
    //   下一帧容器宽度才可用 → 补排一次。
    requestAnimationFrame(function () {{ layout(v); }});
  }}

  tabs.forEach(function (t) {{
    t.addEventListener("click", function () {{
      switchView(t.dataset.go);
      // 切页后回到顶部（同一文档内，无浏览器重置，行为完全可控）
      window.scrollTo({{ top: 0, behavior: "auto" }});
    }});
  }});

  kindBtns.forEach(function (b) {{
    b.addEventListener("click", function () {{
      // 恩赐/诅咒互斥：点谁就切到谁（再点已选中的那个退回全部）。
      // 不做「禁用另一个」—— 禁掉后玩家想换阵营必须先点 ALL，多一步且反直觉。
      state.kind = state.kind === b.dataset.kind && b.dataset.kind !== "all"
        ? "all"
        : b.dataset.kind;
      syncButtons();
      paint();
    }});
  }});

  flagBtns.forEach(function (b) {{
    b.addEventListener("click", function () {{
      var f = b.dataset.flag;
      if (state.flags.has(f)) state.flags.delete(f); else state.flags.add(f);
      syncButtons();
      paint();
    }});
  }});

  rarBtns.forEach(function (b) {{
    b.addEventListener("click", function () {{
      var r = b.dataset.rarity;
      if (state.rarities.has(r)) state.rarities.delete(r); else state.rarities.add(r);
      syncButtons();
      paint();
    }});
  }});

  // 难度页文案里的「神话诅咒」→ 跳到恩赐与诅咒页并锁定「诅咒 + 神话」
  Array.from(document.querySelectorAll(".xlink[data-xkind]")).forEach(function (a) {{
    a.addEventListener("click", function (e) {{
      e.preventDefault();
      state.kind = a.dataset.xkind || "curse";
      state.flags.clear();
      state.rarities.clear();
      if (a.dataset.xrarity) state.rarities.add(a.dataset.xrarity);
      syncButtons();
      switchView("affixes");
      window.scrollTo({{ top: 0, behavior: "auto" }});
    }});
  }});

  var t = null;
  q.addEventListener("input", function () {{
    state.q = q.value.trim().toLowerCase();
    clearTimeout(t);
    t = setTimeout(paint, 90);
  }});

  // 快捷键：1-3 切视图，/ 聚焦搜索
  document.addEventListener("keydown", function (e) {{
    if (e.key === "/" && document.activeElement !== q) {{ e.preventDefault(); q.focus(); return; }}
    if (document.activeElement === q) return;
    var i = ["1", "2", "3"].indexOf(e.key);
    if (i > -1) {{
      switchView(tabs[i].dataset.go);
      window.scrollTo({{ top: 0, behavior: "auto" }});
    }}
  }});

  // 窗口缩放：列数/卡宽/卡高全变，必须重排。用防抖避免拖动时狂算。
  var rt = null;
  window.addEventListener("resize", function () {{
    clearTimeout(rt);
    rt = setTimeout(layoutAll, 120);
  }});

  // 🔴 重排时机一共三处，缺一个就会出现「卡片重叠/错位」：
  //   ① 首次paint() —— 初始布局
  //   ② resize     —— 列数变了
  //   ③ 图片/字体加载完成 —— 卡高会变。achievements/affixes 都有 <img>，
  //      图片没加载完时 offsetHeight 是占位高度，图片加载后卡片会突然变高，
  //      必须在 load 事件后再排一次。
  Array.from(document.images).forEach(function (img) {{
    if (!img.complete) img.addEventListener("load", layoutAll);
    else if (img.naturalWidth === 0) img.addEventListener("error", layoutAll);
  }});
  if (document.fonts && document.fonts.ready) {{
    document.fonts.ready.then(layoutAll);
  }}
  window.addEventListener("load", layoutAll);

  syncButtons();
  paint();
}})();
</script>
</body>
</html>
"""


def main() -> int:
    ap = argparse.ArgumentParser(description="生成 Heroes Rogue 中文图鉴（单文件 SPA）")
    ap.add_argument("--output", required=True, type=Path, help="输出目录")
    ap.add_argument("--version", default="", help="mod 版本号（写入标题）")
    args = ap.parse_args()

    out: Path = args.output
    out.mkdir(parents=True, exist_ok=True)

    version = args.version
    if not version:
        import subprocess

        # mod 目录里没有 modinfo.txt，DocumentInfo 也不含版本号 → 从 Git tag 取。
        # 用 constants.ROOT（已在 constants.py 里算好），不要自己数 parents。
        #
        # ⚠️ 必须用 `--match 'v[0-9]*'` 过滤：本仓库除了上游的 mod 版本 tag，
        # 还有我们自己的分发标签 `installer-v0.1`（打在一路汉化提交上）。
        # 不加过滤时 `git describe` 会选中它（离HEAD 更近），
        # 页面标题就会显示成「vinstaller-v0.1」这种鬼东西。
        root = ROOT
        for cmd in (["git", "describe", "--tags", "--abbrev=0", "--match", "v[0-9]*"],
                    ["git", "rev-parse", "--short", "HEAD"]):
            try:
                proc = subprocess.run(
                    cmd, cwd=root, capture_output=True, text=True, timeout=10
                )
                if proc.returncode == 0 and proc.stdout.strip():
                    version = proc.stdout.strip().lstrip("v")
                    break
            except Exception:
                pass
    version = version or "0.0.0"

    zh = load_strings(STRINGS_PATH)
    en = load_strings(ENUS_STRINGS_PATH) if ENUS_STRINGS_PATH.exists() else {}
    heroes = load_hero_name_overrides(HERO_NAME_OVERRIDES_PATH)
    heroes_en_path = CONFIG_DIR / "hero_names_en.json"
    heroes_en = load_name_overrides(heroes_en_path, label="hero name") if heroes_en_path.exists() else {}
    maps = load_map_name_overrides(MAP_NAME_OVERRIDES_PATH)
    # ★ 2026-10-04 新增：英文侧地图名，供英文段落使用（缺失则回落中文表）
    maps_en = (
        load_map_name_overrides(MAP_NAME_OVERRIDES_EN_PATH)
        if MAP_NAME_OVERRIDES_EN_PATH.exists()
        else maps
    )
    hidden = load_hidden_affix_ids(AFFIX_OVERVIEW_CONFIG_PATH)
    base = load_dynamic_base_values(DYNAMIC_BASE_VALUES_PATH)

    # 「本版本新增/修改」清单：缺失时 VERSION_CHANGES 为空 dict，
    # 卡片不渲染标记、筛选按钮也不出现 —— 缺配置不影响主体功能。
    global VERSION_CHANGES, VERSION_LABELS
    VERSION_CHANGES = load_version_changes(VERSION_CHANGES_PATH)
    VERSION_LABELS = load_version_labels(VERSION_CHANGES_PATH)

    _load_mythic_curse_labels(zh, en)

    resolver = DynamicValueResolver({}, base)
    resolver.set_hero_name_overrides(heroes)

    affixes = load_affixes(zh, out, resolver, heroes, maps, en, heroes_en, maps_en)
    if hidden:
        affixes = [a for a in affixes if a.affix_id not in hidden]

    difficulties = load_difficulties(zh, resolver, en)
    achievements = load_achievements(zh, out, resolver, en)

    affixes = sort_affixes(affixes)

    html_text = build_html(affixes, difficulties, achievements, version)
    target = out / "index.html"
    target.write_text(html_text, encoding="utf-8")

    print(f"Wrote {target}  ({len(html_text) / 1024:.0f} KB)")
    n_boon = sum(1 for a in affixes if not a.negative)
    print(
        f"Affixes {len(affixes)} (Boons {n_boon} / Curses {len(affixes) - n_boon})"
        f" | Difficulties {len(difficulties)} | Achievements {len(achievements)}"
    )
    return 0




if __name__ == "__main__":
    raise SystemExit(main())
