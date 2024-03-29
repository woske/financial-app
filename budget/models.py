from django.db import models
from django.contrib.auth.models import User



class Category(models.Model):
    name = models.CharField(max_length=100)
    monthly_budget = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    
    def __str__(self):
        return self.name

class Account(models.Model):
    name = models.CharField(max_length=100, default="")
    balance = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    goal = models.DecimalField(max_digits=10, decimal_places=2,default=0)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)
    
    def __str__(self):
        return self.name

    def update_balance(self):
        transactions = Transaction.objects.filter(account=self)
        credits = sum(t.amount for t in transactions if t.amount > 0)
        debits = abs(sum(t.amount for t in transactions if t.amount < 0))
        self.balance = credits - debits
        self.save()
    
    def completion_percentage(self):
        if self.goal > 0:
            return round(self.balance / self.goal * 100, 2)
        else:
            return 0

class Transaction(models.Model):
    date = models.DateField()
    description = models.CharField(max_length=200, default="")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    category = models.ForeignKey(Category, on_delete=models.CASCADE)
    account = models.ForeignKey(Account, on_delete=models.PROTECT)
    user = models.ForeignKey(User, on_delete=models.CASCADE, default=None)




    
