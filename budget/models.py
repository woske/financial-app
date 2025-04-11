from django.db import models
from django.contrib.auth.models import User
from decimal import Decimal



class Category(models.Model):
    name = models.CharField(max_length=100)
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    
    def __str__(self):
        return self.name

class Account(models.Model):
    ACCOUNT_TYPES = [
        ('chequing', 'Chequing'),
        ('savings', 'Savings'),
        ('credit', 'Credit Card'),
        ('investment', 'Investment'),
        ('crypto', 'Crypto'),
    ]

    name = models.CharField(max_length=100, default="")
    starting_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0, editable=False)  # Now auto-calculated
    goal = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    account_type = models.CharField(max_length=20, choices=ACCOUNT_TYPES, default='chequing')
    crypto_amount = models.DecimalField(max_digits=18, decimal_places=8, default=0, blank=True, null=True) 


    def __str__(self):
        return self.name

    def update_balance(self):
        if self.account_type == 'crypto' and self.crypto_amount:
            import yfinance as yf
            btc = yf.Ticker("BTC-CAD")
            latest_price = btc.history(period="1d")["Close"].iloc[-1]
            self.balance = self.starting_balance + (Decimal(latest_price) * self.crypto_amount)
        else:
            transactions = Transaction.objects.filter(account=self)
            credits = sum(t.amount for t in transactions if t.amount > 0)
            debits = abs(sum(t.amount for t in transactions if t.amount < 0))
            self.balance = self.starting_balance + credits - debits
        self.save()


    def completion_percentage(self):
        if self.goal > 0:
            return round(self.balance / self.goal * 100, 2)
        return 0


class Transaction(models.Model):
    date = models.DateField()
    description = models.CharField(max_length=200, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='from_account')
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    transfer_to = models.ForeignKey(Account, on_delete=models.PROTECT, null=True, blank=True, related_name='to_account')  # optional

    def is_transfer(self):
        return self.transfer_to is not None





    
