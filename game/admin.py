from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path, reverse
from django.core.files.base import ContentFile
from urllib.parse import urlparse
import os
import uuid

import requests
from game.models import GameInfo



from ScriptsInfo import Parsing4gameinfo

# Register your models here.
class GameInfoForm(forms.ModelForm):

    generated_source = forms.CharField(
        required=False,
        label='Ссылку для обработки',
        help_text='Введите значение и нажмите на кнопку',
        widget=forms.TextInput(
            attrs={
                "id": "id_generated_source",
                "placeholder": "Введите текст"

            }
        )
    )
    generated_image_url = forms.CharField(
        required=False,
        widget=forms.HiddenInput(
            attrs={
                "id": "id_generated_image_url",
            }
        ),
    )

    class Meta:
        model = GameInfo
        fields = '__all__'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Файл подставляется в save_model из generated_image_url; браузер не может заполнить type=file.
        self.fields["image_url"].required = False

    def clean(self):
        cleaned_data = super().clean()
        uploaded = cleaned_data.get("image_url")
        has_upload = bool(getattr(uploaded, "name", None) or uploaded)
        gen_url = (cleaned_data.get("generated_image_url") or "").strip()
        try:
            has_existing = bool(self.instance.pk and self.instance.image_url.name)
        except ValueError:
            has_existing = False

        if not has_upload and not gen_url and not has_existing:
            self.add_error(
                "image_url",
                "Загрузите файл, либо нажмите «Обработать…» чтобы подтянуть обложку со Steam.",
            )
        return cleaned_data

    class Media:
        js = ("js/GameAdmin.js",)

    def clean_steam_url(self):
        steam_url = self.cleaned_data.get("steam_url")
        if not steam_url:
            return steam_url
        coreset = GameInfo.objects.filter(steam_url=steam_url)
        if self.instance.pk:
            coreset = coreset.exclude(pk=self.instance.pk)
        if coreset.exists():
            raise forms.ValidationError(f"АЩИПКА, ЕСТЬ ИГРА ID={coreset.first().pk}")
        return steam_url

@admin.register(GameInfo,)
class GameInfoAdmin(admin.ModelAdmin):
    form = GameInfoForm
    fieldsets = (
        (
            "Обработка значения",
            {
                "fields": ("generated_source",),
                "description": (
                    '<button type="button" class="button" id="apply-generated-value">'
                    "Обработать и вставить в Название"
                    "</button>"
                ),
            },
        ),
        (None, {"fields": ("generated_image_url",)}),
        (None, {"fields":  ("title", "rating", "release", "description", "steam_url", "image_url", )}),
    )

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                "process-value/",
                self.admin_site.admin_view(self.process_value_view),
                name="games_game_process_value",
            ),
        ]
        return custom_urls + urls

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        generated_source_field = form.base_fields.get("generated_source")
        if generated_source_field:
            generated_source_field.widget.attrs["data-process-url"] = reverse(
                "admin:games_game_process_value"
            )
        return form

    def process_generated_source(self, raw_value):
        """
        Ожидаемый контракт для будущей функции game_get_info(url):
        - str: тогда заполним только title
        - dict: можно вернуть поля title/raing/date
        """
        try:
            parsinggi = Parsing4gameinfo
        except ImportError:
            return {"title": raw_value}

        data = parsinggi.get_steam_game_data(raw_value)
        if isinstance(data, dict):
            allowed_fields = {"title", "rating", "release", "description", "steam_url", "image_url", }
            print ({key: value for key, value in data.items() if key in allowed_fields})
            return {key: value for key, value in data.items() if key in allowed_fields}
        return {"title": str(data)}

    def _save_image_from_url(self, obj, image_url):
        image_url = (image_url or "").strip()
        if not image_url:
            return

        parsed = urlparse(image_url)
        name_from_path = os.path.basename(parsed.path) or ""
        ext = os.path.splitext(name_from_path)[1] or ".jpg"
        filename = f"generated_{uuid.uuid4().hex}{ext}"

        if image_url.startswith("file://"):
            image_url = image_url[7:]

        if os.path.isfile(image_url):
            with open(image_url, "rb") as fh:
                content = fh.read()
        else:
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
            }
            response = requests.get(image_url, timeout=25, headers=headers)
            response.raise_for_status()
            content = response.content

        obj.image_url.save(filename, ContentFile(content), save=False)

    def process_value_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "Only POST method is allowed."}, status=405)

        source_value = request.POST.get("source_value", "")
        processed_fields = self.process_generated_source(source_value)
        return JsonResponse({"fields": processed_fields})

    def save_model(self, request, obj, form, change):
        generated_image_url = form.cleaned_data.get("generated_image_url", "")
        if generated_image_url:
            try:
                self._save_image_from_url(obj, generated_image_url)
            except Exception as exc:
                self.message_user(
                    request,
                    f"Не удалось скачать изображение: {exc}",
                    level="warning",
                )
        super().save_model(request, obj, form, change)
