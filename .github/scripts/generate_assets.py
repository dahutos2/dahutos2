#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Profile 用 assets 生成スクリプト
- assets/info.json : ユーザー名・Bio・ロケーション
- assets/repos.json : 言語ごとの総バイト数と該当リポジトリ数
"""
from __future__ import annotations

import collections
import json
import os
import pathlib
import time
import urllib.error
import urllib.request
from typing import Dict, List

# ─────────────── 環境
OWNER = os.getenv("OWNER")
TOKEN = os.getenv("GH_TOKEN_PRIVATE")
if not OWNER or not TOKEN:
    raise RuntimeError("ENV OWNER / GH_TOKEN_PRIVATE が未設定です。")

HEAD = {"Authorization": f"token {TOKEN}"}
ROOT = pathlib.Path(__file__).resolve().parents[2]
REST_SLEEP = 0.5

# 仮の平均ファイルサイズ (bytes) を定義（例えば 1KB と仮定）
AVG_FILE_SIZE = 1024
FILE_THRESHOLD = 10


# ─────────────── HTTP
def rest_get(url: str) -> Dict:
    try:
        req = urllib.request.Request(url, headers=HEAD)
        with urllib.request.urlopen(req) as res:
            return json.load(res)
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTPError {e.code}: {e.reason} -> {url}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"URLError: {e.reason} -> {url}")


# ─────────────── ユーザー情報
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


# ─────────────── リポジトリ統計
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
            if repo.get("fork"):
                continue
            process_repo(repo, lang_info)

        page += 1
        time.sleep(REST_SLEEP)

    return [
        {"language": lang, "bytes": info["bytes"], "repos": info["repos"]}
        for lang, info in sorted(
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
        lang_info[lang]["bytes"] += bytes_
        # 仮想ファイル数 = bytes / 平均ファイルサイズ
        approx_file_count = bytes_ / AVG_FILE_SIZE
        if approx_file_count >= FILE_THRESHOLD:
            lang_info[lang]["repos"] += 1

    time.sleep(REST_SLEEP)


# ─────────────── 保存
def save_repo_stats(data: List[Dict]) -> None:
    (ROOT / "assets/repos.json").write_text(json.dumps(data, ensure_ascii=False))


# ─────────────── メイン
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
