#!/usr/bin/env python3
"""从中文维基文库拉取纪传体正史全文，缓存为按卷切分的 JSON。

取渲染后的纯文本（`prop=extracts&explaintext`）而非 wikitext：文库的史记正文里
人名用 `{{ProperNoun|司馬光}}` 包、年份用 `{{YL|元豐三年}}` 包、缺字用
`{{SKchar|2593}}` 编码，直接剥模板会丢掉姓名、年号和生僻字；渲染文本已把这些
模板展开成原字。

用法：
    python scripts/corpus/01_fetchSources.py
    python scripts/corpus/01_fetchSources.py --books 宋史 明史 --force
"""

import argparse
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

API = "https://zh.wikisource.org/w/api.php"
USER_AGENT = "historia-course/0.1 (PKU text mining course project)"
WORKERS = 3
RETRY = 8
RETRY_SLEEP = 3
MIN_VOLUME_CHARS = 500

# 只收正卷，排除「(四庫全書本)」「全覽」「紀事本末」等同前缀页面
VOLUME_PAGE = re.compile(r"^[^/]+/卷[零一二三四五六七八九十百〇0-9]+[上下中]?$")

DEFAULT_BOOKS = ["宋史", "明史", "舊唐書", "新唐書"]
ROOT = Path(__file__).resolve().parents[2]


def api_get(params: dict) -> dict | None:
    url = API + "?" + urllib.parse.urlencode(dict(params, format="json"))
    for attempt in range(RETRY):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
            with urllib.request.urlopen(req, timeout=90) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except Exception:
            if attempt == RETRY - 1:
                return None
            time.sleep(RETRY_SLEEP * (attempt + 1))
    return None


def list_volume_titles(book: str) -> list[str]:
    titles, cont = [], None
    while True:
        params = {"action": "query", "list": "allpages", "apprefix": f"{book}/卷",
                  "aplimit": "500", "apnamespace": "0"}
        if cont:
            params["apcontinue"] = cont
        data = api_get(params)
        if data is None:
            raise RuntimeError(f"{book}: 卷目列表请求失败")
        titles += [p["title"] for p in data["query"]["allpages"]]
        if "continue" not in data:
            break
        cont = data["continue"]["apcontinue"]
    return sorted(t for t in titles if VOLUME_PAGE.match(t))


def fetch_volume(title: str) -> str | None:
    data = api_get({"action": "query", "prop": "extracts", "explaintext": "1",
                    "titles": title, "redirects": "1"})
    if data is None:
        return None
    page = list(data["query"]["pages"].values())[0]
    return page.get("extract") or None


def fetch_book(book: str, out_dir: Path, force: bool) -> dict[str, str]:
    target = out_dir / f"{book}.json"
    texts: dict[str, str] = {}
    if target.exists() and not force:
        texts = json.loads(target.read_text(encoding="utf-8"))
        sample = next(iter(texts.values()), "")
        if "{{" in sample:
            print(f"{book}: 缓存为旧版 wikitext，丢弃重拉")
            texts = {}
        else:
            print(f"{book}: 复用缓存 {len(texts)} 卷")

    titles = list_volume_titles(book)
    if not titles:
        raise RuntimeError(f"{book}: 未取到任何卷页")
    pending = [t for t in titles if t not in texts]
    print(f"{book}: 共 {len(titles)} 卷，待拉 {len(pending)} 卷", flush=True)
    if not pending:
        return texts

    failed: list[str] = []

    def collect(batch_title: str) -> None:
        text = fetch_volume(batch_title)
        if text:
            texts[batch_title] = text
        else:
            failed.append(batch_title)

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        for done, _ in enumerate(pool.map(collect, pending), 1):
            if done % 50 == 0:
                print(f"  {book} {done}/{len(pending)}", flush=True)

    # 并发下的偶发断连集中串行补一次，避免整批作废
    if failed:
        print(f"  {book} 首批失败 {len(failed)} 卷，串行重试", flush=True)
        again, failed = list(failed), []
        for i, title in enumerate(again, 1):
            time.sleep(0.5)
            text = fetch_volume(title)
            if text:
                texts[title] = text
            else:
                failed.append(title)
            if i % 25 == 0:
                print(f"  {book} 补拉 {i}/{len(again)}", flush=True)

    out_dir.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(texts, ensure_ascii=False), encoding="utf-8")
    total_kb = sum(len(v) for v in texts.values()) // 1024
    print(f"{book}: 已存 {len(texts)}/{len(titles)} 卷，正文 {total_kb} KB → {target.name}")

    if failed:
        # 缺的都是表（宰輔表、宗室世系表、諸王世表），渲染超时，且不含列传正文
        (out_dir / f"{book}.missing.json").write_text(
            json.dumps(sorted(failed), ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"  {book} 然缺 {len(failed)} 卷，多为表，已记入 {book}.missing.json")
    elif (out_dir / f"{book}.missing.json").exists():
        (out_dir / f"{book}.missing.json").unlink()
    thin = [t for t, v in texts.items() if len(v) < MIN_VOLUME_CHARS]
    if thin:
        print(f"  正文偏短（<{MIN_VOLUME_CHARS} 字）{len(thin)} 卷：{thin[:5]}")
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
