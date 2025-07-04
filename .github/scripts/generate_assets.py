#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Profile 用 assets 生成スクリプト
- assets/info.json  : ユーザー名・Bio・ロケーション
- assets/repos.json : 言語ごとの総バイト数と該当リポジトリ数
                      （そのリポジトリで当該言語のファイル数が10以上のとき repos++）
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List

# ────────────────────────── 環境変数
OWNER = os.getenv("OWNER")
TOKEN = os.getenv("GH_TOKEN_PRIVATE")
if not OWNER or not TOKEN:
    raise RuntimeError("ENV OWNER / GH_TOKEN_PRIVATE が未設定です。")

# ────────────────────────── 共通設定
HEAD = {"Authorization": f"token {TOKEN}"}
ROOT = pathlib.Path(__file__).resolve().parents[2]
REST_SLEEP = 1.1  # Code Search は 1req/秒まで
FILE_THRESHOLD = 10


# ────────────────────────── HTTP Util
def rest_get(url: str, *, retry: int = 3) -> Dict:
    for attempt in range(retry):
        try:
            req = urllib.request.Request(url, headers=HEAD)
            with urllib.request.urlopen(req) as res:
                return json.load(res)
        except urllib.error.HTTPError as e:
            # 5xx のみリトライ
            if e.code >= 500 and attempt < retry - 1:
                time.sleep(2**attempt)
                continue
            raise RuntimeError(f"HTTPError {e.code}: {e.reason} -> {url}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"URLError: {e.reason} -> {url}")
    raise RuntimeError("Exceeded retry limit")


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


# ────────────────────────── Code Search でファイル数を取得
def code_count(repo: str, lang: str) -> int:
    q = urllib.parse.quote_plus(f"repo:{OWNER}/{repo} language:{lang}")
    url = f"https://api.github.com/search/code?q={q}&per_page=1"
    resp = rest_get(url)
    return resp.get("total_count", 0)


# ────────────────────────── リポジトリ統計
def collect_repo_stats() -> List[Dict]:
    lang_info = collections.defaultdict(lambda: {"bytes": 0, "repos": 0})
    page = 1
    while True:
        repos = rest_get(
            f"https://api.github.com/users/{OWNER}/repos?type=owner&per_page=100&page={page}"
        )
        if not repos:
            break

        for repo in repos:
            if repo["fork"]:
                continue
            process_repo(repo, lang_info)
        page += 1
        time.sleep(REST_SLEEP)  # REST list 呼び出し

    # bytes 降順→repos 降順で並べ替え
    return [
        {"language": l, "bytes": v["bytes"], "repos": v["repos"]}
        for l, v in sorted(
            lang_info.items(),
            key=lambda t: (t[1]["bytes"], t[1]["repos"]),
            reverse=True,
        )
    ]


def process_repo(repo: Dict, lang_info: Dict) -> None:
    langs = rest_get(repo["languages_url"])
    if not langs:
        return

    for lang, bytes_ in langs.items():
        # Code Search （1 req / 言語）
        cnt = code_count(repo["name"], lang)
        time.sleep(REST_SLEEP)

        lang_info[lang]["bytes"] += bytes_
        if cnt >= FILE_THRESHOLD:
            lang_info[lang]["repos"] += 1


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
