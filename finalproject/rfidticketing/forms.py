# myapp/forms.py

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from .models import *

class RegistrationForm(UserCreationForm):
    age = forms.IntegerField(required=True)
    phone_number = forms.CharField(max_length=10, required=True)
    class Meta:
        model = User
        fields = ['username', 'password1', 'password2', 'age']

class RechargeForm(forms.Form):
    amount = forms.DecimalField(max_digits=10, decimal_places=2)

class TransactionForm(forms.ModelForm):
    class Meta:
        model=RFIDCardLog
        exclude=['user','rfid_card'] # automatically set
