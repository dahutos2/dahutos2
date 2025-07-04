#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Profile 用 assets 生成スクリプト
- assets/info.json  : ユーザー名・Bio・ロケーション
- assets/repos.json : 言語ごとの総バイト数と該当リポジトリ数
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import textwrap
import time
import urllib.request
from typing import Dict, List

# 環境変数
OWNER = os.environ["OWNER"]
TOKEN = os.environ["GH_TOKEN_PRIVATE"]

# リクエストヘッダ
HEAD = {"Authorization": f"token {TOKEN}"}
GQLHEAD = {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}

# リポジトリルート
ROOT = pathlib.Path(__file__).resolve().parents[2]


# ---------- HTTP Utility ----------
def get(url: str) -> Dict:
    req = urllib.request.Request(url, headers=HEAD)
    with urllib.request.urlopen(req) as res:
        return json.load(res)


def gql(query: str) -> Dict:
    body = json.dumps({"query": textwrap.dedent(query)}).encode()
    req = urllib.request.Request(
        "https://api.github.com/graphql", data=body, headers=GQLHEAD
    )
    with urllib.request.urlopen(req) as res:
        return json.load(res)["data"]


# ---------- ユーザー情報の取得・保存 ----------
def save_user_info() -> None:
    user = get(f"https://api.github.com/users/{OWNER}")
    (ROOT / "assets").mkdir(exist_ok=True)
    (ROOT / "assets/info.json").write_text(
        json.dumps(
            {
                "name": user.get("name") or OWNER,
                "bio": user.get("bio") or "",
                "location": user.get("location") or "",
            },
            ensure_ascii=False,
        )
    )


# ---------- リポジトリ統計の収集 ----------
def collect_repo_stats() -> List[Dict]:
    """
    所有リポジトリを走査し、
    言語ごとのバイト数・該当リポジトリ数を集計
    """
    lang_info = collections.defaultdict(lambda: {"bytes": 0, "repos": 0})
    page = 1

    while True:
        repos = get(
            f"https://api.github.com/users/{OWNER}/repos"
            f"?type=owner&per_page=100&page={page}"
        )
        if not repos:
            break

        for repo in repos:
            if repo["fork"]:
                continue  # フォークは対象外
            process_repo(repo, lang_info)

        page += 1
        time.sleep(0.5)  # REST API レート制限緩和

    return [
        {"language": lang, "bytes": info["bytes"], "repos": info["repos"]}
        for lang, info in lang_info.items()
    ]


def process_repo(repo: Dict, lang_info: Dict) -> None:
    """
    単一リポジトリの言語バイト数・該当リポジトリ数を集計
    言語ごとに GraphQL codeCount を確認し、ファイル数10以上のリポジトリをカウント
    """
    langs = get(repo["languages_url"])
    if not langs:
        return

    # GraphQL クエリ生成
    queries = []
    for idx, lang in enumerate(langs.keys()):
        lq = lang.replace('"', '\\"')
        rq = repo["name"].replace('"', '\\"')
        queries.append(
            f"""
            L{idx}: search(query:"repo:{OWNER}/{rq} language:\\"{lq}\\"",
                          type:CODE, first:1) {{ codeCount }}
            """
        )

    # GraphQL 実行
    gql_res = gql("query{" + "".join(queries) + "}")

    # 集計処理
    for idx, (lang, b) in enumerate(langs.items()):
        lang_info[lang]["bytes"] += b
        if gql_res[f"L{idx}"]["codeCount"] >= 10:
            lang_info[lang]["repos"] += 1

    time.sleep(0.25)  # GraphQL レート制限緩和


# ---------- リポジトリ統計の保存 ----------
def save_repo_stats(data: List[Dict]) -> None:
    (ROOT / "assets/repos.json").write_text(json.dumps(data, ensure_ascii=False))


# ---------- メインエントリーポイント ----------
def main() -> None:
    """全処理を順次実行"""
    stats = collect_repo_stats()
    save_repo_stats(stats)


if __name__ == "__main__":
    main()
