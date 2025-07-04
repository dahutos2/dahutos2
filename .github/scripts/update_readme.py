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
  • assets/trophy.svg
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
from typing import Dict, List, Tuple
from urllib.parse import quote, quote_plus

# ────────────────────────── 基本設定
ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"
OWNER = os.getenv("OWNER") or Path.cwd().parts[-1]

# ────────────────────────── Shields.io 用の色マッピング
LEVEL_COLOR = {
    "Expert": "CA9B04",  # gold
    "Advanced": "57DD55",  # green
    "Intermediate": "4CA8FF",  # blue
    "Beginner": "ADBAC7",  # gray-light
    "Newbie": "9CA3AF",  # gray
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
    1行目 : icon.png + 氏名（横並び）
    2行目 : ハンドル＋外部リンク（同一行）
    3行目 : Bio（センターに 1行）
    4行目 : ロケーション
    """
    # ----- タイトル行 (アイコン＋テキストを横並び)
    h1 = (
        f'<h1 align="left">'
        f'<img src="icon.png" alt="icon" align="center"'
        f'style="height:1.25em;width:1.25em;">'
        f'  {info["name"]}'
        f"</h1>"
    )

    # ----- ハンドル＋リンク
    #   @ユーザー ｜ <a>Link</a>
    handle = f"@{OWNER}"
    links = json.loads(os.getenv("PROFILE_LINKS") or "[]")
    if links:
        # 各リンクを <a> に変換
        link_parts = [f'<a href="{link["url"]}">{link["title"]}</a>' for link in links]
        # ｜ で連結
        link_str = " ｜ ".join(link_parts)
        handle += f" ｜ {link_str}"
    row2 = f'<p align="left">{handle}</p>'

    # ----- Bio
    bio_txt = info.get("bio", "").strip().replace("\n", " ")
    row3 = f'<p align="left">{bio_txt}</p>' if bio_txt else ""

    # ----- Location
    loc = info.get("location", "")
    row4 = f'<p align="right">📍 {loc}</p>' if loc else ""

    return "\n".join(filter(None, [h1, row2, row3, row4]))


def escape_shields(text: str) -> str:
    text = text.replace("_", "__").replace("-", "--")
    return quote(text, safe="-_")


def simple_icons_slug(lang: str) -> str:
    return quote_plus(lang.lower())


def lang_badge(lang: str, lvl: str) -> str:
    label = escape_shields(lang)
    logo = simple_icons_slug(lang)
    color = LEVEL_COLOR[lvl]
    lbl = LOGO_COLOR.get(lang, "888888")
    return (
        f"https://img.shields.io/badge/{label}-{lvl}-{color}"
        f"?logo={logo}&logoColor=white&labelColor={lbl}"
    )


def build_stack(langs: List[Dict[str, int]]) -> str:
    size_kb = {d["language"]: d["bytes"] / 1024 for d in langs}
    repo_cnt = {d["language"]: d["repos"] for d in langs}

    # ── 評価基準 ──
    #   * Expert       : ≥ 2 MB  〃 またはリポ数 ≥ 8
    #   * Advanced     : ≥ 0.8 MB 〃 またはリポ数 ≥ 4
    #   * Intermediate : ≥ 0.2 MB 〃 またはリポ数 ≥ 2
    #   * Beginner     : ≥ 0.05 MB 〃 またはリポ数 ≥ 1
    def classify(kb: float, repos: int) -> str:
        if kb >= 2000 or repos >= 8:
            return "Expert"
        if kb >= 800 or repos >= 4:
            return "Advanced"
        if kb >= 200 or repos >= 2:
            return "Intermediate"
        if kb >= 50 or repos >= 1:
            return "Beginner"
        return "Newbie"

    buckets: Dict[str, List[Tuple[str, float, int]]] = collections.defaultdict(list)
    for lang in size_kb:
        lvl = classify(size_kb[lang], repo_cnt[lang])
        buckets[lvl].append((lang, size_kb[lang], repo_cnt[lang]))

    rows: List[str] = []
    for lvl in ["Expert", "Advanced", "Intermediate", "Beginner", "Newbie"]:
        if lvl not in buckets:
            continue
        rows.append(f"### {lvl}")
        rows.append(
            " ".join(
                f"![{lang}]({lang_badge(lang, lvl)})"
                for lang, _, _ in sorted(
                    buckets[lvl],
                    key=lambda t: (t[1], t[2]),  # KB→Repos の順で降順
                    reverse=True,
                )
            )
        )
    return "\n\n".join(rows)


# ────────────────────────── Stats & Streak + Wakatime & Top-Langs
def stats_block() -> str:
    # 画像タグ生成ヘルパ
    def img(src: str, alt: str, w: str = "100%", extra: str = "") -> str:
        return f'<img src="{src}" alt="{alt}" width="{w}" align="top"{extra}>'

    # 行 1 ︙ Stats / Streak（48 % + 48 %）
    row1 = (
        '<p style="margin:0;">'
        f'{img("assets/stats.svg",  "stats",  "48%")}\n'
        f'{img("assets/streak-stats.svg", "streak", "48%")}'
        "</p>"
    )

    # 行 2 ︙ Activity graph（全幅）
    row2 = img("assets/activity-graph.svg", "activity")

    # 行 3 ︙ WakaTime / Top-Langs（48 % + 48 %）
    row3 = (
        '<p style="margin:0;">'
        f'{img("assets/wakatime.svg",       "wakatime", "48%")}\n'
        f'{img("assets/top-langs.svg",      "top langs", "48%")}'
        "</p>"
    )

    # 組み立て
    return f"{row1}\n<br/>\n{row2}\n<hr/>\n{row3}"


# ────────────────────────── メイン処理
def main() -> None:
    info = json.loads(Path("assets/info.json").read_text())
    repos = json.loads(Path("assets/repos.json").read_text())
    md = README.read_text()

    md = repl("badges", badges_row(), md)
    md = repl("hero", hero(info), md)
    md = repl("stack", build_stack(repos), md)
    md = repl("stats", stats_block(), md)

    # Trophy
    trophy_tag = f'<img src="assets/trophy.svg" alt="{OWNER} graph" width="99.8%"/>'
    md = repl("trophy", trophy_tag, md)

    # 更新日時
    ts = (datetime.now(timezone.utc) + timedelta(hours=9)).strftime(
        "%Y-%m-%d %H:%M JST"
    )
    md = repl("footer", f'<p align="right"><sup>⏰ Updated {ts}</sup></p>', md)

    README.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        exit(1)
