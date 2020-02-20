from django import forms
from .models import *


class UploadFileForm(forms.ModelForm):
    # title = forms.CharField(max_length=50)
    # file = forms.FileField()

    class Meta:
        model = Upload
        fields = ['file', ]