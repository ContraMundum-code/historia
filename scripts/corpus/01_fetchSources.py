#!/usr/bin/env python3
"""从中文维基文库拉取纪传体正史全文，缓存为按卷切分的 JSON。

底本选择依据：二十四史全文在维基文库属公有领域，MediaWiki API 无需鉴权，
每个卷页即一个 MediaWiki 页面，按卷落盘后可在本地反复重建人物索引，避免
重复请求。

用法：
    python scripts/corpus/01_fetchSources.py
    python scripts/corpus/01_fetchSources.py --books 宋史 明史 --force
"""

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "historia-course/0.1 (PKU text mining course project)"
BATCH = 50
WORKERS = 6
RETRY = 3

# 只收正卷，排除「(四庫全書本)」「全覽」「紀事本末」等同前缀页面
VOLUME_PAGE = re.compile(r"^[^/]+/卷[零一二三四五六七八九十百〇0-9]+[上下中]?$")

DEFAULT_BOOKS = ["宋史", "明史", "舊唐書", "新唐書"]
ROOT = Path(__file__).resolve().parents[2]


def api_get(params: dict) -> dict:
    params = dict(params, format="json")
    url = API + "?" + urllib.parse.urlencode(params)
    last_error = None
    for _ in range(RETRY):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception as exc:  # 网络抖动重试，三次仍失败则抛出
            last_error = exc
    raise RuntimeError(f"请求失败：{url}") from last_error


def list_volume_titles(book: str) -> list[str]:
    titles, cont = [], None
    while True:
        params = {"action": "query", "list": "allpages", "apprefix": f"{book}/卷",
                  "aplimit": "500", "apnamespace": "0"}
        if cont:
            params["apcontinue"] = cont
        data = api_get(params)
        titles += [p["title"] for p in data["query"]["allpages"]]
        if "continue" not in data:
            break
        cont = data["continue"]["apcontinue"]
    return sorted(t for t in titles if VOLUME_PAGE.match(t))


def fetch_wikitext(titles: list[str]) -> dict[str, str]:
    data = api_get({"action": "query", "prop": "revisions", "rvprop": "content",
                    "rvslots": "main", "titles": "|".join(titles)})
    out = {}
    for page in data["query"]["pages"].values():
        if "revisions" not in page:
            continue
        out[page["title"]] = page["revisions"][0]["slots"]["main"]["*"]
    return out


def fetch_book(book: str, out_dir: Path, force: bool) -> dict[str, str]:
    target = out_dir / f"{book}.json"
    if target.exists() and not force:
        texts = json.loads(target.read_text(encoding="utf-8"))
        print(f"{book}: 命中缓存 {len(texts)} 卷 → {target}")
        return texts

    titles = list_volume_titles(book)
    if not titles:
        raise RuntimeError(f"{book}: 未取到任何卷页")
    batches = [titles[i:i + BATCH] for i in range(0, len(titles), BATCH)]
    texts: dict[str, str] = {}
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for done, part in enumerate(pool.map(fetch_wikitext, batches), 1):
            texts.update(part)
            print(f"  {book} 批次 {done}/{len(batches)}，累计 {len(texts)} 卷", flush=True)

    missing = [t for t in titles if t not in texts]
    if missing:
        raise RuntimeError(f"{book}: {len(missing)} 卷未取到 → {missing[:5]}")
    assert len(texts) == len(titles), f"{book}: 卷数不一致 {len(texts)} != {len(titles)}"

    out_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    total_kb = sum(len(v) for v in texts.values()) // 1024
    print(f"{book}: {len(texts)} 卷，正文 {total_kb} KB → {target}")
    return texts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--books", nargs="+", default=DEFAULT_BOOKS)
    parser.add_argument("--out", type=Path, default=ROOT / ".scratch" / "sources")
    parser.add_argument("--force", action="store_true", help="忽略缓存重新下载")
    args = parser.parse_args()

    ok, failed = 0, []
    for book in args.books:
        try:
            fetch_book(book, args.out, args.force)
            ok += 1
        except Exception as exc:
            failed.append((book, str(exc)))
    print(f"\n完成 {ok}/{len(args.books)} 部")
    for book, err in failed:
        print(f"  失败 {book}: {err}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
