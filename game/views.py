from django.db.models import Avg, Count
from django.shortcuts import render, redirect
from game.forms import ReviewForm
from game.models import GameInfo, Review


# Create your views here.
def game_news(request):
    game= GameInfo.objects.all()
    print(game[0].title)
    return render(request, 'gamenews.html', {'games': game})
def game_detail(request, game_id):
    game = GameInfo.objects.get(id=game_id)
    reviews = Review.objects.filter(game=game)
    avg = reviews.aggregate(Avg_rating = Avg('rating'), reviews_total = Count('id'))
    reviews_total = avg['reviews_total']
    reviews_avg = avg['Avg_rating']
    print(avg)
    user_already = (request.user.is_authenticated and Review.objects.filter(user=request.user).exists())
    if request.method == 'POST':
        if not request.user.is_authenticated:
            return redirect("login")
        form = ReviewForm(request.POST)
        if form.is_valid():
            if reviews.filter(game=game).exists():
                form.add_error(None, "Ащипка, повторный отзыв")
            else:
                review = form.save(commit=False)
                review.game = game
                review.user = request.user
                review.save()
    else:
        form = ReviewForm()
    return render(request, 'gamedetail.html',
                  {'game': game,
                   'reviews': reviews,
                   'form': form,
                   'reviews_avg': reviews_avg,
                   'reviews_total': reviews_total,
                   'user_already_reviwed': user_already
                   })
