#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
README 自動生成
  • Hero  : links は $PROFILE_LINKS (JSON) > Twitter の優先順
  • Stack : 公開＋プライベート Repo でスコア計算
  • Stats/Trophy : キャッシュ SVG 埋め込み
"""
from __future__ import annotations
import json, os, re, time, hashlib, urllib.request, collections
from pathlib import Path

USER = "dahutos2"
ROOT = Path(__file__).resolve().parents[2]
README = ROOT / "README.md"

# ■ スキルレベル定義
SKILL_LEVELS = [
    (20, "Expert", "7E3AF2"),
    (10, "Advanced", "10B981"),
    (5, "Intermediate", "F59E0B"),
    (1, "Beginner", "EF4444"),
]
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

# ■ GraphQL
API = "https://api.github.com/graphql"
HEAD = {"Authorization": f"bearer {os.getenv('GH_TOKEN_PRIVATE','')}"}

INFO_Q = """
query($login:String!){ user(login:$login){
  name bio twitterUsername
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
    return gql(INFO_Q, {"login": USER})["data"]["user"]


def repos_all():
    out, cur = [], None
    while True:
        r = gql(REPO_Q, {"after": cur})["data"]["viewer"]["repositories"]
        out += r["nodes"]
        if not r["pageInfo"]["hasNextPage"]:
            break
        cur = r["pageInfo"]["endCursor"]
    return out


# ■ Build sections
def hero_md(info):
    name = f'<h1 align="center">{info["name"]} ({USER})</h1>'
    bio = info["bio"].replace("\n", " ") if info["bio"] else ""
    # links: Environment var > Twitter
    links_json = os.getenv("PROFILE_LINKS", "")
    links = []
    if links_json:
        try:
            data = json.loads(links_json)
            links = [f'<a href="{d["url"]}">{d["title"]}</a>' for d in data]
        except Exception:
            pass
    elif info["twitterUsername"]:
        links = [f'<a href="https://twitter.com/{info["twitterUsername"]}">Twitter</a>']
    line = " ・ ".join(links)
    body = f'<p align="center">{bio}<br/>{line}</p>' if (bio or links) else ""
    return f"{name}\n{body}"


def classify(score):
    for th, l, c in SKILL_LEVELS:
        if score >= th:
            return l, c
    return "Newbie", "9CA3AF"


def badge(lang, label, lblcol):
    from urllib.parse import quote_plus

    base = LOGO_COLOR.get(lang, "888888")
    return (
        f"https://img.shields.io/badge/{quote_plus(lang)}-{quote_plus(label)}-{base}"
        f"?logo={lang.lower().replace(' ','')}&logoColor=white&labelColor={lblcol}"
    )


def stack_md(repos):
    # 言語スコアの上位10件をバッジ化
    cnt, star = collections.Counter(), collections.Counter()
    for r in repos:
        lang = r["primaryLanguage"]["name"] if r["primaryLanguage"] else None
        if not lang:
            continue
        cnt[lang] += 1
        star[lang] += r["stargazerCount"]
    score = {l: cnt[l] + star[l] / 10 for l in cnt}
    top = sorted(score.items(), key=lambda t: t[1], reverse=True)[:10]
    return " ".join(f"![{l}]({badge(l,*classify(s))})" for l, s in top)


def svg(path, alt):
    h = hashlib.md5((ROOT / path).read_bytes()).hexdigest()
    return f'<img src="{path}?v={h}" alt="{alt}" width="450px"/>'


def stats_md():
    owner = os.getenv("OWNER")
    return "\n\n".join(
        [
            f"![GitHub Stats Card](https://github-readme-stats.vercel.app/api?username={owner}&show_icons=true&count_private=true)",
            f"![Top Languages Card](https://github-readme-stats.vercel.app/api/top-langs/?username={owner}&layout=compact&hide=jupyter%20notebook)",
        ]
    )


# ■ Replace helper
def repl(tag, new, text):
    p = rf"<!--START_SECTION:{tag}-->(.*?)<!--END_SECTION:{tag}-->"
    return re.sub(
        p,
        f"<!--START_SECTION:{tag}-->\n{new}\n<!--END_SECTION:{tag}-->",
        text,
        flags=re.S,
    )


def main():
    info = user_info()
    repos = repos_all()
    md = README.read_text(encoding="utf-8")
    md = repl("hero", hero_md(info), md)
    md = repl("stack", stack_md(repos), md)
    md = repl("stats", stats_md(), md)
    md = repl(
        "trophy",
        f'[![trophy](https://github-profile-trophy.vercel.app/?username={os.getenv("OWNER")})]'
        f"(https://github.com/ryo-ma/github-profile-trophy)",
        md,
    )
    from datetime import datetime, timezone, timedelta

    jst = datetime.now(timezone.utc) + timedelta(hours=9)
    stamp = jst.strftime("%Y-%m-%d %H:%M JST")
    footer = f'<p align="right"><sup>⏰ Updated {stamp}</sup></p>'
    md += f"\n\n{footer}\n"
    README.write_text(md, encoding="utf-8")


if __name__ == "__main__":
    main()
