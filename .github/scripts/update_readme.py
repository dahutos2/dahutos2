#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
README 自動生成
  • Hero  : links は $PROFILE_LINKS (JSON)
  • Stack : 公開＋プライベート Repo でスコア計算
  • Stats/Contributions/Trophy : 埋め込み
"""
from __future__ import annotations
import json, os, re, urllib.request, collections
from pathlib import Path
from urllib.parse import quote_plus
from datetime import datetime, timezone, timedelta


# ---------- 基本 ----------
OWNER = os.getenv("OWNER", "")
ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"


# ---------- レベル ----------
SKILL_LEVELS = [(20, "Expert"), (10, "Advanced"), (5, "Intermediate"), (1, "Beginner")]
LEVEL_COLOR = {
    "Expert": "7E3AF2",
    "Advanced": "10B981",
    "Intermediate": "F59E0B",
    "Beginner": "EF4444",
    "Newbie": "9CA3AF",
}


# ---------- ロゴ色 ----------
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


# ---------- GitHub GraphQL ----------
API = "https://api.github.com/graphql"
HEAD = {"Authorization": f"bearer {os.getenv('GH_TOKEN_PRIVATE','')}"}

INFO_Q = """
query($login:String!){ user(login:$login){
  name bio location
}}"""
REPO_Q = """
query($after:String){
  viewer{ repositories(first:100, after:$after, ownerAffiliations:OWNER, isFork:false){
    nodes{
      stargazerCount
      primaryLanguage{ name }
    }
    pageInfo{ hasNextPage endCursor }
  }}
}"""


def gql(q: str, v: dict) -> dict:
    data = json.dumps({"query": q, "variables": v}).encode()
    req = urllib.request.Request(API, data, HEAD)
    with urllib.request.urlopen(req) as r:
        return json.load(r)


def user_info():
    return gql(INFO_Q, {"login": OWNER})["data"]["user"]


def repos_all():
    out, cur = [], None
    while True:
        r = gql(REPO_Q, {"after": cur})["data"]["viewer"]["repositories"]
        out += r["nodes"]
        if not r["pageInfo"]["hasNextPage"]:
            break
        cur = r["pageInfo"]["endCursor"]
    return out


# ---------- Helper ----------
def classify(score):
    for th, l, c in SKILL_LEVELS:
        if score >= th:
            return l, c
    return "Newbie", "9CA3AF"


def badge(lang, label):
    base = LOGO_COLOR.get(lang, "888888")
    return (
        f"https://img.shields.io/badge/{quote_plus(lang)}-{quote_plus(label)}-{base}"
        f"?logo={lang.lower().replace(' ','')}&logoColor=white&labelColor={LEVEL_COLOR[label]}"
    )


def repl(tag, new, text):
    p = rf"<!--START_SECTION:{tag}-->(.*?)<!--END_SECTION:{tag}-->"
    return re.sub(
        p,
        f"<!--START_SECTION:{tag}-->\n{new}\n<!--END_SECTION:{tag}-->",
        text,
        flags=re.S,
    )


# ---------- Markdown builders ----------
def hero_md(info):
    name = f'<h1 align="center">👋 {info["name"]}</h1>'
    user = f'<p align="center"><strong>@{OWNER}</strong></p>'

    # links
    link_data = json.loads(os.getenv("PROFILE_LINKS", "[]"))
    links = " ・ ".join(f'<a href="{d["url"]}">{d["title"]}</a>' for d in link_data)
    links_md = f'<p align="center">{links}</p>' if links else ""

    # intro
    intro = os.getenv("PROFILE_INTRO", "").strip()
    intro_md = f"<p>{intro}</p>" if intro else ""

    loc = info.get("location") or ""
    loc_md = f'<p align="center">📍 {loc}</p>' if loc else ""

    return "\n".join([name, user, links_md, intro_md, loc_md])


def stack_md(repos):
    cnt, star = collections.Counter(), collections.Counter()
    for r in repos:
        lang = r["primaryLanguage"]["name"] if r["primaryLanguage"] else None
        if not lang:
            continue
        cnt[lang] += 1
        star[lang] += r["stargazerCount"]
    score = {l: cnt[l] + star[l] / 10 for l in cnt}

    grouped = collections.defaultdict(list)
    for lang, val in score.items():
        grouped[classify(val)].append((lang, val))

    order = ["Expert", "Advanced", "Intermediate", "Beginner", "Newbie"]

    out = []
    for lvl in order:
        if lvl not in grouped:
            continue
        out.append(f"### {lvl}")
        badges = " ".join(
            badge(lang, lvl)
            for lang, _ in sorted(grouped[lvl], key=lambda t: t[1], reverse=True)
        )
        out.append(badges)
    return "\n\n".join(out)


def stats_md():
    return "\n\n".join(
        [
            f"![GitHub Stats Card](https://github-readme-stats.vercel.app/api?username={OWNER}&show_icons=true&count_private=true)",
            f"![Top Languages Card](https://github-readme-stats.vercel.app/api/top-langs/?username={OWNER}&layout=compact&hide=jupyter%20notebook)",
        ]
    )


def contrib_md():
    return f"![Contribution Graph](https://github-readme-activity-graph.cyclic.app/graph?username={OWNER}&theme=github)"


# ---------- main ----------
def main():
    info = user_info()
    repos = repos_all()
    md = README.read_text(encoding="utf-8")

    md = repl("hero", hero_md(info), md)
    md = repl("stack", stack_md(repos), md)
    md = repl("stats", stats_md(), md)
    md = repl("contrib", contrib_md(), md)
    md = repl(
        "trophy",
        f"[![trophy](https://github-profile-trophy.vercel.app/?username={OWNER})]"
        f"(https://github.com/ryo-ma/github-profile-trophy)",
        md,
    )

    jst = datetime.now(timezone.utc) + timedelta(hours=9)
    stamp = jst.strftime("%Y-%m-%d %H:%M JST")
    footer = f'<p align="right"><sup>⏰ Updated {stamp}</sup></p>'
    md = repl("footer", footer, md)

    README.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
