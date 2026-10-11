"""按「数值/效果」判据分类两个上游 tag 之间的 affix 变化。

输出 build_spa.py 直接认得的 version_changes.json：
  added    = 本版本新增
  modified = 数值/效果/触发器变了（玩家可感知）
  text_only= 仅英文文案改写（按用户判据**不算**修改）

用法:
    python scripts/classify_changes.py v0.17.1 v0.17.2
    python scripts/classify_changes.py v0.17.1 v0.17.2 --out <其它路径>

⚠️ **不要用 `> file` 重定向**：本脚本输出的是完整配置结构
   （modified 是字典、含 baseline_version 等 key），
   重定向会写出 load_version_changes() 认不出的格式，把配置弄坏。
   默认直接写入 DEFAULT_OUT。
"""

from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

AFFIX_XML = "mods/HeroesRogue.StormMod/Base.StormData/GameData/AffixData.xml"
STRINGS = "mods/HeroesRogue.StormMod/enUS.StormData/LocalizedData/GameStrings.txt"
DEFAULT_OUT = "scripts/affix_overview/config/version_changes.json"

# 玩家可感知的字段：数值、效果定义、触发条件、槽位、叠加上限、稀有度
EFFECT_FIELDS = {
    "CatalogModification", "Trigger", "Max", "Rarity", "HeroSpecific",
    "NoRoll", "Enabled", "Behavior", "Icon", "Instances",
    "MinimumDifficulty", "Count",
}


def sh(a):
    r = subprocess.run(a, capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    if r.returncode != 0:
        raise RuntimeError(f"git 失败: {r.stderr[:300]}")
    return r.stdout


def parse_fields(xml: str) -> dict[str, dict[str, str]]:
    out = {}
    for m in re.finditer(r'<Instances Id="([^"]+)">(.*?)</Instances>', xml, re.S):
        aid, body = m.group(1), m.group(2)
        fields: dict[str, str] = {}
        for c in re.finditer(
            r"<(String|Int)(?:\s+(\w+)=\"([^\"]*)\")?>\s*<Field Id=\"([^\"]+)\"[^>]*/>",
            body, re.S,
        ):
            typ, attr, val, fid = c.group(1), c.group(2), c.group(3), c.group(4)
            fields[fid] = (val or "") if attr else fields.get(fid, "") + (val or "")
        out[aid] = fields
    return out


def parse_strings(tag: str) -> dict[str, str]:
    out = {}
    for line in sh(["git", "show", f"{tag}:{STRINGS}"]).splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip()
    return out


def norm(s: str | None) -> str:
    return re.sub(r"\s+", " ", s or "").strip()


def main() -> int:
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__)
        return 1
    old, new = args[0], args[1]
    # 默认写回配置本体 —— 手工重定向容易写出错结构（见下面 result 处的注释）
    out_path = None
    if "--out" in sys.argv:
        out_path = sys.argv[sys.argv.index("--out") + 1]
    else:
        out_path = DEFAULT_OUT

    o_f = parse_fields(sh(["git", "show", f"{old}:{AFFIX_XML}"]))
    n_f = parse_fields(sh(["git", "show", f"{new}:{AFFIX_XML}"]))
    o_s, n_s = parse_strings(old), parse_strings(new)

    added, changed, text_only, removed = [], [], [], []

    for aid in sorted(n_f):
        if aid not in o_f:
            added.append(aid)
            continue
        effect_diffs, text_diffs = [], []
        for fid in set(o_f[aid]) | set(n_f[aid]):
            a, b = norm(o_f[aid].get(fid)), norm(n_f[aid].get(fid))
            if a == b:
                continue
            (effect_diffs if fid in EFFECT_FIELDS else []).append(f"{fid}")
        for key in (f"Affix/Name/{aid}", f"Affix/Tooltip/{aid}"):
            if o_s.get(key) != n_s.get(key):
                text_diffs.append(key.split("/")[1])
        if effect_diffs:
            changed.append({"id": aid, "fields": sorted(set(effect_diffs))})
        elif text_diffs:
            text_only.append({"id": aid, "fields": text_diffs})

    for aid in sorted(set(o_f) - set(n_f)):
        removed.append(aid)

    result = {
        "_comment": [
            "「本版本新增 / 修改」的 affix 清单。",
            f"由 scripts/classify_changes.py 对比上游 tag 自动生成，不要手改：",
            f"  python scripts/classify_changes.py {old} {new} "
            f"--out scripts/affix_overview/config/version_changes.json",
            "",
            "判据：仅「数值/效果/触发器」变动才算 modified；纯英文文案改写不算",
            "（用户 2026-10-10 定：玩家能感知的变化才值得提示）。",
            "modified 的值是改动涉及的字段名，仅用于说明改动性质。"
        ],
        "baseline_version": old,
        "version": new,
        "added": added,
        "modified": {c["id"]: c["fields"] for c in changed},
        "text_only": [t["id"] for t in text_only],
        "removed": removed,
    }

    # 🔴 必须带 _comment / baseline_version / modified(字典) 这套 key ——
    #   这些正是 data_loading.load_version_changes() 读的字段名。
    #   裸重定向（> file）会输出另一套结构（changed 是数组），把配置写坏。
    if out_path:
        Path(out_path).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"已写入 {out_path}", file=sys.stderr)
    else:
        json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
        print("", file=sys.stderr)
        print("提示：加 --out <路径> 可直接写成 build_spa.py 认得的格式",
              file=sys.stderr)

    print(f"新增 {len(added)} | 数值效果改动 {len(changed)} | "
          f"仅文案 {len(text_only)} | 删除 {len(removed)}", file=sys.stderr)
    print(f"→ 图鉴将标记 {len(added) + len(changed)} 条", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
