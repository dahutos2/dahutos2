#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
README 自動生成スクリプト
──────────────────────────────────────────────
ワークフロー側で
  • assets/stats.svg
  • assets/streak-stats.svg
  • assets/wakatime.svg
  • assets/top-langs.svg
  • assets/activity-graph.svg
  • assets/info.json           ← name / bio / location
  • assets/repos.json          ← [{language, stars}, …]
を準備済みとし、本スクリプトは
  1) JSON を読み込んで Hero・Stack を構築
  2) キャッシュ済み SVG を配置
  3) SECTION コメントで README を置換
  4) 更新日時をフッタに書き込む
Environment      : OWNER / PROFILE_LINKS
Secrets (workflow): PROFILE_TOKEN （GraphQL 用 PAT）等 / WAKA_TIME_SVG_ID
"""

from __future__ import annotations
import json, os, re, collections
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

# ────────────────────────── 基本設定
ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
OWNER = os.getenv("OWNER") or Path.cwd().parts[-1]

# ────────────────────────── スキルレベル & 色
LEVELS = [(20, "Expert"), (10, "Advanced"), (5, "Intermediate"), (1, "Beginner")]
LEVEL_COLOR = {  # レベル別ラベル色
    "Expert": "7E3AF2",
    "Advanced": "10B981",
    "Intermediate": "F59E0B",
    "Beginner": "EF4444",
    "Newbie": "9CA3AF",
}

# ────────────────────────── 言語→ロゴ色（全量保持）
LOGO_COLOR = {
    "Dart": "0175C2",
    "Flutter": "02569B",
    "Ruby": "CC342D",
    "Rails": "D30001",
    "Python": "3776AB",
    "TypeScript": "3178C6",
    "JavaScript": "F7DF1E",
    "Vue": "41B883",
    "Nuxt": "00C58E",
    "Go": "00ADD8",
    "Shell": "89e051",
    "Java": "B07219",
    "C": "555555",
    "C++": "f34b7d",
    "C#": "178600",
    "PHP": "777BB4",
    "Swift": "FA7343",
    "Kotlin": "A97BFF",
    "Rust": "DEA584",
    "Scala": "DC322F",
    "Perl": "0298C3",
    "Haskell": "5E5086",
    "Elixir": "6E4A7E",
    "Erlang": "B83998",
    "R": "198CE7",
    "Objective-C": "438EFF",
    "Objective-C++": "6866FB",
    "SQL": "E38C00",
    "HTML": "E34C26",
    "CSS": "1572B6",
    "SCSS": "CD6799",
    "Less": "1D365D",
    "Sass": "CC6699",
    "Markdown": "083FA1",
    "JSON": "292929",
    "YAML": "CB171E",
    "Dockerfile": "384D54",
    "Makefile": "427819",
    "Bash": "89E051",
    "PowerShell": "012456",
    "Lua": "000080",
    "GraphQL": "E10098",
    "CoffeeScript": "244776",
    "Groovy": "4298B8",
    "Gradle": "02303A",
    "Vim script": "199F4B",
    "Emacs Lisp": "8C7597",
    "Clojure": "5881D8",
    "F#": "378BBA",
    "Assembly": "6E4C13",
    "MATLAB": "E16737",
    "Jupyter Notebook": "DA5B0B",
    "TeX": "3D6117",
    "LaTeX": "008080",
    "OpenSCAD": "000000",
    "Visual Basic": "945DB7",
    "Ada": "02f88c",
    "Fortran": "734F96",
    "VHDL": "adb2cb",
    "Verilog": "b2b7f8",
    "SystemVerilog": "DAE1C2",
    "Crystal": "000100",
    "Nim": "FFE953",
    "OCaml": "3BE133",
    "Elm": "60B5CC",
    "Reason": "FF5847",
    "Pug": "A86454",
    "Handlebars": "F0772B",
    "HCL": "844FBA",
    "Terraform": "844FBA",
    "Ansible": "000000",
    "SaltStack": "00AA00",
}


# ────────────────────────── Util：SECTION 置換
def repl(tag: str, new: str, text: str) -> str:
    pat = rf"<!--START_SECTION:{tag}-->(.*?)<!--END_SECTION:{tag}-->"
    return re.sub(
        pat,
        f"<!--START_SECTION:{tag}-->\n{new}\n<!--END_SECTION:{tag}-->",
        text,
        flags=re.S,
    )


# ────────────────────────── Badges（Views / Wakatime）
def badges_row() -> str:
    views = f"![Views](https://komarev.com/ghpvc/?username={OWNER}&style=flat)"
    waka = ""
    if uid := os.getenv("WAKA_TIME_SVG_ID"):
        waka = (
            f"[![wakatime](https://wakatime.com/badge/user/{uid}.svg)]"
            f"(https://wakatime.com/@{uid})"
        )
    return " ".join(filter(None, [views, waka]))


# ────────────────────────── Hero（簡潔センタリング）
def hero(info: dict) -> str:
    """
    左カラム : 氏名タイトル + Bio
    右カラム : ハンドル名 / 外部リンク / ロケーション
    各カラム幅は 50% 固定。テーブルなのでモバイルでも自然に縦積みされる。
    """

    # ---------- データ取得 ----------
    name = info["name"]
    bio = (info.get("bio") or "").strip().replace("\n", " ")
    location = info.get("location") or ""
    links_cfg = json.loads(os.getenv("PROFILE_LINKS") or "[]")

    # ---------- 左カラム ----------
    left_parts = [f"<h1>👋 {name}</h1>"]
    if bio:
        left_parts.append(f"<p>{bio}</p>")
    left_td = "<br/>\n".join(left_parts)

    # ---------- 右カラム ----------
    right_lines = [f"<strong>@{OWNER}</strong>"]

    # 外部リンク（1 行ずつ）
    for l in links_cfg:
        right_lines.append(f'<a href="{l["url"]}">{l["title"]}</a>')

    if location:
        right_lines.append(f"📍 {location}")

    right_td = "<br/>\n".join(right_lines)

    # ---------- テーブル結合 ----------
    hero_html = f"""
<table width="100%">
  <tr>
    <td width="50%" valign="top">{left_td}</td>
    <td width="50%" valign="top" align="right">{right_td}</td>
  </tr>
</table>
""".strip()

    return hero_html


# ────────────────────────── Stack
def classify(v: float) -> str:
    for th, lvl in LEVELS:
        if v >= th:
            return lvl
    return "Newbie"


def badge(lang: str, lvl: str) -> str:
    lang_col = LOGO_COLOR.get(lang, "888888")
    lvl_col = LEVEL_COLOR[lvl]
    return (
        f"https://img.shields.io/badge/{quote_plus(lang)}-{quote_plus(lvl)}-{lvl_col}"
        f"?logo={lang.lower().replace(' ','')}&logoColor=white&labelColor={lang_col}"
    )


def build_stack(repos: list[dict]) -> str:
    cnt, star = collections.Counter(), collections.Counter()
    for r in repos:
        cnt[r["language"]] += 1
        star[r["language"]] += r["stars"]
    score = {l: cnt[l] + star[l] / 10 for l in cnt}

    grouped = collections.defaultdict(list)
    for lang, val in score.items():
        grouped[classify(val)].append((lang, val))

    out: list[str] = []
    for lvl in ["Expert", "Advanced", "Intermediate", "Beginner", "Newbie"]:
        langs = grouped.get(lvl)
        if not langs:
            continue
        out.append(f"### {lvl}")
        out.append(
            " ".join(
                f"![{lang}]({badge(lang, lvl)})"
                for lang, _ in sorted(langs, key=lambda t: t[1], reverse=True)
            )
        )
    return "\n\n".join(out)


# ────────────────────────── Stats & Streak + Wakatime & Top-Langs (2 行)
def stats_block() -> str:
    stats = (
        f'<img src="assets/stats.svg" alt="{OWNER} stats"  width="48.7%" align="left"/>'
    )
    streak = f'<img src="assets/streak-stats.svg"  alt="{OWNER} streak" width="48.7%"/>'
    graph = f'<img src="assets/activity-graph.svg" alt="{OWNER} graph" width="99.8%"/>'
    waka = '<img src="assets/wakatime.svg" alt="wakatime" width="49.5%" align="left"/>'
    langs = '<img src="assets/top-langs.svg" alt="top langs" width="48%"/>'

    return (
        '<div class="d-block">\n'
        f"  {stats}\n  {streak}\n</div>\n<br/>\n"
        f"{graph}\n\n---\n"
        '<div class="d-block">\n'
        f"  {waka}\n  {langs}\n</div>"
    )


# ────────────────────────── Contribution Graph
def contrib_graph() -> str:
    return '<img src="assets/activity-graph.svg" width="100%"/>'


# ────────────────────────── メイン処理
def main() -> None:
    info = json.loads(Path("assets/info.json").read_text())
    repos = json.loads(Path("assets/repos.json").read_text())
    md = README.read_text()

    md = repl("badges", badges_row(), md)
    md = repl("hero", hero(info), md)
    md = repl("stack", build_stack(repos), md)
    md = repl("stats", stats_block(), md)
    md = repl("contrib", contrib_graph(), md)

    # Trophy (外部呼び出し)
    trophy_tag = (
        "[![trophy](https://github-profile-trophy.vercel.app/?username="
        f"{OWNER})](https://github.com/ryo-ma/github-profile-trophy)"
    )
    md = repl("trophy", trophy_tag, md)

    # 更新日時
    ts = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime(
        "%Y-%m-%d %H:%M JST"
    )
    md = repl("footer", f'<p align="right"><sup>⏰ Updated {ts}</sup></p>', md)

    README.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
