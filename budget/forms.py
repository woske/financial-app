from django import forms
from django.contrib.auth.forms import ReadOnlyPasswordHashField
from django.contrib.auth.models import User
from .models import Transaction, Category, Account

class TransactionForm(forms.ModelForm):
    category = forms.ModelChoiceField(queryset=Category.objects.none())
    account = forms.ModelChoiceField(queryset=Account.objects.none())
    transfer_to = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        required=False,
        label='Transfer To (optional)'
    )
    date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    def __init__(self, *args, **kwargs):
        category_choices = kwargs.pop('category_choices', None)
        account_choices = kwargs.pop('account_choices', None)
        super(TransactionForm, self).__init__(*args, **kwargs)
        if category_choices is not None:
            self.fields['category'].queryset = category_choices
        if account_choices is not None:
            self.fields['account'].queryset = account_choices
            self.fields['transfer_to'].queryset = account_choices

    class Meta:
        model = Transaction
        fields = ['date', 'description', 'amount', 'category', 'account']  # `transfer_to` is NOT in the model


class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ['name', 'monthly_budget']

class AccountForm(forms.ModelForm):
    class Meta:
        model = Account
        fields = ['name','account_type', 'starting_balance', 'goal', 'crypto_amount']
        widgets = {
            'crypto_amount': forms.NumberInput(attrs={'step': '0.00000001'}),
        }

class ImportExpensesForm(forms.Form):
    file = forms.FileField()

class UserChangeForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField()

    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email', 'password')

    def clean_password(self):
        return self.initial["password"]
