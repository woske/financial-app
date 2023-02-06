import pandas as pd
from .models import Transaction

def analyze_transactions():
    transactions = Transaction.objects.all()
    df = pd.DataFrame(list(transactions.values()))
    data = df.groupby('category').sum()
    return data
