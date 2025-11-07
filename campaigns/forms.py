# campaigns/forms.py
from django import forms
from .models import Campaign

class CampaignForm(forms.ModelForm):
    class Meta:
        model = Campaign
        fields = ['name', 'subject', 'content', 'scheduled_time']
        widgets = {
            'scheduled_time': forms.DateTimeInput(attrs={'type': 'datetime-local'}),
            'content': forms.Textarea(attrs={'rows': 10}),
        }

class RecipientUploadForm(forms.Form):
    file = forms.FileField(label="Upload CSV or Excel File")