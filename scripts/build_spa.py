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
        # dedupe=True：chip 是单行 inline 布局，中英同形（如 D.Va）时重复
        # 会变成「专属 D.Va D.Va」，还会把这一排 chip 的宽度撑得参差不齐。
        hero_chip = (
            f'<span class="chip chip-hero" data-hero="{html.escape(affix.hero_specific)}">'
            + bilingual(
                html.escape(affix.hero_specific),
                html.escape(affix.hero_specific_en),
                dedupe=True,
            )
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

    # ---- 筛选维度用的 data 属性（2026-10-11 筛选系统重做新增）----
    # data-stack: 叠加上限。0=无限、1=不可叠加、>=2=有限叠加。
    #   用字符串而不是数字 —— DOM dataset 只有字符串，写 "0" 会被 `if (x)` 判成假。
    stack_kind = "infinite" if affix.max_stacks == 0 else (
        "none" if affix.max_stacks == 1 else "finite"
    )

    # 条件类维度统一从 conditions 的 key 取，不另写映射 ——
    #   条件 key 是数据层唯一的真相来源，加一个条件不用动这里。
    cond_keys = {c.key for c in affix.conditions}
    # 「地图限定」把 map-specific / maps-excluded 合成一类：
    #   玩家关心的是「这条恩赐跟地图有关吗」，不关心是只限还是排除。
    data_cond = (
        f' data-map="{ "1" if ({"map-specific", "maps-excluded"} & cond_keys) else "0" }"'
        f' data-level="{ "1" if "level-range" in cond_keys else "0" }"'
        f' data-req="{ "1" if "affixes-required" in cond_keys else "0" }"'
    )

    return f"""
<article class="card{' card-curse' if affix.negative else ''}" data-rarity="{html.escape(affix.rarity)}"
         data-curse="{'true' if affix.negative else 'false'}"
         data-hero-specific="{'true' if affix.hero_specific else 'false'}"
         data-stack="{stack_kind}"{data_cond}{data_changed}
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

  /* ---- 动效令牌 ----------------------------------------------------
     全站只有这一组曲线/时长。新增动画一律引用它们，不要就地写
     cubic-bezier(...) 或新的毫秒数 —— 分散写出来的曲线必然互相不匹配。
     取值来自 Emil Kowalski 的动画方法论（animate 技能）：
       ease-out 用于「进入/退出」，ease-in-out 用于「在屏幕上移动」，
       颜色/边框这类状态切换用短时长，位移类不给超过 300ms。 */
  --ease-out: cubic-bezier(0.23, 1, 0.32, 1);
  --ease-in-out: cubic-bezier(0.77, 0, 0.175, 1);
  --dur-press: 110ms;      /* 按下反馈：要快到几乎感觉不到，但要有 */
  --dur-state: 150ms;      /* 选中/悬停的颜色与边框切换 */
  --dur-pop:   200ms;      /* 浮层展开 */
  --dur-collapse: 220ms;   /* 「更多条件」折叠区 */
  --dur-card: 130ms;       /* 卡片筛选后淡入 */
  --dur-tab:   250ms;      /* 页签指示条滑动（在屏幕上移动 → ease-in-out） */
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
@media (hover: hover) and (pointer: fine) {
  html::-webkit-scrollbar-thumb:hover { background: #3a5573; background-clip: padding-box; }
}

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

.tabs { display: flex; gap: 4px; margin-top: 10px; flex-wrap: wrap; position: relative; }

/* 页签选中指示条。
   🔴 只动transform，绝不动 width ——
      宽高变化会触发布局，页签切换时整排跟着抖。
      做法：元素本身固定 100px 宽，用 scaleX 缩放到目标宽度，
      translateX 负责位移。两个都是合成器属性，切换零重排。 */
.tab-ind {
  position: absolute; left: 0; bottom: 0;
  width: 100px; height: 2px;
  background: var(--accent); border-radius: 2px;
  transform-origin: left center;
  transform: translateX(var(--tx, 0px)) scaleX(var(--sx, 0));
  transition: transform var(--dur-tab) var(--ease-in-out);
  pointer-events: none;
}

.tab {
  appearance: none; border: 0; background: transparent; color: var(--muted);
  font: inherit; cursor: pointer;
  padding: 7px 13px 8px; border-radius: 10px 10px 0 0;
  display: inline-flex; align-items: baseline; gap: 6px; line-height: 1.25;
  /* ⚠️ 显式定死 font-weight：按下时若靠 font-weight 变粗，文字会变宽 →
     按钮变宽 → 右侧所有按钮整体右移（选中一个，其余跟着抖一下）。
     选中态只改颜色，不改字重，并锁 min-width 兜底。 */
  font-weight: 500;
  min-width: 9em;
  /* 颜色类属性各自具名列出，不要写 transition: all ——
     all 会把上面指示条之外的意外属性也带上，过渡时间不一致时很难排查。 */
  transition: background-color var(--dur-state) var(--ease-out),
              color var(--dur-state) var(--ease-out);
}
/* 🔴 子元素的颜色也必须有各自的过渡 —— `transition` 不会从父元素继承，
      .tab 换了 color / background，内部的<u> 英文名、<i> 数量却瞬间跳色，
      会看到「外框平滑、字突然变」的割裂感。逐个显式列出。 */
/* 数量 */
.tab i {
  font-style: normal; font-size: .74rem; color: #61748d;
  transition: color var(--dur-state) var(--ease-out);
}
/* 英文名 */
.tab u {
  text-decoration: none; font-size: .7rem; color: #55698a;
  letter-spacing: .02em; font-weight: 400;
  transition: color var(--dur-state) var(--ease-out);
}
/* 🔴 hover 一律包在媒体查询里 —— 触屏点一下会**留下** :hover 状态，
      表现为「点了某个按钮之后，它一直保持着高亮」，看着像 bug。
      这是 emilkowalski 审查清单第 8 条（Accessibility）的硬要求。 */
@media (hover: hover) and (pointer: fine) {
  .tab:hover { color: var(--text); background: var(--bg-soft); }
  .tab:hover u { color: #7c90ac; }
}
.tab[aria-selected="true"] { color: var(--text); background: var(--panel); }
.tab[aria-selected="true"] i { color: var(--muted); }
.tab[aria-selected="true"] u { color: #8fa3bd; }

/* ---------------- 主体 ---------------- */
main { padding: 18px 0 64px; }

/* ---- 视图显隐（只在这里定义一次）---- */
main .view { display: none; }
body[data-view="affixes"] #v-affixes,
body[data-view="achievements"] #v-achievements,
body[data-view="difficulties"] #v-difficulties { display: block; }

/* 视图切换：只淡入，不做位移。
   卡片是绝对定位的，任何 transform 都会和 Masonry 写的 translate3d 打架。
   淡入的目的是「整块内容换了一页」的提示，130ms 足够，再长就是拖沓。 */
.view { animation: viewIn var(--dur-card) var(--ease-out) both; }
@keyframes viewIn { from { opacity: 0; } to { opacity: 1; } }

.toolbar {
  display: flex; flex-direction: column; gap: 8px;
  margin-bottom: 14px;
  padding-bottom: 12px; border-bottom: 1px solid var(--line-soft);
}
/* 筛选区：非恩赐/诅咒页整块隐藏。
   🔴 原设计用 `visibility:hidden` 保留占位高度，是为防「切页时工具条塌陷导致首卡上移」。
      但现在布局已是 Masonry，切页时页面高度本来就会重算变一变，
      占位反而在成就/难度页顶部留出 ~100px 无意义空白 → 直接 display:none。 */
.filters { display: flex; flex-direction: column; gap: 8px; }
body:not([data-view="affixes"]) .filters { display: none; }

/* 两行筛选：第一行=类型/英雄/更新，第二行=稀有度 + 更多条件入口 */
.frow { display: flex; align-items: center; gap: 6px 14px; flex-wrap: wrap; }

/* 筛选分组：左标签 + 右按钮组。
   标签用固定宽度，两行之间天然对齐 —— 否则三组的按钮会各自左移，
   视觉上像没排版。 */
.fgroup { display: flex; align-items: center; gap: 8px; min-width: 0; }
.flabel {
  flex: 0 0 auto; font-size: .72rem; color: #7e91ab; letter-spacing: .04em;
  white-space: nowrap; user-select: none;
  /* 标签也有中英两段：中文实心、英文更淡更小 —— 和按钮里的双语同一个层级关系，
     读起来是「同一个词的中英两版」，不是两个并列的词。
     🔴 min-width 是**对齐用的**：四个分组的标签长度差很多
     （类型 2 字 / 稀有度 3 字），不锁宽的话按钮起始位置会参差，
     两行之间更对不齐。宽要够放下最长的「稀有度 RARITY」。 */
  display: inline-flex; align-items: baseline; gap: 4px;
  min-width: 7.2em;
}
.flabel i {
  font-style: normal; font-size: .92em; color: #5b6d86;
  letter-spacing: .01em; text-transform: uppercase;
}
.fbtns { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; min-width: 0; }

/* ---- 筛选按钮 ----
   🔴 选中态绝不能改 font-weight / letter-spacing / padding / border-width / font-size：
      任何一项让文字变宽，按钮就会变宽，把右边的按钮整体推走（整排抖动）。
      视觉反馈只走 background + border-color + color 三项。 */
.fbtn {
  appearance: none; cursor: pointer; font: inherit; font-size: .82rem;
  padding: 5px 11px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--bg-soft); color: var(--muted);
  font-weight: 500;
  min-width: 6.4em; text-align: center;
  display: inline-flex; align-items: baseline; justify-content: center; gap: 5px;
  /* 按下反馈：缩放会连同文字一起缩，所以读起来是「被按下去」而不是「变模糊」。
     110ms —— 再慢就变成明显的拖影，反而像卡顿。 */
  transition: background-color var(--dur-state) var(--ease-out),
              border-color var(--dur-state) var(--ease-out),
              color var(--dur-state) var(--ease-out),
              transform var(--dur-press) var(--ease-out);
}
.fbtn:active { transform: scale(0.96); }
.fbtn i { font-style: normal; font-size: .7rem; opacity: .65; }
.fbtn-n {
  font-style: normal; font-size: .66rem; opacity: .7;
  /*🔴 tabular-nums 必须保留：筛选后计数会变（如 409→323），
     等宽数字保证数字变化时按钮宽度不变，否则整排按钮会横向抖动。 */
  font-variant-numeric: tabular-nums;
  transition: opacity var(--dur-state) var(--ease-out);
}
@media (hover: hover) and (pointer: fine) {
  .fbtn:hover { color: var(--text); border-color: #35506f; }
}
.fbtn[aria-pressed="true"] {
  background: var(--accent); border-color: var(--accent); color: #08111d;
}
.fbtn[aria-pressed="true"] i { opacity: .8; }
.fbtn:disabled { opacity: .32; cursor: not-allowed; }
@media (hover: hover) and (pointer: fine) {
  .fbtn:disabled:hover { color: var(--muted); border-color: var(--line); }
}

/* 单选组（类型 / 英雄限定）：按钮视觉上连成一体，
   强化「这组里只能选一个」的语义 —— 分组本身已经用 label 说明，
   样式再补一层，玩家不必去试就知道不是复选。 */
/* 单选组（类型 / 英雄限定）：按钮视觉上连成一体，
   强化「这组里只能选一个」的语义 —— 分组本身已经用 label 说明，
   样式再补一层，玩家不必去试就知道不是复选。 */
.fgroup[data-single] .fbtns {
  gap: 0; padding: 2px;
  background: var(--bg-soft); border: 1px solid var(--line);
  border-radius: 999px;
  /* 🔴 grid-template-columns: repeat(auto-fit, minmax(0, 1fr))
     让三段**自动等分** —— 按钮文案长度不同（特定 Specific / 通用 General
     差一个字母）时，靠 min-width 猜出来的值必然不准，结果是三段宽窄不一，
     看起来像排版没对齐。等分由容器决定，与内容长度彻底解耦。 */
  display: grid; grid-auto-flow: column; grid-auto-columns: 1fr;
}
.fgroup[data-single] .fbtn {
  border-radius: 999px; border-color: transparent; background: transparent;
  min-width: 0;   /* 交给 grid 等分管，这里再给下限反而会破坏等分 */
  justify-content: center;
}
/* 分段控件里选中态要「填进」容器，所以去掉自身边框，
   否则相邻两段各留 1px 边，选中时宽度会跳。 */
.fgroup[data-single] .fbtn[aria-pressed="true"] {
  border-color: transparent; background: var(--accent); color: #08111d;
}
/* 分段内的按下缩放会露出容器底色，缩小幅度，比散排按钮更收敛 */
.fgroup[data-single] .fbtn:active { transform: scale(0.94); }

/* 类型筛选按下时用各自的游戏内标识色，而不是通用蓝 */
.fgroup[data-single] .fbtn[data-kind="boon"][aria-pressed="true"] {
  background: #00ff55; border-color: transparent; color: #04180b;
}
.fgroup[data-single] .fbtn[data-kind="curse"][aria-pressed="true"] {
  background: #c52020; border-color: transparent; color: #fff;
}
/* 「排除」用中性偏红的描边态：它不是「选中一种类型」，
   而是「反向过滤」，实心红会和诅咒按钮撞色，语义也糊。 */
.fbtn[data-hero-mode="exclude"][aria-pressed="true"] {
  background: transparent; border-color: #b4553f; color: #ffb9a4;
}
.fbtn[data-hero-mode="exclude"][aria-pressed="true"] i { opacity: .8; }

/* 「本次更新」筛选：金色，与飘带贴纸同色 */
.fbtn-change[aria-pressed="true"] { background: #d9a441; border-color: #d9a441; color: #1a1206; }
.fbtn-change[aria-pressed="true"] .fbtn-n { opacity: .85; }

/* 稀有度筛选按下时用**该品级自己的颜色**（--rc 由生成器逐按钮注入，
   与卡片上 chip-rarity 的颜色同源，改 RARITY_COLORS 两边一起变）。
   🔴 文字一律压深：品级色从近白（Common #f2f5f8）到深粉（Mythic #d86caf），
      只有深字能在全部 8 色上保持可读；白字在 Common 上会完全消失。
   规则放在通用选中态之后，靠 specificity 覆盖 --accent 蓝底。 */
.fbtn[data-rarity][aria-pressed="true"] {
  background: var(--rc); border-color: var(--rc); color: #08111d;
}
.fbtn[data-rarity][aria-pressed="true"] .fbtn-n { opacity: .82; }

/* ---- 「更多条件」折叠区 ----
   grid-template-rows: 0fr → 1fr 是纯 CSS 的高度过渡，
   不用 JS 量高度、也不用 max-height 猜数值（那两种都会在内容变化时失准）。 */
.fmore-btn[aria-expanded="true"] { border-color: var(--accent); color: var(--text); }
.fmore-btn .caret {
  display: inline-block; width: 0; height: 0;
  border-left: 4px solid transparent; border-right: 4px solid transparent;
  border-top: 5px solid currentColor;
  transition: transform var(--dur-collapse) var(--ease-out);
}
.fmore-btn[aria-expanded="true"] .caret { transform: rotate(180deg); }
.fmore {
  display: grid; grid-template-rows: 0fr;
  transition: grid-template-rows var(--dur-collapse) var(--ease-out);
}
.fmore[data-open="true"] { grid-template-rows: 1fr; }
.fmore-in { overflow: hidden; min-height: 0; }
.fmore-in > .frow {
  padding-top: 8px; margin-top: 8px; border-top: 1px dashed var(--line-soft);
  opacity: 1; transition: opacity var(--dur-collapse) var(--ease-out);
}
.fmore:not([data-open="true"]) .fmore-in > .frow { opacity: 0; }

/* ---- 窄屏收敛 ----
   🔴 1280px（常见笔记本）下稀有度行会折成两行，把「更多条件」挤到第三行，
      工具条从 116px 涨到 170px，首屏白扔一块。
   做法是**只藏英文小字**：中文标签 + 计数仍全在，筛选能力一点没少，
   换来一行放得下。宽屏（≥1440px）保持双语 —— 那里放得下且英文名有检索价值。
   用媒体查询而不是给每个按钮加类：媒体查询是唯一的正确入口，
   逐个加 class 迟早漏掉一个。 */
@media (max-width: 1439px) {
  /* 稀有度行的英文名最占地方，优先牺牲它 */
  .frow .fgroup > .fbtns > .fbtn > i { display: none; }
  /* 分组标签在窄屏只留中文（英文是同一个词的第二版，不是新信息），
     省下的宽度刚好够稀有度九个按钮排一行。
     🔴 用 `i {display:none}` 而不是整个 `.flabel {display:none}` ——
        后者会让标签整块消失，min-width 失效、按钮起始位置重新参差。 */
  .flabel i { display: none; }
  .flabel { min-width: 3.4em; }
  /* 🔴 「叠加」那组的中文被压到单字（「有 / 无限 / 无」），英文一藏
     「无」就只剩一个字，和「无限」看不出区别 → 给它一个 title 兜底。
     title 不占布局宽度，但悬停/长按仍能读到完整含义。 */
  .fbtn[data-stack="none"] { min-width: 4.6em; }
}

@media (max-width: 720px) {
  /* 再窄就只留类型组的中文，其余靠「更多条件」和搜索 */
  .fbtn { min-width: 0; }
  .fgroup[data-single] .fbtn { min-width: 4.4em; }
  .fbtn-n { display: none; }
}

.count { color: var(--muted); font-size: .85rem; white-space: nowrap; align-self: flex-end; }
.count b { color: var(--text); }
/* 筛选结果变化时数字轻微跳一下，给一个「结果变了」的瞬间反馈。
   纯 transform，不影响旁边任何东西的排布。 */
.count b { display: inline-block; }
.count[data-bump="1"] b { animation: bump 220ms var(--ease-out); }
@keyframes bump {
  0%   { transform: translateY(0); }
  35%  { transform: translateY(-3px); }
  100% { transform: translateY(0); }
}

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
  /* ⚠️ 不加 transform 过渡：筛选时 400+ 张卡同时滑动会明显卡顿、且快速连点会晃。
     transform 是 Masonry 用来定位的唯一手段，动它必然和layout() 打架。
     反馈改用 opacity —— 见下面的 .card.enter。 */
}

.card {
  background: var(--panel); border: 1px solid var(--line);
  /* 🔴 padding 上边距比左右各少 1px —— 上边框是 2px（原本 1px），
     不补回来卡片内容区会整体下移 1px、行距变紧，视觉上卡片显得更挤。 */
  border-radius: var(--radius); padding: 15px 17px;
  display: flex; flex-direction: column; gap: 11px;
  /* ⚠️ 不用 content-visibility:auto —— 切换视图时浏览器会重新估算
     离屏卡片高度，导致滚动位置/页面高度瞬间变化（同样是"跳变"）。
     500 张卡在现代浏览器上直接渲染也不卡。 */
  /* hover 过渡：逐个具名列颜色属性。
     🔴 绝不能写 `transition: all` —— 会把筛选淡入用的 opacity 也带进来，
     两者互相干扰（实测卡片先淡入再跳一下边框）。 */
  transition: border-top-color var(--dur-state) var(--ease-out),
              border-right-color var(--dur-state) var(--ease-out),
              border-bottom-color var(--dur-state) var(--ease-out),
              background-color var(--dur-state) var(--ease-out);
}
.card.hidden { display: none; }

/* 筛选后新出现的卡片淡入。
   🔴 只动 opacity，绝不动 transform/位置：
      卡片位置由 JS 的 translate3d 决定，这里再叠一个位移会和它抢 transform，
      表现为「卡片抖一下再归位」。130ms 够短，不会让人觉得在等。 */
.card.enter { animation: cardIn var(--dur-card) var(--ease-out) both; }

/* 🔴 FLIP **不需要任何 CSS transition** —— 由 WAAPI（Element.animate）驱动。
   这正是它比 transition 强的地方：
     · Animation 对象可 `commitStyles()` 固化中间态 → 打断时从当前位置接管
     · 硬件加速，`fill:'none'` 播完自动失效 → 不需要 class / 定时器 / transitionend
       三套清理机制（前四版正是被这些清理逻辑的时序 bug 反复咬）。
   在这里挂 `transition: transform` 会与 WAAPI 叠加，拖慢所有属性变化。 */
@keyframes cardIn { from { opacity: 0; } to { opacity: 1; } }

/* 恩赐 / 诅咒 用**左上两条**色条区分（色值取自游戏内原文）。
   hover 效果：**外框提亮到中性灰蓝 + 背景微提亮**，色条与边框宽度全程不动。

   🔴 为什么外框必须用**中性色**（不带 hue）：简写 `border-color` 会把四条边
      连同色条一起染成混合色 —— 实测恩赐 #00ff85 被稀释成暗绿、
      诅咒 #c52020 变暗红，hover 后两类几乎分不开，而「一眼分清恩赐还是诅咒」
      正是这个色条存在的唯一理由。逐边上色 + 中性色，两者职责才分得开。
   🔴 为什么必须**逐边写**而不是 `border-color` 简写：简写会把色条也重写掉，
      而色条本来就该是这个颜色，逐边写才看得出「只动另外两边」这个意图。

   ⚠️ 改 `border-width` 会触发布局 —— 实测 409 张里 21 张卡在换行临界点，
      宽度一变内容少 1px → 文字多换一行 → 卡片变高 → Masonry 整列位移（最多 +22px）。
      本版本全程只改颜色，不碰宽度。 */
.card {
  /* 🔴 左 + 上两条同规格色条，构成「L 形」标识。
     两条都是 2px：3px 在密集列表里偏抢眼，2px 已足够一眼分清类型
     （用户 2026-10-11 从 3px 调到 2px）。 */
  border-left: 2px solid var(--kind, #26374d);
  border-top: 2px solid var(--kind, #26374d);
}
.card.card-curse { background: #1a1620; }

@media (hover: hover) and (pointer: fine) {
  .card:hover {
    /* 🔴 只改右 / 下两条 —— 上方已是身份色条，不能动 */
    border-right-color: #3d5573;
    border-bottom-color: #3d5573;
    background: #182337;
  }
  .card.card-curse:hover { background: #1f1a26; }
}

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
  /* 🔴 `text-decoration-style` 不可过渡（浏览器不把它列入可动画属性），
     所以这里过渡的是 text-decoration-color + text-underline-offset ——
     hover 时虚线变实线的观感靠「更深的颜色 + 更近的偏移」来实现，
     视觉上同样是「线变明显了」，但全程平滑。
     ⚠️ hover 必须包在媒体查询里 —— 触屏点一下会触发 :hover，
        造成「点了之后样式变了」的假反馈。 */
  transition: color var(--dur-state) var(--ease-out),
              text-decoration-color var(--dur-state) var(--ease-out);
  text-decoration-color: #4a5c76;
}
@media (hover: hover) and (pointer: fine) {
  .xlink:hover { text-decoration-style: solid; text-decoration-color: #7fb0e8; }
}

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
/* 🔴 成就卡 / 难度卡**没有 `--kind` 变量**（它们不属于恩赐/诅咒分类），
   所以 `.card` 里的 `var(--kind, #26374d)` 会退化成中性灰 ——
   静止时看不出来，但 hover 时「L 形色条」会整条变灰，与恩赐/诅咒卡完全不像一套。
   显式给一个中性色值，让三处视觉一致：色条在、但不带类型 hue。 */
.card-ach, .card-diff { --kind: #3d5573; }
.card-diff { min-height: 132px; }
.card-ach { flex-direction: row; gap: 11px; align-items: flex-start; }
.ach-icon {
  width: 44px; height: 44px; flex: 0 0 44px; border-radius: 9px;
  border: 1px solid var(--line); background: #0d1522; object-fit: cover;
}
.ach-body { min-width: 0; display: flex; flex-direction: column; gap: 5px; }

.empty { padding: 48px 0; text-align: center; color: var(--muted); }
.empty[hidden] { display: none; }
.empty { animation: viewIn var(--dur-card) var(--ease-out) both; }

/* ---- 降低动效偏好 ----
   🔴 这不是「关掉所有动画」，是「保留帮助理解的、去掉纯位移的」：
      折叠区直接展开（不再有高度过渡），指示条直接跳到目标位置（滑动只是装饰）。
   漏掉这一段 = 前庭功能障碍用户每次点筛选都要难受一次。 */
/* 🔴 **reduced-motion = 去掉位移，不是去掉所有动画**
      （emilkowalski 审查清单第 8 条）：前庭功能障碍用户受不了移动，
      但「颜色/透明度过渡」是帮助理解的，必须留着 ——
      全部关掉会让「点了没反应」变得无法感知。
      逐个列清楚，别漏：

      位置类（全关）
        · .tab-ind   页签指示条在屏幕上滑动 —— 位移，最该关
        · .fmore-btn .caret  折叠箭头旋转 —— 纯transform
        · .fmore     折叠区高度过渡 —— grid-template-rows 是布局属性
        · .fbtn:active scale(0.96) —— 按下缩放
      颜色/透明度类（保留，只在需要时给一个极短的淡入）
        · .fbtn / .tab 的 background-color / color —— 留着
        · .card / .xlink 的 border-color / background —— 留着

      ⚠️ 2026-10-11 全量审查时发现漏了 4 处（.card / .xlink / .frow / .card-curse），
         已在下面补齐。 */
@media (prefers-reduced-motion: reduce) {
  /* 位移类：全关 */
  .fbtn:active { transform: none; }
  .tab-ind { transition: none; }
  .fmore-btn .caret { transition: none; }
  .fmore { transition: none; }
  .frow { transition: none; }
  /* 淡入类：改成「不播动画但立刻可见」—— 直接 animation:none 会让
     元素停在 from 的 opacity:0 上（fill: both），必须显式给 opacity:1 */
  .view, .card.enter, .empty, .count[data-bump="1"] b { animation: none; }
  .view, .card.enter, .empty { opacity: 1; }
  .card.enter { opacity: 1; }
  /* 颜色类：**刻意保留**，只去掉 transition 让它瞬时生效 ——
     前庭敏感与颜色过渡无关，全关反而丢失「状态变了」的提示。 */
  .fbtn, .tab, .card, .xlink, .fbtn-n, .tab i, .tab u {
    transition-duration: 1ms;
  }
}

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
    # 🔴 「特定」判的是**专属某个具体英雄**（上游 HeroSpecific 字段），不是
    #   「带任何英雄条件」。两者差14 条：另有 10 条按**英雄类型**限定
    #   （仅法力英雄 / 仅远程 / 可骑乘…）、6 条是**排除某几个英雄**
    #   （不出现于加尔等）—— 它们都与英雄有关，但都不是「专属某人」，
    #   所以归到「排除 Other」那一侧。
    #   判据直接用 `hero_specific` 字段，不要用 `has_hero_condition`
    #   （后者是三者的并集，用它会让「特定」多算 14 条，与文案不符）。
    n_hero_specific = sum(1 for a in affixes if a.hero_specific)
    n_hero_general = len(affixes) - n_hero_specific

    # ---- 常用筛选条件的可选值（供「更多条件」区渲染）
    def has_cond(keys: set[str]) -> int:
        return sum(1 for a in affixes if keys & {c.key for c in a.conditions})

    n_map = sum(
        1 for a in affixes
        if {"map-specific", "maps-excluded"} & {c.key for c in a.conditions}
    )
    n_level = has_cond({"level-range"})
    n_req = has_cond({"affixes-required"})
    n_stack_finite = sum(1 for a in affixes if a.max_stacks > 1)
    n_stack_infinite = sum(1 for a in affixes if a.max_stacks == 0)

    # ---- 第一行：类型（单选互斥）
    type_group = f"""
        <div class="fgroup" data-single role="group" aria-label="类型 / Type">
          <span class="flabel">类型<i>Type</i></span>
          <div class="fbtns">
            <button class="fbtn" type="button" data-kind="all" aria-pressed="true">全部<i>All</i><span class="fbtn-n">{len(affixes)}</span></button>
            <button class="fbtn" type="button" data-kind="boon" aria-pressed="false">恩赐<i>Boon</i><span class="fbtn-n">{n_boon}</span></button>
            <button class="fbtn" type="button" data-kind="curse" aria-pressed="false">诅咒<i>Curse</i><span class="fbtn-n">{n_curse}</span></button>
          </div>
        </div>"""

    # ---- 英雄限定（三态单选）
    # 三个取值是同一维度上互斥的三种状态，所以做成和类型一样的分段控件。
    #
    # 🔴 **英文与上游字段、与原版英文站对齐**：分组标签已经写了「英雄 Hero」，
    #    按钮上只补后半段 —— 视觉上「英雄 Hero」+「特定 Specific」连读就是
    #    `hero-specific`，正是英文原站与AffixData.xml `HeroSpecific` 字段的拼法。
    #    🔴 **两个按钮的英文必须等长且同族**（specific / general）：
    #    长度不一致会让分段控件的三段宽度不等，看起来像排版没对齐；
    #    而且它们必须构成一对反义词，否则玩家学不会这个对应关系。
    #    `general` 与 `specific` 是严格的反义对，且长度相同。
    #
    # 🔴 **三态不能交给搜索框替代**（2026-10-11 用户定的分工）：
    #   搜索是「包含某关键词」，而 specific/general 判的是「是不是专属某个英雄」
    #   这个**反向属性**，搜索框做不到。「是哪个英雄」才归搜索管。
    hero_group = f"""
        <div class="fgroup" data-single role="group" aria-label="英雄限定 / Hero scope">
          <span class="flabel">英雄<i>Hero</i></span>
          <div class="fbtns">
            <button class="fbtn" type="button" data-hero-mode="all" aria-pressed="true">不限<i>All</i></button>
            <button class="fbtn" type="button" data-hero-mode="only" aria-pressed="false">特定<i>Specific</i><span class="fbtn-n">{n_hero_specific}</span></button>
            <button class="fbtn" type="button" data-hero-mode="exclude" aria-pressed="false">通用<i>General</i><span class="fbtn-n">{n_hero_general}</span></button>
          </div>
        </div>"""

    # ---- 「本次更新」：无清单时不渲染，避免出现点了没反应的按钮
    # 🔴 原来这组带一个「更新」分组标签，按钮里又写「本次更新」，
    #    同一句话在屏幕上出现两遍且其中一遍是多余的（2026-10-11 用户去掉标签）。
    #    按钮自带的 `本次更新 / Updated` 已经说清了，标签纯属占地方。
    change_btn = ""
    if VERSION_CHANGES:
        n_added = sum(1 for v in VERSION_CHANGES.values() if v["status"] == "added")
        n_mod = len(VERSION_CHANGES) - n_added
        base_v, cur_v = VERSION_LABELS
        btn_title = (
            f"只显示 {base_v} → {cur_v} 之间新增或数值/效果有改动的条目"
            if base_v else "只显示本版本新增或数值/效果有改动的条目"
        )
        change_btn = f"""
        <div class="fgroup">
          <div class="fbtns">
            <button class="fbtn fbtn-change" type="button" data-flag="changed"
                    aria-pressed="false" title="{html.escape(btn_title)}">本次更新<i>Updated</i><span class="fbtn-n">{n_added + n_mod}</span></button>
          </div>
        </div>"""

    # ---- 第二行：稀有度（复选，同组 OR；跨组 AND）
    # Starter 排最左：它本身是稀有度，且内容全是恩赐，玩家一眼能看出来。
    present = {a.rarity for a in affixes}
    ordered = [r for r in RARITY_ORDER if r in present]
    ordered += sorted(present - set(ordered))
    rarity_counts = {r: sum(1 for a in affixes if a.rarity == r) for r in ordered}

    rar_chips = [
        f'<button class="fbtn" type="button" data-rarity="{html.escape(r)}" aria-pressed="false"'
        f' style="--rc:{html.escape(RARITY_COLORS.get(r, "#c8d4e6"))}">'
        f'{html.escape(RARITY_DISPLAY_NAMES.get(r, r))}'
        f'<i>{html.escape(RARITY_DISPLAY_NAMES_EN.get(r, r))}</i>'
        f'<span class="fbtn-n">{rarity_counts[r]}</span></button>'
        for r in ordered
    ]
    rar_html = "\n            ".join(rar_chips)

    rarity_group = f"""
        <div class="fgroup">
          <span class="flabel">稀有度<i>Rarity</i></span>
          <div class="fbtns">
            {rar_html}
          </div>
        </div>"""

    # ---- 「更多条件」：默认折叠。这些维度命中数少（个位数到几十），
    #   常驻在第一屏既占地方又很少用，所以收起来，需要时一键展开。
    # 🔴 这组**刻意没有分组标签**（2026-10-11 用户去掉）：
    #   按钮自己已经写了「更多条件 / More」，标签是同一句话重复两遍，
    #   而且「条件」这词太泛 —— 上面常驻的「类型 / 英雄 / 稀有度」也是条件。
    #   折叠区里的「叠加上限 / 生效范围」两个标签才是真正有区分度的。
    more_btn = f"""
        <div class="fgroup">
          <div class="fbtns">
            <button class="fbtn fmore-btn" type="button" id="moreOpen"
                    aria-expanded="false" aria-controls="morePanel">
              更多条件<i>More</i><span class="caret" aria-hidden="true"></span>
            </button>
          </div>
        </div>"""

    # 折叠区每一行：左标签 + 按钮组。
    # 🔴 标签也走中英双语（与常驻分组一致）—— 用户要求「尽量每处中英对比」，
    #   否则同一个词在第一行有英文、在折叠区没有，读起来像两套东西。
    more_rows = [
        # 🔴 中文按钮只留核心词（「有限/ 无限 / 无」），「叠加」二字
        #   已经在左侧分组标签上了，重复一遍既占地方又是废话。
        #   英文小字保留完整（Stacked / Infinite / None）—— 英文里
        #   "Finite stack" 这类说法离开标签就不知道在说什么。
        ("叠加", "Stacks", [
            ("stack", "finite", "有限", "Stacked", n_stack_finite, "最多叠加有限层数。"),
            ("stack", "infinite", "无限", "Infinite", n_stack_infinite, "可无限叠加。"),
            ("stack", "none", "无", "None", len(affixes) - n_stack_finite - n_stack_infinite, "不可叠加。"),
        ]),
        ("生效范围", "Scope", [
            ("cond", "map", "限定地图", "Maps", n_map),
            ("cond", "level", "等级限制", "Levels", n_level),
            ("cond", "req", "需搭配恩赐", "Requires", n_req),
        ]),
    ]
    # 元组第五项 n 之后可选第六项 title：给「按钮上被压成单字」的项做兜底说明。
    # 🔴 一律从数据现算，不写死：上游加一种叠加上限时不会漏掉 title。
    more_html = "\n          ".join(
        f"""<div class="fgroup">
            <span class="flabel">{html.escape(label)}<i>{html.escape(label_en)}</i></span>
            <div class="fbtns">{''.join(
                f'<button class="fbtn" type="button" data-{attr}="{html.escape(val)}"'
                f' aria-pressed="false"'
                + (f' title="{html.escape(item[5])}"' if len(item) > 5 else '')
                + f'>{html.escape(zh)}<i>{html.escape(en)}</i>'
                f'<span class="fbtn-n">{n}</span></button>'
                for item in items
                for attr, val, zh, en, n in [item[:5]]
            )}</div>
          </div>"""
        for label, label_en, items in more_rows
    )
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
<!-- 构建时间戳（仅调试用）。workflow 与 rebuild_compendium 比对产物时按它识别并忽略时间差异 -->
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
      <!-- 搜索框：🔴 不在框外加「搜索 Search」标签 —— 页头本来就紧，
           加一行会把它撑高、把页签挤下去。占位符里同时写中英，
           空态就能看到两版；聚焦后占位符消失，此时靠 aria-label 兜底。
           面包屑式的位置提示放在 header 底部的页签行更合适。 -->
      <input id="q" class="search" type="search"
             placeholder="搜索全部内容 · Search all"
             aria-label="搜索全部内容 / Search everything">
    </div>
    <nav class="tabs" role="tablist">
      <button class="tab" role="tab" data-go="affixes" aria-selected="true">恩赐与诅咒<i>{len(affixes)}</i><u>Boons &amp; Curses</u></button>
      <button class="tab" role="tab" data-go="achievements" aria-selected="false">成就<i>{len(achievements)}</i><u>Achievements</u></button>
      <button class="tab" role="tab" data-go="difficulties" aria-selected="false">难度<i>{len(difficulties)}</i><u>Difficulties</u></button>
      <span class="tab-ind" id="tabInd" aria-hidden="true"></span>
    </nav>
  </div>
</header>

<main class="wrap">
  <div class="toolbar">
    <div class="filters">
      <div class="frow">{type_group}{hero_group}{change_btn}
      </div>
      <div class="frow">{rarity_group}{more_btn}
      </div>
      <div class="fmore" id="morePanel" data-open="false">
        <div class="fmore-in">
          <div class="frow">
          {more_html}
          </div>
        </div>
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
    本站基于 Errorb0t 的<a href="https://errorb0t.github.io/heroesrogue/">英文图鉴</a>汉化改进。
    Heroes Rogue 为玩家自制项目，与暴雪娱乐无关，原始游戏素材与角色版权均归暴雪娱乐所有。
  </footer>
</main>

<script>
(function () {{
  var body = document.body;
  var q = document.getElementById("q");
  var countEl = document.getElementById("count");
  var emptyEl = document.getElementById("empty");
  var tabs = Array.from(document.querySelectorAll(".tab"));
  var tabInd = document.getElementById("tabInd");
  var kindBtns = Array.from(document.querySelectorAll(".fbtn[data-kind]"));
  var heroModeBtns = Array.from(document.querySelectorAll(".fbtn[data-hero-mode]"));
  var flagBtns = Array.from(document.querySelectorAll(".fbtn[data-flag]"));
  var rarBtns = Array.from(document.querySelectorAll(".fbtn[data-rarity]"));
  var stackBtns = Array.from(document.querySelectorAll(".fbtn[data-stack]"));
  var condBtns = Array.from(document.querySelectorAll(".fbtn[data-cond]"));
  var views = {{
    affixes: document.getElementById("v-affixes"),
    achievements: document.getElementById("v-achievements"),
    difficulties: document.getElementById("v-difficulties")
  }};
  var LABEL = {{ affixes: "项恩赐与诅咒", achievements: "项成就", difficulties: "项难度" }};

  /* ================= 筛选状态 =================
     单选维度（互斥，同组只能留一个）：
       kind       "all" | "boon" | "curse"
       heroMode   "all" | "only" | "exclude"
     复选维度（同组 OR，跨组 AND）：
       rarities   Set<rarity>
       stacks     Set<"finite"|"infinite"|"none">
       conds      Set<"map"|"level"|"req">
       tags       Set<英雄类型标签名>（法力/近战/远程/可骑乘…）
       flags      Set（目前只有 changed）

     🔴 「指定某个英雄」**不在状态里**（2026-10-11 用户定）：交给搜索框。
        33 个英雄里绝大多数只关联 1~3 条恩赐，为它常驻一个按钮 + 320px 浮层
        不值得；搜「纳兹波」效果一样，还能顺带搜到描述里提到该英雄的条目。
        三态（不限/仅限定/排除）必须留着 —— 它判的是「有没有英雄条件」这个
        反向属性，搜索框替代不了。 */
  var state = {{
    view: "affixes", q: "",
    kind: "all", heroMode: "all",
    flags: new Set(), rarities: new Set(), stacks: new Set(), conds: new Set(),
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
    // 类型（单选）
    if (state.kind === "boon" && card.dataset.curse === "true") return false;
    if (state.kind === "curse" && card.dataset.curse !== "true") return false;

    // 英雄限定（三态单选）
    //   only → 只要**专属某个具体英雄**的（data-hero-specific）
    //   exclude → 反过来，其余全留
    //
    // 🔴 判据是「专属某人」而不是「带任何英雄条件」（2026-10-11 用户定）。
    //   两者差 14 条：10 条按英雄类型限定（法力/远程/骑乘…）、
    //   6 条是排除某几个英雄 —— 它们都与英雄有关但不是「专属某人」，
    //   归到 exclude 侧。文案写的是「特定 / Hero-specific」，
    //   判据就必须跟文案一致，否则玩家点「特定」会看到「非起始英雄」这类条目，
    //   而那些条目显然不是「特定某个英雄」。
    //
    // 🔴 这三态**不能交给搜索框替代**：搜索是「包含某关键词」，
    //   而 specific/other 判的是反向属性，搜索框做不到。
    if (state.heroMode === "only" && card.dataset.heroSpecific !== "true") return false;
    if (state.heroMode === "exclude" && card.dataset.heroSpecific === "true") return false;

    // 稀有度（同组 OR）
    if (state.rarities.size && !state.rarities.has(card.dataset.rarity)) return false;
    // 叠加上限（同组 OR）
    if (state.stacks.size && !state.stacks.has(card.dataset.stack)) return false;
    // 生效范围（同组 OR）
    if (state.conds.size) {{
      var hit = false;
      state.conds.forEach(function (c) {{
        if (card.dataset[c] === "1") hit = true;
      }});
      if (!hit) return false;
    }}
    // 「本次更新」
    if (state.flags.has("changed") && !card.dataset.changed) return false;
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
      //
      // 🔴🔴 **FLIP 的 Last 阶段：必须用「当前位置」而不是「累加后的值」**
      //   下面这行 heights[k] += 之前先存下当前卡自己的坐标：
      //   写在累加之后会记成「下一张卡该在的位置」，每张卡差一个 (高度+间隙) ——
      //   实测症状是同列卡片互相压住 20px（恰好等于 COL_GAP），看起来像重叠。
      //   这个 bug 在加 FLIP 之前不存在，因为那时 fx/fy 没人读。
      card.dataset.fx = String(k * (colW + COL_GAP));
      card.dataset.fy = String(heights[k]);
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

  /* ================= FLIP 布局动画 =================
     效果：筛选后**留下的卡片滑向新位置**填补空缺；新出现的淡入。

     ── 为什么用 WAAPI 而不是 CSS transition ──
     前四版都用「写 inline transform + CSS transition」，被打断时必然跳变：
       · transition 只能「重新开始」，**读不到当前动画进行到哪儿**
       · 要拿到当前位置只能写 `transition:none` + 瞬移 → 视觉上就是「跳一下」
     WAAPI（`Element.animate()`）解决了两点：
       ① 动画对象可被 `commitStyles()` **固化当前中间态**，也能被 `cancel()` 精确中断
       ② 硬件加速（compositor 层），主线程忙时不掉帧
     技能 STANDARDS「Performance」明确：WAAPI = JS 控制 + CSS 性能 + 可打断。

     ── 打断时的正确做法（业界共识）──
     react-easy-flip / remix-ui / GSAP Flip 都是同一招：
       **以元素「此刻真实的屏幕坐标」为新动画的起点**，而不是旧目标。
     本实现：`readPositions()` 用 getBoundingClientRect 量当前真实位置。
       🔴 这正是前四版的病根 —— 它们一律用「上一轮的 fx/fy」当起点，
          而那个值与屏幕上真实位置已经不一致了，跳变由此而来。

     ── 本项目的一个便宜 ──
     卡片是绝对定位 + JS 写 transform，**布局坐标 (fx, fy) 我们自己就知道**，
     所以不需要为了 FLIP 而多写 inline transform；WAAPI 只负责「从 A 飞到 B」，
     动画结束后 `fill:'none'` 让inline transform 自然成为最终态。
     → inline transform 永远是「布局真值」，WAAPI 只是临时的视觉覆盖层。 */

  var FLIP_EASE = "cubic-bezier(0.22, 1, 0.36, 1)";   // 强 ease-out，末尾不拖
  var FLIP_MS = 340;
  /* 同时飞行的卡片上限。🔴 必须封顶：一次筛选可能让 300+ 张卡同时移动，
     每个都要创建一个 Animation 对象；超出部分直接就位（它们已经归位了，
     只是没有「从远处飞过来」的过程，用户注意不到）。 */
  var MOVING_MAX = 120;

  /** 正在飞行的动画，key = 卡片元素。用 WeakMap 而非 Map：不需要遍历清理。 */
  var flights = new WeakMap();

  /** 一次性清理飞行状态：commit 当前视觉位置 → 取消动画 → 让位给新的。 */
  function landAll(cards) {{
    for (var i = 0; i < cards.length; i++) {{
      var c = cards[i];
      var anim = flights.get(c);
      if (!anim) continue;
      // ① commitStyles() 把「动画此刻的插值」固化进 inline style，
      //    cancel() 之后元素就停在这个真实位置 —— 视觉上不会跳。
      try {{ anim.commitStyles(); }} catch (e) {{ /* 动画已结束会抛，忽略 */ }}
      try {{ anim.cancel(); }} catch (e) {{}}
      flights.delete(c);
      // ②🔴 **立刻把 inline transform 写回布局真值**。
      //    这一步不能省：只commitStyles 的话，inline style 里留下的是
      //    「动画中间态」而不是「布局坐标」，下一轮 readPositions() 量到的
      //    就是这个残留值，与 fx/fy 对不上 → **误判为移动**。
      //    症状正是用户报的「结果不变也跳变」
      //    （实测：已是「诅咒」再点诅咒，仍创建 86 个动画）。
      //    此刻动画已结束，元素该在的地方就是布局算出来的位置。
      if (c.dataset.fx !== undefined) {{
        c.style.transform = "translate3d(" + c.dataset.fx + "px,"
                                 + c.dataset.fy + "px,0)";
      }}
    }}
  }}

  /**
   * First：量出每张可见卡**此刻真实的屏幕位置**。
   * 🔴 必须是 getBoundingClientRect —— 它含当前 transform，
   *    量到的正是「动画进行到一半时的真实坐标」，也就是新动画该起飞的地方。
   *    用 dataset.fx/fy（布局坐标）会把还在飞的卡片瞬间拉回起点。
   */
  function readPositions() {{
    var pos = new Map();
    var cards = cardsOf(state.view);
    // 🔴 容器坐标**只量一次**，提到循环外 ——
    //   放进循环里就是每张卡都调一次 getBoundingClientRect（这里还是两次：
    //   left 和 top 各调一次），409 张 = 818 次强制回流，必然掉帧。
    //   性能标准的「先批量读、再批量写」就指这个。
    var g = grids[state.view].getBoundingClientRect();
    for (var i = 0; i < cards.length; i++) {{
      var c = cards[i];
      if (c.classList.contains("hidden")) continue;
      if (c.dataset.fx === undefined) continue;   // 从未布局过（首屏）
      var r = c.getBoundingClientRect();
      // 相对容器坐标 —— 卡片 transform 就是相对容器写的
      pos.set(c, [r.left - g.left, r.top - g.top]);
    }}
    return pos;
  }}

  /**
   * Play：对位置变了的卡，从「刚才量到的真实位置」飞到「新布局位置」。
   *
   * 两步走（顺序不能反）：
   *   ① 所有位移过的卡**立刻**把 inline transform 写成新坐标（无过渡）
   *      —— 这是布局真值。
   *   ② 只给前 movingMax 张用 WAAPI 从旧屏幕坐标飞到新坐标。
   *      封顶之外不飞：它们已经「就地就位」了，不需要额外开销。
   */
  function playFlips(from, movingMax) {{
    var cards = cardsOf(state.view);
    var moved = 0;

    for (var i = 0; i < cards.length; i++) {{
      var c = cards[i];
      if (c.classList.contains("hidden")) continue;
      var start = from.get(c);
      var tx = Number(c.dataset.fx), ty = Number(c.dataset.fy);
      // 🔴🔴 **本轮新出现的卡必须跳过**（用户报「点 ALL 结果没变也跳变」的真凶）。
      //   它们在 readPositions() 时还是 `hidden`，量不到有效位置；
      //   等 paint() 把 hidden 撤掉、浏览器还没重新布局时就去量，
      //   拿到的是**未收敛的旧值**（实测 from=(0,0)→to=(395,0)，
      //   也就是从左边飞过来）。它们的正确表现是**淡入**（.enter），不该有位移。
      if (!start || !isFinite(tx) || !isFinite(ty)) continue;

      // 🔴🔴 **start 与 (fx, fy) 已经是同一坐标系（都相对容器），直接相减。**
      //   我在这里多减了一次 `g.left / g.top` ——
      //   容器在视口里位于 y=266，于是每张卡的起点都被抬高了 266px，
      //   症状正是用户报的「动画从筛选按钮那个位置跳下来」。
      //   同理，「结果不变也跳变」也是它造成的：
      //   g.top 恒不为 0，任何筛选都会带上这个恒定偏移。
      var dx = start[0] - tx;   // 需要的偏移量（相对容器，两边一致）
      var dy = start[1] - ty;
      if (Math.abs(dx) < 1 && Math.abs(dy) < 1) continue;   // 亚像素抖动不飞

      // ① inline transform 归位到布局真值（无过渡，不产生动画）
      c.style.transition = "";
      c.style.transform = "translate3d(" + tx + "px," + ty + "px,0)";

      // ② 超过上限就不飞 —— 它已经就位了，飞不飞都看不见
      if (moved >= movingMax) continue;
      moved++;

      // WAAPI：从「旧屏幕位置」飞到「布局真值」。
      // fill:'none' → 动画结束后不再影响元素，inline transform 自然接管。
      // 🔴 composite:'replace' + cancelOnReverse 交给默认：
      //    动画播完自动结束，不需要 class / 定时器 / transitionend 三套清理。
      var anim = c.animate(
        [
          {{ transform: "translate3d(" + (tx + dx) + "px," + (ty + dy) + "px,0)" }},
          {{ transform: "translate3d(" + tx + "px," + ty + "px,0)" }}
        ],
        {{ duration: FLIP_MS, easing: FLIP_EASE, fill: "none" }}
      );
      flights.set(c, anim);
      anim.finished
        .then(function () {{ flights.delete(c); }}, function () {{}})
        .catch(function () {{}});
    }}
    return moved;
  }}

  /** 动画进行中又点了筛选：先把在飞的全部「落地」，再开始新一轮。 */
  function settle() {{
    landAll(cardsOf(state.view));
  }}


  /* ================= 渲染 =================
     animate 参数的用意：
       首次渲染（init=true）不淡入 —— 页面刚打开时 400+ 张卡一起淡入，
       用户要等半秒才看得见图，纯粹是拖慢。
       筛选引起的重绘才淡入，且只给「本次新出现」的卡片加 .enter。
       淡入结束后移除类，避免 animation 停在 fill-mode:forwards 的终态
       （终态是 opacity:1，留着无害，但类越少重排越省）。 */
  var enterTimers = new WeakMap();
  function paint(init) {{
    var list = cardsOf(state.view);
    // FLIP First：改布局前先记旧坐标。init（首屏）不记 —— 那时没人「从上一状态过来」。
    // 🔴 **无条件复位**（不只是「上一轮在动画时才复位」）：
    //    上一轮可能停在 Invert 阶段（已写 transform、还没加 .flip），
    //    那种状态没有任何标志位能标识它 —— 只能靠「每次都归位」保证干净。
    //    首屏除外：那时还没布局过，fx/fy 都是 undefined。
    // FLIP First：**先量此刻真实的屏幕位置**（含在飞动画的中间态），
    // 再让上一轮动画「落地」，最后才 layout。
    // 🔴 顺序不能动：先量后落。反了就量到的是落地后的坐标，等于没中断。
    var fromPos = init ? null : readPositions();
    if (!init) settle();
    var n = 0;
    var fresh = [];
    for (var i = 0; i < list.length; i++) {{
      var card = list[i];
      var ok = matches(card);
      var wasHidden = card.classList.contains("hidden");
      card.classList.toggle("hidden", !ok);
      if (ok) {{
        n++;
        if (!init && wasHidden) fresh.push(card);
      }}
    }}
    countEl.innerHTML = "<b>" + n + "</b> / " + list.length + " " + LABEL[state.view];
    emptyEl.hidden = n !== 0;
    // 筛选后立刻重排 → 满足条件的自动上移、填空隙（用户要的行为）
    layout(state.view);

    // FLIP Play：留下的卡片从旧位置滑到新位置（补空缺的关键动画）。
    // 🔴 必须在 layout() **之后**：那时 dataset.fx/fy 才是新坐标。
    if (fromPos) playFlips(fromPos, MOVING_MAX);

    // 新出现的卡片淡入。140 张封顶：再多就没人在看动画了，纯烧 CPU。
    if (fresh.length) {{
      fresh.slice(0, 140).forEach(function (card) {{
        card.classList.remove("enter");
        // 强制回流以重启动画 —— 同一帧内加两次相同的类，第二次是空操作。
        void card.offsetWidth;
        card.classList.add("enter");
        var old = enterTimers.get(card);
        if (old) clearTimeout(old);
        enterTimers.set(card, setTimeout(function () {{
          card.classList.remove("enter");
        }}, 400));
      }});
      // 计数轻微跳动一下，给「结果变了」的瞬间反馈
      countEl.removeAttribute("data-bump");
      void countEl.offsetWidth;
      countEl.setAttribute("data-bump", "1");
    }}
  }}

  function syncButtons() {{
    kindBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(b.dataset.kind === state.kind));
    }});
    heroModeBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(b.dataset.heroMode === state.heroMode));
    }});
    flagBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(state.flags.has(b.dataset.flag)));
    }});
    rarBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(state.rarities.has(b.dataset.rarity)));
    }});
    stackBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(state.stacks.has(b.dataset.stack)));
    }});
    condBtns.forEach(function (b) {{
      b.setAttribute("aria-pressed", String(state.conds.has(b.dataset.cond)));
    }});
  }}

  function resetAffixFilters() {{
    state.kind = "all";
    state.heroMode = "all";
    state.flags.clear();
    state.rarities.clear();
    state.stacks.clear();
    state.conds.clear();
    syncButtons();
  }}

  /* ================= 页签指示条 =================
     只写 translateX + scaleX 两个合成器属性。
     元素本身固定 100px 宽，scaleX 缩放到目标页签宽度 ——
     如果改成改 width，每次切页都会触发布局，整排按钮跟着重排。 */
  function moveIndicator(animate) {{
    var active = null;
    for (var i = 0; i < tabs.length; i++) {{
      if (tabs[i].getAttribute("aria-selected") === "true") {{ active = tabs[i]; break; }}
    }}
    if (!active || !tabInd) return;
    var nav = active.parentElement;
    var ar = active.getBoundingClientRect();
    var nr = nav.getBoundingClientRect();
    if (!ar.width) return;
    if (animate === false) tabInd.style.transition = "none";
    tabInd.style.setProperty("--tx", (ar.left - nr.left) + "px");
    tabInd.style.setProperty("--sx", String(ar.width / 100));
    if (animate === false) {{
      void tabInd.offsetWidth;              // 强制应用无过渡的那一帧
      tabInd.style.transition = "";
    }}
  }}

  function switchView(v) {{
    if (state.view === v) return;
    state.view = v;
    body.dataset.view = v;
    tabs.forEach(function (t) {{
      t.setAttribute("aria-selected", String(t.dataset.go === v));
    }});
    // 指示条跟着走 —— 这是它唯一的职责。
    // 放paint() 之后：页签刚改完aria-selected，此刻量宽度才是新页签的。
    moveIndicator(true);
    // 离开恩赐/诅咒页时清掉筛选，回来时是干净的默认态
    if (v !== "affixes") resetAffixFilters();
    paint(true);
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

  /* 单选组：点谁就切到谁；再点已选中的「非全部」项退回全部。
     🔴 不做「禁用另一个」—— 禁掉后想换阵营必须先点 ALL，多一步且反直觉。
        ALL 存在的意义就是一步回到无过滤，所以它必须始终可点。 */
  function bindSingle(btns, key, attr) {{
    btns.forEach(function (b) {{
      b.addEventListener("click", function () {{
        var v = b.dataset[attr];
        state[key] = (state[key] === v && v !== "all") ? "all" : v;
        syncButtons();
        paint(false);
      }});
    }});
  }}
  bindSingle(kindBtns, "kind", "kind");
  bindSingle(heroModeBtns, "heroMode", "heroMode");

  /* 复选组：同组 OR，跨组 AND */
  function bindMulti(btns, set, attr) {{
    btns.forEach(function (b) {{
      b.addEventListener("click", function () {{
        var v = b.dataset[attr];
        if (set.has(v)) set.delete(v); else set.add(v);
        syncButtons();
        paint(false);
      }});
    }});
  }}
  bindMulti(flagBtns, state.flags, "flag");
  bindMulti(rarBtns, state.rarities, "rarity");
  bindMulti(stackBtns, state.stacks, "stack");
  bindMulti(condBtns, state.conds, "cond");

  /* ================= 「更多条件」折叠 =================
     用 grid-template-rows: 0fr ↔ 1fr 做纯 CSS 高度过渡，
     不用 JS 量高度、也不用 max-height 猜一个值。 */
  var moreOpen = document.getElementById("moreOpen");
  var morePanel = document.getElementById("morePanel");
  moreOpen.addEventListener("click", function () {{
    var open = morePanel.getAttribute("data-open") === "true";
    morePanel.setAttribute("data-open", String(!open));
    moreOpen.setAttribute("aria-expanded", String(!open));
  }});

  // 难度页文案里的「神话诅咒」→ 跳到恩赐与诅咒页并锁定「诅咒 + 神话」
  Array.from(document.querySelectorAll(".xlink[data-xkind]")).forEach(function (a) {{
    a.addEventListener("click", function (e) {{
      e.preventDefault();
      //先 resetAffixFilters() 再设目标值 —— 顺序反了会被 reset 覆盖掉，
      // 结果是跳回去了但筛选没锁上。
      resetAffixFilters();
      state.kind = a.dataset.xkind || "curse";
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
    t = setTimeout(function () {{ paint(false); }}, 90);
  }});

  // 快捷键：1-3 切视图，/ 聚焦搜索，Esc 关浮层
  document.addEventListener("keydown", function (e) {{
    if (e.key === "/" && document.activeElement !== q) {{ e.preventDefault(); q.focus(); return; }}
    // Esc 在输入框里优先交给浏览器（撤销输入），不抢
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
    rt = setTimeout(function () {{ layoutAll(); moveIndicator(true); }}, 120);
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
  paint(true);
  // 指示条首帧直接落位（无过渡），否则页面一打开它会从最左边「滑」过来 ——
  // 首次渲染不是"切换"，不需要动画。
  moveIndicator(false);
  // 字体加载完页签宽度可能变，指示条要跟着重算
  if (document.fonts && document.fonts.ready) {{
    document.fonts.ready.then(function () {{ moveIndicator(true); }});
  }}
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
