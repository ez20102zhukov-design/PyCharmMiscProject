from django.core.paginator import Paginator
from django.shortcuts import get_object_or_404, render

from igonews.models import IgromaniaArticle


def article_list(request):
    qs = IgromaniaArticle.objects.all()
    paginator = Paginator(qs, 12)
    page_obj = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "igonews_list.html",
        {"page_obj": page_obj},
    )


def article_detail(request, pk: int):
    article = get_object_or_404(IgromaniaArticle, pk=pk)
    return render(
        request,
        "igonews_detail.html",
        {"article": article},
    )
