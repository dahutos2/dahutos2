#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Profile 用 assets 生成スクリプト
- assets/info.json  : ユーザー名・Bio・ロケーション
- assets/repos.json : 言語ごとの総バイト数と 該当リポジトリ数
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import textwrap
import time
import urllib.error
import urllib.request
from typing import Dict, List

# ────────────────────────── 環境変数
OWNER = os.getenv("OWNER")
TOKEN = os.getenv("GH_TOKEN_PRIVATE")

if not OWNER or not TOKEN:
    raise RuntimeError("環境変数 OWNER または GH_TOKEN_PRIVATE が未設定です。")

# ────────────────────────── HTTP ヘッダ
HEAD = {"Authorization": f"token {TOKEN}"}
GQLHEAD = {"Authorization": f"bearer {TOKEN}", "Content-Type": "application/json"}

# ────────────────────────── 定数
ROOT = pathlib.Path(__file__).resolve().parents[2]
FILE_THRESHOLD = 10  # ファイル数 10 未満は repos に加算しない
LANG_CHUNK = 20  # GraphQL 1 クエリで 20 言語まで送る
REST_SLEEP = 0.5  # REST API スリープ
GQL_SLEEP = 0.25  # GraphQL スリープ


# ────────────────────────── HTTP Utility
def rest_get(url: str) -> Dict:
    try:
        req = urllib.request.Request(url, headers=HEAD)
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"REST HTTPError {e.code}: {e.reason} → {url}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"REST URLError: {e.reason} → {url}")


def gql(query: str) -> Dict:
    body = json.dumps({"query": textwrap.dedent(query)}).encode()
    try:
        req = urllib.request.Request(
            "https://api.github.com/graphql", data=body, headers=GQLHEAD
        )
        with urllib.request.urlopen(req) as res:
            result = json.load(res)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"GQL HTTPError {e.code}: {e.reason}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"GQL URLError: {e.reason}")

    if "errors" in result:
        raise RuntimeError(f"GraphQL errors: {result['errors']}")
    if "data" not in result:
        raise RuntimeError(f"GraphQL response missing 'data': {result}")
    return result["data"]


# ────────────────────────── ユーザー情報
def save_user_info() -> None:
    user = rest_get(f"https://api.github.com/users/{OWNER}")
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


# ────────────────────────── リポジトリ統計
def collect_repo_stats() -> List[Dict]:
    lang_info = collections.defaultdict(lambda: {"bytes": 0, "repos": 0})
    page = 1

    while True:
        repos = rest_get(
            f"https://api.github.com/users/{OWNER}/repos"
            f"?type=owner&per_page=100&page={page}"
        )
        if not repos:
            break

        for repo in repos:
            if repo["fork"]:
                continue
            process_repo(repo, lang_info)

        page += 1
        time.sleep(REST_SLEEP)

    return [
        {"language": lang, "bytes": v["bytes"], "repos": v["repos"]}
        for lang, v in sorted(
            lang_info.items(),
            key=lambda t: (t[1]["bytes"], t[1]["repos"]),
            reverse=True,
        )
    ]


def process_repo(repo: Dict, lang_info: Dict) -> None:
    langs = rest_get(repo["languages_url"])
    if not langs:
        return

    # 言語リストを LANG_CHUNK ごとに分割
    lang_items = list(langs.items())
    for chunk_start in range(0, len(lang_items), LANG_CHUNK):
        chunk = lang_items[chunk_start : chunk_start + LANG_CHUNK]

        # GraphQL クエリ組み立て
        queries = []
        for idx, (lang, _) in enumerate(chunk):
            lq = lang.replace('"', '\\"')
            rq = repo["name"].replace('"', '\\"')
            queries.append(
                f"""
                L{idx}: search(
                  query:"repo:{OWNER}/{rq} language:\\\"{lq}\\\"",
                  type:CODE, first:1) {{ codeCount }}
                """
            )

        data = gql("query{" + "".join(queries) + "}")

        # 集計
        for idx, (lang, bytes_) in enumerate(chunk):
            lang_info[lang]["bytes"] += bytes_
            if data[f"L{idx}"]["codeCount"] >= FILE_THRESHOLD:
                lang_info[lang]["repos"] += 1

        time.sleep(GQL_SLEEP)


# ────────────────────────── 保存
def save_repo_stats(rows: List[Dict]) -> None:
    (ROOT / "assets/repos.json").write_text(json.dumps(rows, ensure_ascii=False))


# ────────────────────────── Main
def main() -> None:
    save_user_info()
    stats = collect_repo_stats()
    save_repo_stats(stats)


if __name__ == "__main__":
    try:
        main()
        print("✅ assets 生成完了")
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        exit(1)
