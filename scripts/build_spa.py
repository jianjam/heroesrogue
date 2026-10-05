"""单文件 SPA 生成器 —— Heroes Rogue 中文图鉴

与旧方案（四个独立 HTML）的根本区别：
  **单页、零跳转**。四个视图（恩赐/诅咒/难度/成就）在同一文档内切换，
  因此不存在「页面跳转 → 浏览器重置视口 → 视觉跳变」这个根本问题。

用法：
    python build_spa.py --output <dir>            # 需 affix_overview 包可导入
"""

from __future__ import annotations

import argparse
import html
import json
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
    en = _en_name_map()

    def key(item):
        rank = (
            RARITY_ORDER.index(item.rarity)
            if item.rarity in RARITY_ORDER
            else len(RARITY_ORDER)
        )
        return (rank, en.get(item.affix_id, item.name).lower(), item.affix_id)

    return sorted(affixes, key=key)


# ---------------------------------------------------------------- 卡片渲染
def render_affix_card(affix) -> str:
    rarity_color = RARITY_COLORS.get(affix.rarity, "#c8d4e6")
    rarity_zh = RARITY_DISPLAY_NAMES.get(affix.rarity, affix.rarity)
    rarity_en = RARITY_DISPLAY_NAMES_EN.get(affix.rarity, affix.rarity)

    search_blob = " ".join(
        p for p in [
            affix.affix_id, affix.name, affix.name_en, affix.tooltip_plain,
            rarity_zh, rarity_en, affix.hero_specific, affix.hero_specific_en,
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

    return f"""
<article class="card" data-rarity="{html.escape(affix.rarity)}"
         data-hero-only="{'true' if affix.has_hero_condition else 'false'}"
         data-search="{html.escape(search_blob)}">
  <div class="card-head">
    <img class="card-icon" src="{html.escape(affix.icon_url)}" alt="" width="56" height="56">
    <div class="card-labels">
      <span class="chip chip-rarity" style="--rc:{html.escape(rarity_color)}">{html.escape(rarity_zh)}<i>{html.escape(rarity_en)}</i></span>{hero_chip}
    </div>
  </div>
  <h3 class="card-name">{bilingual(html.escape(affix.name), html.escape(affix.name_en))}</h3>
  <div class="card-desc">{bilingual(affix.tooltip_html, affix.tooltip_html_en)}</div>
  <div class="card-notes">{bilingual(notes_zh, notes_en)}{footnotes}</div>
</article>""".strip()


def render_difficulty_card(d) -> str:
    search = " ".join(
        p for p in [d.label, d.name_en, d.tooltip_plain, "difficulty", "难度"] if p
    ).lower()
    zh = d.tooltip_html or "<p>未找到本地化说明。</p>"
    en = d.tooltip_html_en or "<p>No localized tooltip found.</p>"
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
  border-bottom-color: var(--accent); font-weight: 600;
}
.tab[aria-selected="true"] i { color: var(--muted); }
.tab[aria-selected="true"] u { color: #8fa3bd; }

/* ---------------- 主体 ---------------- */
main { padding: 18px 0 64px; }

/* ---- 视图显隐（只在这里定义一次）---- */
main .view { display: none; }
body[data-view="boons"] #v-boons,
body[data-view="curses"] #v-curses,
body[data-view="difficulties"] #v-difficulties,
body[data-view="achievements"] #v-achievements { display: block; }

.toolbar {
  display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
  min-height: 46px;
  margin-bottom: 14px;
  padding-bottom: 12px; border-bottom: 1px solid var(--line-soft);
}
/* 筛选行：非恩赐/诅咒页用 visibility 隐藏（**保留占位高度**），
   不能用 display:none —— 那会让工具条从 46px 塌到 38px，切页时首卡上移 8px。 */
.filters {
  display: flex; gap: 6px; flex-wrap: wrap;
  visibility: hidden; pointer-events: none;
}
body[data-view="boons"] .filters,
body[data-view="curses"] .filters { visibility: visible; pointer-events: auto; }

.fbtn {
  appearance: none; cursor: pointer; font: inherit; font-size: .82rem;
  padding: 5px 12px; border-radius: 999px;
  border: 1px solid var(--line); background: var(--bg-soft); color: var(--muted);
}
.fbtn i { font-style: normal; font-size: .7rem; opacity: .65; margin-left: 4px; }
.fbtn:hover { color: var(--text); border-color: #35506f; }
.fbtn[aria-pressed="true"] {
  background: var(--accent); border-color: var(--accent); color: #08111d; font-weight: 600;
}
.fbtn[aria-pressed="true"] i { opacity: .8; }

.count { margin-left: auto; color: var(--muted); font-size: .85rem; white-space: nowrap; }
.count b { color: var(--text); }

.grid {
  display: grid; gap: 14px;
  grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
  align-items: start;
}

.card {
  background: var(--panel); border: 1px solid var(--line);
  border-radius: var(--radius); padding: 14px 15px;
  display: flex; flex-direction: column; gap: 9px;
  /* ⚠️ 不用 content-visibility:auto —— 切换视图时浏览器会重新估算
     离屏卡片高度，导致滚动位置/页面高度瞬间变化（同样是"跳变"）。
     510 张卡在现代浏览器上直接渲染也不卡。 */
}
.card.hidden { display: none; }

.card-head { display: flex; gap: 11px; align-items: flex-start; }
.card-icon {
  width: 56px; height: 56px; flex: 0 0 56px;
  border-radius: 11px; border: 1px solid var(--line);
  background: #0d1522; object-fit: cover;
}
.card-labels { display: flex; flex-wrap: wrap; gap: 5px; min-width: 0; }

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


def build_html(boons, curses, difficulties, achievements, version) -> str:
    import time as _t
    build_stamp = _t.strftime("%Y-%m-%d %H:%M:%S")
    # ---- 筛选按钮（稀有度）
    present = {a.rarity for a in boons} | {a.rarity for a in curses}
    ordered = [r for r in RARITY_ORDER if r in present]
    ordered += sorted(present - set(ordered))
    chips = ['<button class="fbtn" data-rarity="" aria-pressed="true">全部<i>All</i></button>',
             '<button class="fbtn" data-rarity="__hero__" aria-pressed="false">特定英雄<i>Hero-specific</i></button>']
    for r in ordered:
        chips.append(
            f'<button class="fbtn" data-rarity="{html.escape(r)}" aria-pressed="false">'
            f'{html.escape(RARITY_DISPLAY_NAMES.get(r, r))}'
            f'<i>{html.escape(RARITY_DISPLAY_NAMES_EN.get(r, r))}</i></button>'
        )
    chips_html = "\n      ".join(chips)

    total = len(boons) + len(curses) + len(difficulties) + len(achievements)

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
<body data-view="boons">
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
      <button class="tab" role="tab" data-go="boons"   aria-selected="true">恩赐<i>{len(boons)}</i><u>Boons</u></button>
      <button class="tab" role="tab" data-go="curses"  aria-selected="false">诅咒<i>{len(curses)}</i><u>Curses</u></button>
      <button class="tab" role="tab" data-go="difficulties" aria-selected="false">难度<i>{len(difficulties)}</i><u>Difficulties</u></button>
      <button class="tab" role="tab" data-go="achievements" aria-selected="false">成就<i>{len(achievements)}</i><u>Achievements</u></button>
    </nav>
  </div>
</header>

<main class="wrap">
  <div class="toolbar">
    <div class="filters">
      {chips_html}
    </div>
    <div class="count" id="count"></div>
  </div>

  <section class="view" id="v-boons">
    <div class="grid">
{cards(boons, render_affix_card)}
    </div>
  </section>

  <section class="view" id="v-curses">
    <div class="grid">
{cards(curses, render_affix_card)}
    </div>
  </section>

  <section class="view" id="v-difficulties">
    <div class="grid">
{cards(difficulties, render_difficulty_card)}
    </div>
  </section>

  <section class="view" id="v-achievements">
    <div class="grid">
{cards(achievements, render_achievement_card)}
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
  var fbtns = Array.from(document.querySelectorAll(".fbtn"));
  var views = {{
    boons: document.getElementById("v-boons"),
    curses: document.getElementById("v-curses"),
    difficulties: document.getElementById("v-difficulties"),
    achievements: document.getElementById("v-achievements")
  }};
  var LABEL = {{ boons: "个恩赐", curses: "个诅咒", difficulties: "项难度", achievements: "项成就" }};

  var state = {{ view: "boons", q: "", rarity: "" }};
  // 每个视图各自缓存卡片列表，避免每次切页重查 DOM
  var cache = {{}};

  function cardsOf(v) {{
    if (!cache[v]) {{
      cache[v] = Array.from(views[v].querySelectorAll(".card"));
      views[v].__total = cache[v].length;
    }}
    return cache[v];
  }}

  function matches(card) {{
    // 稀有度 / 特定英雄筛选
    if (state.rarity) {{
      if (state.rarity === "__hero__") {{
        if (card.dataset.heroOnly !== "true") return false;
      }} else if (card.dataset.rarity !== state.rarity) {{
        return false;
      }}
    }}
    // 关键词（卡片 data-search 已含中英双语的 id/名称/描述/条件）
    if (state.q) {{
      if (card.dataset.search.indexOf(state.q) === -1) return false;
    }}
    return true;
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
  }}

  function switchView(v) {{
    if (state.view === v) return;
    state.view = v;
    body.dataset.view = v;
    tabs.forEach(function (t) {{
      t.setAttribute("aria-selected", String(t.dataset.go === v));
    }});
    // 切换筛选：恩赐/诅咒保留稀有度筛选，其它视图清掉
    if (v !== "boons" && v !== "curses") {{
      state.rarity = "";
      fbtns.forEach(function (b) {{
        b.setAttribute("aria-pressed", String(b.dataset.rarity === ""));
      }});
    }}
    paint();
  }}

  tabs.forEach(function (t) {{
    t.addEventListener("click", function () {{
      switchView(t.dataset.go);
      // 切页后回到顶部（同一文档内，无浏览器重置，行为完全可控）
      window.scrollTo({{ top: 0, behavior: "auto" }});
    }});
  }});

  fbtns.forEach(function (b) {{
    b.addEventListener("click", function () {{
      state.rarity = b.dataset.rarity;
      fbtns.forEach(function (x) {{
        x.setAttribute("aria-pressed", String(x === b));
      }});
      paint();
    }});
  }});

  var t = null;
  q.addEventListener("input", function () {{
    state.q = q.value.trim().toLowerCase();
    clearTimeout(t);
    t = setTimeout(paint, 90);
  }});

  // 快捷键：1-4 切视图，/ 聚焦搜索
  document.addEventListener("keydown", function (e) {{
    if (e.key === "/" && document.activeElement !== q) {{ e.preventDefault(); q.focus(); return; }}
    if (document.activeElement === q) return;
    var i = ["1", "2", "3", "4"].indexOf(e.key);
    if (i > -1) {{
      switchView(tabs[i].dataset.go);
      window.scrollTo({{ top: 0, behavior: "auto" }});
    }}
  }});

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

    resolver = DynamicValueResolver({}, base)
    resolver.set_hero_name_overrides(heroes)

    affixes = load_affixes(zh, out, resolver, heroes, maps, en, heroes_en, maps_en)
    if hidden:
        affixes = [a for a in affixes if a.affix_id not in hidden]

    difficulties = load_difficulties(zh, resolver, en)
    achievements = load_achievements(zh, out, resolver, en)

    boons = sort_affixes([a for a in affixes if not a.negative])
    curses = sort_affixes([a for a in affixes if a.negative])

    html_text = build_html(boons, curses, difficulties, achievements, version)
    target = out / "index.html"
    target.write_text(html_text, encoding="utf-8")

    print(f"Wrote {target}  ({len(html_text) / 1024:.0f} KB)")
    print(f"Boons {len(boons)} | Curses {len(curses)} | Difficulties {len(difficulties)} | Achievements {len(achievements)}")
    return 0




if __name__ == "__main__":
    raise SystemExit(main())
