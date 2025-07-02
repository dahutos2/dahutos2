#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
README 自動生成 – JSON(assets/info.json・repos.json)＋キャッシュ SVG を利用
  • Badges       : Views  +  Wakatime (任意)
  • Hero         : 中央寄せタイトル / ハンドル，リンク行，自己紹介(bio)，所在地
  • Stack        : 全リポジトリ言語をレベル分類バッジ
  • Stats Row    : stats.svg + streak-stats.svg を横並び
  • Contributions: activity-graph.svg
  • Trophy       : GitHub Profile Trophy (外部呼び出し)
  • Footer       : JST 時刻をマーカー置換
"""

from __future__ import annotations
import json, os, re, collections
from pathlib import Path
from datetime import datetime, timezone, timedelta
from urllib.parse import quote_plus

# ---------- 基本 ----------
ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
OWNER = os.getenv("OWNER") or Path.cwd().parts[-1]

# ---------- レベル & カラー ----------
LEVELS = [(20, "Expert"), (10, "Advanced"), (5, "Intermediate"), (1, "Beginner")]
LEVEL_COLOR = {
    "Expert": "7E3AF2",
    "Advanced": "10B981",
    "Intermediate": "F59E0B",
    "Beginner": "EF4444",
    "Newbie": "9CA3AF",
}

# ---------- 言語ロゴ色（省略せずに保持） ----------
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


# ---------- 共通置換関数 ----------
def repl(tag: str, new: str, text: str) -> str:
    pattern = rf"<!--START_SECTION:{tag}-->(.*?)<!--END_SECTION:{tag}-->"
    return re.sub(
        pattern,
        f"<!--START_SECTION:{tag}-->\n{new}\n<!--END_SECTION:{tag}-->",
        text,
        flags=re.S,
    )


# ---------- ビュー & Wakatime バッジ ----------
def small_badges() -> str:
    views = f"![Views](https://komarev.com/ghpvc/?username={OWNER}&style=flat)"
    waka_badge = ""
    wak_user = os.getenv("WAKATIME_USER")
    if wak_user:
        waka_badge = (
            f"[![wakatime](https://wakatime.com/badge/user/{wak_user}.svg)]"
            f"(https://wakatime.com/@{wak_user})"
        )
    return " ".join(filter(None, [views, waka_badge]))


# ---------- Hero ----------
def hero(info: dict) -> str:
    name_html = f'<h1 align="center">👋 {info["name"]}</h1>'
    user_html = f'<p align="center"><strong>@{OWNER}</strong></p>'
    # 外部リンク
    links_html = ""
    links = json.loads(os.getenv("PROFILE_LINKS", "[]"))
    if links:
        row = " ・ ".join(f'<a href="{l["url"]}">{l["title"]}</a>' for l in links)
        links_html = f'<p align="center">{row}</p>'
    # Bio / Location
    bio_html = f'<p>{info["bio"].strip()}</p>' if info.get("bio") else ""
    loc_html = (
        f'<p align="center">📍 {info["location"]}</p>' if info.get("location") else ""
    )
    return "\n".join(
        filter(None, [name_html, user_html, links_html, bio_html, loc_html])
    )


# ---------- Stack ----------
def classify(v: float) -> str:
    for th, lvl in LEVELS:
        if v >= th:
            return lvl
    return "Newbie"


def badge(lang: str, lvl: str) -> str:
    base = LOGO_COLOR.get(lang, "888888")
    lbl = LEVEL_COLOR[lvl]
    return (
        f"https://img.shields.io/badge/{quote_plus(lang)}-{quote_plus(lvl)}-{base}"
        f"?logo={lang.lower()}&logoColor=white&labelColor={lbl}"
    )


def stack(repos: list[dict]) -> str:
    cnt, star = collections.Counter(), collections.Counter()
    for r in repos:
        cnt[r["language"]] += 1
        star[r["language"]] += r["stars"]
    score = {l: cnt[l] + star[l] / 10 for l in cnt}

    grouped = collections.defaultdict(list)
    for lang, val in score.items():
        grouped[classify(val)].append((lang, val))

    out = []
    for lvl in ["Expert", "Advanced", "Intermediate", "Beginner", "Newbie"]:
        if lvl not in grouped:
            continue
        out.append(f"### {lvl}")
        out.append(
            " ".join(
                badge(l, lvl)
                for l, _ in sorted(grouped[lvl], key=lambda t: t[1], reverse=True)
            )
        )
    return "\n\n".join(out)


# ---------- Stats Row ----------
def stats_row() -> str:
    stats = '<img src="assets/stats.svg" width="49.3%" align="left"/>'
    streak = '<img src="assets/streak-stats.svg" width="49.3%"/>'
    return f"<div>{stats}{streak}</div>\n<br/>"


# ---------- Contributions ----------
def contrib() -> str:
    return '<img src="assets/activity-graph.svg" width="100%"/>'


# ---------- メイン処理 ----------
def main():
    # 事前にワークフローで生成済み JSON を読む
    info = json.loads(Path("assets/info.json").read_text())
    repos = json.loads(Path("assets/repos.json").read_text())

    md = README.read_text()

    md = repl("badges", small_badges(), md)
    md = repl("hero", hero(info), md)
    md = repl("stack", stack(repos), md)
    md = repl("stats", stats_row(), md)
    md = repl("contrib", contrib(), md)
    md = repl(
        "trophy",
        f"[![trophy](https://github-profile-trophy.vercel.app/?username={OWNER})]"
        f"(https://github.com/ryo-ma/github-profile-trophy)",
        md,
    )

    ts = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime(
        "%Y-%m-%d %H:%M JST"
    )
    md = repl("footer", f'<p align="right"><sup>⏰ Updated {ts}</sup></p>', md)

    README.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
