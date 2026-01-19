# forms.py
from django import forms
from .models import Review

class ReviewForm(forms.ModelForm):
    rating = forms.ChoiceField(
        choices=[(i, f"{i} Star{'s' if i > 1 else ''}") for i in range(1, 6)],
        widget=forms.HiddenInput()
    )

    class Meta:
        model = Review
        fields = ['comment', 'rating']
        widgets = {
            'comment': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Share your experience with this product...'
            }),
        }
    # Custom validation for the rating field
    def clean_rating(self):
        rating = self.cleaned_data.get('rating')
        if rating:
            return int(rating)
        raise forms.ValidationError("Please select a rating.")# for the rating field in the form