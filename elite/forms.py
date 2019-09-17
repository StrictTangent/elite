from django import forms

class LocationForm(forms.Form):
    location = forms.CharField(label='Reference System', initial="Sol", max_length=200)
    radius = forms.IntegerField(label='Radius', initial = 30, min_value=0, max_value=100)
