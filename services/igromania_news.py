"""
Парсинг новостей Игромании: официальное API (как у Steam — HTTP + нормализация в dict).

Список: GET https://www.igromania.ru/api/v3/news/
Материал: GET https://www.igromania.ru/api/v3/news/{id}/

Публичные страницы вида /news/{id}/{slug}/
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

import requests

BASE_URL = "https://www.igromania.ru"
NEWS_API_LIST = f"{BASE_URL}/api/v3/news/"
# Сколько новостей запрашивать при `python -m services.igromania_news` (можно передать числом: `... igromania_news 30`)
CLI_DEFAULT_NEWS_LIMIT = 18

_DEFAULT_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def _headers() -> dict[str, str]:
    return {
        "User-Agent": _DEFAULT_UA,
        "Accept": "application/json",
    }


def _request_json(method: str, url: str, **kwargs: Any) -> dict[str, Any]:
    kwargs.setdefault("timeout", 25)
    kwargs.setdefault("headers", _headers())
    response = requests.request(method, url, **kwargs)
    response.raise_for_status()
    return response.json()


def _flatten_content(content: dict[str, Any] | None) -> str:
    if not content or not isinstance(content, dict):
        return ""
    parts: list[str] = []
    for block in content.get("data") or []:
        if not isinstance(block, dict):
            continue
        btype = block.get("type")
        bdata = block.get("data") or {}
        if btype == "text" and isinstance(bdata.get("text"), str):
            parts.append(bdata["text"])
        elif btype == "embed" and bdata.get("url"):
            parts.append(str(bdata["url"]))
    return "\n\n".join(parts).strip()


def _pic_origin(pic: Any) -> str:
    if not isinstance(pic, dict):
        return ""
    return (pic.get("origin") or pic.get("thumb") or "").strip()


def _release_from_pubdate(pubdate: str | None) -> str | None:
    if not pubdate or not isinstance(pubdate, str):
        return None
    # "2026-05-10T14:56:00+03:00" -> YYYY-MM-DD
    if len(pubdate) >= 10 and pubdate[4] == "-" and pubdate[7] == "-":
        return pubdate[:10]
    return None


def _article_url(news_id: int, slug: str = "") -> str:
    slug = (slug or "").strip().strip("/")
    if slug:
        return f"{BASE_URL}/news/{int(news_id)}/{slug}/"
    return f"{BASE_URL}/news/{int(news_id)}/"


_NEWS_ID_IN_PATH = re.compile(r"/news/(\d+)(?:/|$)")


def parse_news_id_from_url(url: str) -> int | None:
    """Извлекает числовой id из URL или пути вида .../news/123/..."""
    raw = (url or "").strip()
    if raw.isdigit():
        return int(raw)
    if "/news/" not in raw and raw.startswith("http"):
        return None
    if not raw.startswith("http"):
        raw = f"https://example.com{raw if raw.startswith('/') else '/' + raw}"
    path = urlparse(raw).path or ""
    m = _NEWS_ID_IN_PATH.search(path)
    if m:
        return int(m.group(1))
    return None


def normalize_list_item(item: dict[str, Any]) -> dict[str, Any]:
    """Одна запись из results (список новостей)."""
    news_id = item.get("id")
    slug = (item.get("slug") or "").strip()
    title = item.get("title") or ""
    snippet = item.get("snippet") or ""
    pubdate = item.get("pubdate")
    pic = _pic_origin(item.get("pic"))
    url = _article_url(int(news_id), slug) if news_id else ""
    return {
        "article_id": news_id,
        "slug": slug,
        "title": title,
        "description": snippet,
        "release": _release_from_pubdate(pubdate if isinstance(pubdate, str) else None),
        "image_url": pic,
        "article_url": url,
    }


def normalize_detail(payload: dict[str, Any]) -> dict[str, Any]:
    """Полный материал из GET /api/v3/news/{id}/."""
    news_id = payload.get("id")
    slug = (payload.get("slug") or "").strip()
    title = payload.get("title") or ""
    pubdate = payload.get("pubdate")
    pic = _pic_origin(payload.get("pic"))
    body = _flatten_content(payload.get("content"))
    snippet = (payload.get("snippet") or "").strip()
    description = body or snippet
    url = _article_url(int(news_id), slug) if news_id else ""
    return {
        "article_id": news_id,
        "slug": slug,
        "title": title,
        "description": description,
        "release": _release_from_pubdate(pubdate if isinstance(pubdate, str) else None),
        "image_url": pic,
        "article_url": url,
    }


def fetch_igromania_news_page(
    limit: int = 18,
    offset: int = 0,
    tags: str = "",
    verticals: str = "",
) -> dict[str, Any]:
    """
    Страница ленты (аналог открытию https://www.igromania.ru/news/ в браузере).

    Возвращает словарь API: count, next, previous, results;
    в results каждый элемент дополнительно доступен через normalize_list_item.
    """
    params = {
        "limit": max(1, min(int(limit), 100)),
        "offset": max(0, int(offset)),
        "tags": tags or "",
        "verticals": verticals or "",
    }
    return _request_json("GET", NEWS_API_LIST, params=params)


def get_igromania_news_detail(news_id: int) -> dict[str, Any]:
    """
    Полные данные новости по id (как get_steam_game_data по ссылке).

    Успех: поля title, description, release, image_url, article_url, article_id, slug.
    Ошибка: {"error": "..."}
    """
    try:
        nid = int(news_id)
    except (TypeError, ValueError):
        return {"error": "Некорректный id новости"}

    url = f"{NEWS_API_LIST}{nid}/"
    try:
        payload = _request_json("GET", url)
    except requests.HTTPError as e:
        if e.response is not None and e.response.status_code == 404:
            return {"error": f"Новость с id={nid} не найдена"}
        return {"error": f"Ошибка запроса к API Игромании: {e}"}
    except requests.RequestException as e:
        return {"error": f"Ошибка сети: {e}"}
    except ValueError as e:
        return {"error": f"Ошибка разбора JSON: {e}"}

    if not isinstance(payload, dict) or "id" not in payload:
        return {"error": "Неожиданный ответ API"}

    return normalize_detail(payload)


def get_igromania_news_from_source(raw_value: str) -> dict[str, Any]:
    """
    Точка входа «как Steam»: строка — числовой id, полный URL или путь /news/123/...

    Успех: тот же набор полей, что у get_igromania_news_detail.
    """
    raw = (raw_value or "").strip()
    if not raw:
        return {"error": "Пустое значение"}

    news_id = parse_news_id_from_url(raw)
    if news_id is None:
        return {
            "error": "Укажите id новости или ссылку вида https://www.igromania.ru/news/123/slug/",
        }

    return get_igromania_news_detail(news_id)


def list_normalized(
    limit: int = 18,
    offset: int = 0,
    tags: str = "",
    verticals: str = "",
) -> dict[str, Any]:
    """
    Лента с нормализованными элементами (удобно для UI).

    {"items": [...], "count": int, "next_offset": int | None, "previous_offset": int | None}
    или {"error": "..."}
    """
    try:
        page = fetch_igromania_news_page(
            limit=limit, offset=offset, tags=tags, verticals=verticals
        )
    except requests.RequestException as e:
        return {"error": f"Ошибка запроса: {e}"}
    except ValueError as e:
        return {"error": f"Ошибка разбора JSON: {e}"}

    results = page.get("results") or []
    if not isinstance(results, list):
        return {"error": "Поле results отсутствует или некорректно"}

    items = [normalize_list_item(x) for x in results if isinstance(x, dict)]
    count = page.get("count")
    lim = max(1, min(int(limit), 100))
    off = max(0, int(offset))
    next_off = off + lim if (isinstance(count, int) and off + lim < count) else None
    prev_off = off - lim if off > 0 else None

    return {
        "items": items,
        "count": count,
        "next_offset": next_off,
        "previous_offset": prev_off,
    }


if __name__ == "__main__":
    import json
    import sys

    limit = CLI_DEFAULT_NEWS_LIMIT
    if len(sys.argv) > 1:
        try:
            limit = max(1, min(int(sys.argv[1]), 100))
        except ValueError:
            print("Использование: python -m services.igromania_news [limit]", file=sys.stderr)
            sys.exit(2)

    print(f"=== Лента (limit={limit}) ===\n")
    batch = list_normalized(limit=limit, offset=0)
    if batch.get("error"):
        print(json.dumps(batch, ensure_ascii=False, indent=2))
    else:
        items = batch.get("items") or []
        print(f"Всего в базе (count): {batch.get('count')}, в ответе: {len(items)}\n")
        for i, item in enumerate(items, 1):
            print(f"{i}. {item.get('title')}")
            print(f"   {item.get('article_url')}\n")
        print("--- JSON ---\n")
        print(json.dumps(batch, ensure_ascii=False, indent=2))

    first_id = None
    if batch.get("items"):
        first_id = batch["items"][0].get("article_id")

    if first_id:
        print("\n=== Пример: полный материал id=%s ===\n" % first_id)
        detail = get_igromania_news_from_source(str(first_id))
        print(json.dumps(detail, ensure_ascii=False, indent=2))
