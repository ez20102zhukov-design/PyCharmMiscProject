from django import forms
from game.models import Review

class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['text', 'rating']
        widgets = {
            'text': forms.TextInput(attrs={'rows': 4, "placeholder": "Enter your review here..."}),
            'rating': forms.Select(choices=[(i, f"{i} ⭐") for i in range(1, 11)],),
        }