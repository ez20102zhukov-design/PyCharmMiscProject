"""Внешние сервисы парсинга и интеграций (отдельно от Django-приложений)."""

from .igromania_news import (
    get_igromania_news_detail,
    get_igromania_news_from_source,
    fetch_igromania_news_page,
)

__all__ = [
    "fetch_igromania_news_page",
    "get_igromania_news_detail",
    "get_igromania_news_from_source",
]
