from django.contrib import admin
from django import forms
from django.http import JsonResponse
from django.urls import path, reverse
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

    class Meta:
        model = GameInfo
        fields = '__all__'
    class Media:
        js = ("js/GameAdmin.js",)

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

    def process_value_view(self, request):
        if request.method != "POST":
            return JsonResponse({"error": "Only POST method is allowed."}, status=405)

        source_value = request.POST.get("source_value", "")
        processed_fields = self.process_generated_source(source_value)
        return JsonResponse({"fields": processed_fields})
