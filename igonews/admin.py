import os
import uuid
from datetime import date, datetime
from typing import Optional
from urllib.parse import urlparse

from django import forms
from django.contrib import admin, messages
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.urls import path, reverse
import requests

from igonews.models import IgromaniaArticle
from services.igromania_news import (
    fetch_igromania_news_page,
    get_igromania_news_detail,
    get_igromania_news_from_source,
    normalize_list_item,
)


def _parse_release_date(value) -> Optional[date]:
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    s = str(value).strip()[:10]
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


class IgromaniaArticleForm(forms.ModelForm):
    generated_source = forms.CharField(
        required=False,
        label="Ссылка или id новости",
        help_text="URL вида /news/123/... или числовой id. Нажмите «Подтянуть с API».",
        widget=forms.TextInput(
            attrs={
                "id": "id_generated_source",
                "placeholder": "https://www.igromania.ru/news/123/slug/",
            }
        ),
    )
    generated_image_url = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={"id": "id_generated_image_url"}),
    )

    class Meta:
        model = IgromaniaArticle
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["cover"].required = False

    class Media:
        js = ("js/NewsAdmin.js",)


@admin.register(IgromaniaArticle)
class IgromaniaArticleAdmin(admin.ModelAdmin):
    form = IgromaniaArticleForm
    list_display = (
        "igromania_id",
        "title",
        "release_date",
        "updated_at",
    )
    list_filter = ("release_date",)
    search_fields = ("title", "description", "slug", "source_url")
    readonly_fields = ("created_at", "updated_at")
    actions = ("action_sync_feed", "action_refresh_full_text")

    fieldsets = (
        (
            "Импорт с Игромании",
            {
                "fields": ("generated_source",),
                "description": (
                    '<button type="button" class="button" id="apply-generated-value">'
                    "Подтянуть с API"
                    "</button>"
                ),
            },
        ),
        (None, {"fields": ("generated_image_url",)}),
        (
            None,
            {
                "fields": (
                    "igromania_id",
                    "slug",
                    "title",
                    "release_date",
                    "source_url",
                    "external_image_url",
                    "cover",
                    "description",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom = [
            path(
                "process-value/",
                self.admin_site.admin_view(self.process_value_view),
                name="igonews_igromaniaarticle_process_value",
            ),
        ]
        return custom + urls

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        gf = form.base_fields.get("generated_source")
        if gf:
            gf.widget.attrs["data-process-url"] = reverse(
                "admin:igonews_igromaniaarticle_process_value"
            )
        return form

    def process_generated_source(self, raw_value: str):
        data = get_igromania_news_from_source(raw_value)
        if not isinstance(data, dict) or data.get("error"):
            err = data.get("error") if isinstance(data, dict) else "Неизвестная ошибка"
            return {"error": err}

        if data.get("article_id") is None:
            return {"error": "В ответе API нет id материала"}

        img = (data.get("image_url") or "").strip()
        slug = (data.get("slug") or "").strip()[:320]
        return {
            "title": data.get("title") or "",
            "description": data.get("description") or "",
            "release_date": data.get("release") or "",
            "source_url": data.get("article_url") or "",
            "igromania_id": data.get("article_id"),
            "slug": slug,
            "external_image_url": img[:600],
            "cover": img,
        }

    def _save_cover_from_url(self, obj, image_url: str):
        image_url = (image_url or "").strip()
        if not image_url:
            return
        parsed = urlparse(image_url)
        name_from_path = os.path.basename(parsed.path) or ""
        ext = os.path.splitext(name_from_path)[1] or ".jpg"
        filename = f"news_{uuid.uuid4().hex}{ext}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        }
        response = requests.get(image_url, timeout=25, headers=headers)
        response.raise_for_status()
        obj.cover.save(filename, ContentFile(response.content), save=False)

    def process_value_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "Only POST method is allowed."}, status=405)
        source_value = request.POST.get("source_value", "")
        processed = self.process_generated_source(source_value)
        if processed.get("error"):
            return JsonResponse({"error": processed["error"]}, status=400)
        fields = {k: v for k, v in processed.items() if k != "error"}
        return JsonResponse({"fields": fields})

    def save_model(self, request, obj, form, change):
        gen_img = (form.cleaned_data.get("generated_image_url") or "").strip()
        if gen_img:
            try:
                self._save_cover_from_url(obj, gen_img)
            except Exception as exc:
                self.message_user(
                    request,
                    f"Не удалось скачать обложку: {exc}",
                    level=messages.WARNING,
                )
        super().save_model(request, obj, form, change)

    @admin.action(description="Синхронизировать ленту с Игромании (до 250 новостей)")
    def action_sync_feed(self, request, queryset):
        total = 0
        offset = 0
        limit = 50
        pages_max = 5
        for _ in range(pages_max):
            try:
                page = fetch_igromania_news_page(limit=limit, offset=offset)
            except Exception as exc:
                self.message_user(
                    request,
                    f"Ошибка API: {exc}",
                    level=messages.ERROR,
                )
                return
            results = page.get("results") or []
            if not results:
                break
            for raw in results:
                if not isinstance(raw, dict):
                    continue
                item = normalize_list_item(raw)
                aid = item.get("article_id")
                src = (item.get("article_url") or "").strip()
                if not aid or not src:
                    continue
                IgromaniaArticle.objects.update_or_create(
                    igromania_id=int(aid),
                    defaults={
                        "title": item.get("title") or "",
                        "description": item.get("description") or "",
                        "release_date": _parse_release_date(item.get("release")),
                        "source_url": src[:600],
                        "slug": (item.get("slug") or "")[:320],
                        "external_image_url": (item.get("image_url") or "")[:600],
                    },
                )
                total += 1
            offset += limit
            count = page.get("count")
            if isinstance(count, int) and offset >= count:
                break
        self.message_user(request, f"Синхронизировано записей: {total}.")

    @admin.action(description="Обновить полный текст выбранных (API по id)")
    def action_refresh_full_text(self, request, queryset):
        updated = 0
        for obj in queryset:
            data = get_igromania_news_detail(obj.igromania_id)
            if data.get("error"):
                continue
            obj.description = data.get("description") or ""
            obj.title = data.get("title") or obj.title
            obj.release_date = _parse_release_date(data.get("release")) or obj.release_date
            ext = (data.get("image_url") or "").strip()
            if ext:
                obj.external_image_url = ext[:600]
            obj.save()
            updated += 1
        self.message_user(request, f"Обновлено материалов: {updated}.")
