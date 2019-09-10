from django import forms

class LocationForm(forms.Form):
    location = forms.CharField(label='Your Location', max_length=200)
