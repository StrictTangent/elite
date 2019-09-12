from django import forms

class LocationForm(forms.Form):
    location = forms.CharField(label='Reference System', max_length=200)
