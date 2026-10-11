"""核查中文侧是否跟上指定版本的英文改动（跟完上游必跑）。

用法：
    python scripts/check_zh_sync.py v0.17.1 v0.17.2

🔴 **判据是「数值集合比对」，不是纯文本相等**：
   - 抽出中英文各自剥标签后的全部数字，比较「英文有而中文没有」的部分；
     命中即判定为**数值滞后**（玩家会按错误信息决策，属真bug）。
   - 纯文本不同但数字齐全的，只报「待人工确认」——
     翻译过的东西必然与英文不同，逐条报警等于没报警。

⚠️ 已知会大量误报/噪音的项：
   - 专有名词（鲁莽/Reckless）属正常翻译，不是滞后
   - `Affix/Tooltip/Append/*` 系列因含 `<d ref>` 动态引用，
     数字由引擎运行时填，不适合用本判据

退出码恒为 0（这是体检脚本不是门禁）；看输出里的三段统计即可。
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

EN = "mods/HeroesRogue.StormMod/enUS.StormData/LocalizedData/GameStrings.txt"
ZH = "mods/HeroesRogue.StormMod/zhCN.StormData/LocalizedData/GameStrings.txt"


def sh(a):
    r = subprocess.run(a, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    return r.stdout


def load(txt):
    d = {}
    for line in txt.splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            d[k.strip()] = v.strip()
    return d


def plain(s: str) -> str:
    """剥标签 → 归一化数字/百分号/空白，用于语义比对。"""
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = s.replace("&nbsp;", " ")
    s = re.sub(r"\s+", " ", s).strip()
    return s


def numbers(s: str) -> list[str]:
    """抽出所有数值（含百分号），用来专门比对「数值有没有改」。"""
    return re.findall(r"[+-]?\d+(?:\.\d+)?%?", plain(s))


def main() -> int:
    old, new = (sys.argv[1], sys.argv[2]) if len(sys.argv) > 2 else ("v0.17.1", "v0.17.2")
    o_en = load(sh(["git", "show", f"{old}:{EN}"]))
    n_en = load(sh(["git", "show", f"{new}:{EN}"]))
    zh = load(Path(ZH).read_text(encoding="utf-8-sig"))

    changed = sorted(k for k in set(o_en) | set(n_en) if o_en.get(k) != n_en.get(k))
    rel = [k for k in changed
           if k.startswith(("Affix/", "Achievement/", "Label/Name/PickAffix"))]

    print(f"对比 {old} → {new}：英文侧变化 {len(changed)} 个 key，"
          f"其中恩赐/成就相关 {len(rel)}\n")

    missing_key, num_lag, text_lag, ok = [], [], [], []

    for k in rel:
        old_en, new_en = o_en.get(k, ""), n_en.get(k, "")
        zh_val = zh.get(k)
        if zh_val is None:
            missing_key.append(k)
            continue
        # 1) 数值比对：中文抽出的数字集合是否覆盖英文新版的全部数字
        en_nums = set(numbers(new_en))
        zh_nums = set(numbers(zh_val))
        lost = en_nums - zh_nums
        # 2) 文本比对：纯文本完全一致视为同步
        if lost:
            num_lag.append((k, old_en, new_en, zh_val, sorted(lost)))
        elif plain(new_en) != plain(zh_val):
            text_lag.append((k, old_en, new_en, zh_val))
        else:
            ok.append(k)

    print(f"✔ 已同步: {len(ok)} 条")
    print(f"✘ 中文缺key: {len(missing_key)} 条")
    for k in missing_key:
        print(f"    {k}")
    print(f"\n▲ 中文数值滞后（英文新版有、中文没有的数字）: {len(num_lag)} 条")
    for k, o, nw, z, lost in num_lag:
        print(f"\n    【{k}】缺数字 {lost}")
        print(f"      英文旧: {plain(o)[:160]}")
        print(f"      英文新: {plain(nw)[:160]}")
        print(f"      中文现: {plain(z)[:160]}")
    print(f"\n○ 文本表述不同（非数值滞后，需人工确认）: {len(text_lag)} 条")
    for k, o, nw, z in text_lag:
        print(f"\n    【{k}】")
        print(f"      英文新: {plain(nw)[:200]}")
        print(f"      中文现: {plain(z)[:200]}")

    print(f"\n{'='*70}")
    print(f"需处理: 缺key {len(missing_key)} + 数值滞后 {len(num_lag)} "
          f"+ 待确认 {len(text_lag)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
