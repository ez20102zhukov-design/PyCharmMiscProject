from django.shortcuts import render

from game.models import GameInfo


# Create your views here.
def game_news(request):
    game= GameInfo.objects.all()
    print(game[0].title)
    return render(request, 'gamenews.html', {'games': game})
def game_detail(request, game_id):
    game = GameInfo.objects.get(id=game_id)
    return render(request, 'gamedetail.html', {'game': game})
