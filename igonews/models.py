from django.db import models
from django.urls import reverse


class IgromaniaArticle(models.Model):
    """Локальная копия новости с Игромании (источник: API v3/news)."""

    igromania_id = models.PositiveIntegerField("ID на Игромании", unique=True, db_index=True)
    slug = models.SlugField(max_length=320, blank=True)
    title = models.CharField("Заголовок", max_length=500)
    description = models.TextField("Текст", blank=True)
    release_date = models.DateField("Дата публикации", null=True, blank=True)
    source_url = models.URLField("Ссылка на материал", max_length=600)
    external_image_url = models.URLField("URL обложки (CDN)", max_length=600, blank=True)
    cover = models.ImageField("Обложка", upload_to="news/", blank=True, null=True)
    created_at = models.DateTimeField("Создано", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлено", auto_now=True)

    class Meta:
        ordering = ("-release_date", "-igromania_id")
        verbose_name = "Новость Игромании"
        verbose_name_plural = "Новости Игромании"

    def __str__(self) -> str:
        return f"{self.igromania_id}: {self.title[:80]}"

    def get_absolute_url(self) -> str:
        return reverse("igonews_detail", kwargs={"pk": self.pk})

    def display_image_url(self) -> str:
        if self.cover:
            return self.cover.url
        return self.external_image_url or ""
