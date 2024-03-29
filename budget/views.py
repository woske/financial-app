from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Transaction, Category, Account
from django.contrib.auth.decorators import login_required
from .helpers import analyze_transactions
from .forms import TransactionForm, CategoryForm, ImportExpensesForm, AccountForm, UserChangeForm
import csv, datetime, decimal, json, plotly, urllib, base64, io
from django.db.models import Case, Sum, When, F
import plotly.express as px
import plotly.offline as pyo
import plotly.graph_objects as go
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.contrib import messages
from django.db.models.functions import  ExtractYear, ExtractMonth
from django.http import JsonResponse
from django.urls import reverse
from decimal import Decimal
from datetime import datetime, timedelta
from dateutil.parser import parse
import yfinance as yf
import matplotlib.pyplot as plt
import numpy as np

#Login System#
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'login.html', {'error': 'Invalid login credentials'})
    return render(request, 'login.html')

def logout_view(request):
    logout(request)
    return redirect('dashboard')

def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        first_name= request.POST.get('first_name')
        last_name= request.POST.get('last_name')
        password = request.POST.get('password')
        password2 = request.POST.get('password2')
        if User.objects.filter(username=username).exists():
            return render(request, 'register.html', {'error': 'Username already exists'})
        if password == password2:
            User.objects.create_user(username=username, first_name=first_name, last_name=last_name, email=email, password=password)
            user = authenticate(request, username=username, password=password)
            login(request, user)
            return redirect('dashboard')
        else:
            return render(request, 'register.html', {'error': 'Passwords do not match'})
    else:
        return render(request, 'register.html')

@login_required
def profile(request):
    form_user = UserChangeForm(instance=request.user)
    form_password = PasswordChangeForm(request.user)
    if request.method == 'POST':
        if 'update_profile' in request.POST:
            form = UserChangeForm(request.POST, instance=request.user)
            if form.is_valid():
                form.save()
                messages.success(request, 'Profile updated successfully.')
                return redirect('profile')
            else:
                messages.error(request, 'Please correct the error below.')
        elif 'change_password' in request.POST:
            form = PasswordChangeForm(request.user, request.POST)
            if form.is_valid():
                form.save()
                update_session_auth_hash(request, form.user)  # Important!
                messages.success(request, 'Password updated successfully.')
                return redirect('profile')
            else:
                messages.error(request, 'Please correct the error below.')
        elif 'delete_user' in request.POST:
            user = request.user
            user.delete()
            messages.success(request, 'Account deleted successfully.')
            return redirect('dashboard')
    else:
        form_user = UserChangeForm(instance=request.user)
        form_password = PasswordChangeForm(request.user)
    return render(request, 'accounts/profile.html', {'form_user': form_user, 'form_password': form_password, 'user': request.user})

@login_required
def delete_user(request):
    if request.method == 'POST':
        # Delete all transactions, categories, and accounts linked to the user
        Transaction.objects.filter(user=request.user).delete()
        Category.objects.filter(user=request.user).delete()
        Account.objects.filter(user=request.user).delete()
        # Delete the user account
        request.user.delete()
        return redirect('dashboard')
    return render(request, 'accounts/delete_user.html')





def dashboard(request):
    if request.user.is_authenticated:
        data = Transaction.objects.filter(user=request.user).order_by('date')
        cumulative_sum = 0
        labels = []
        values = []

        monthly_data = data.annotate(year=ExtractYear('date'), month=ExtractMonth('date')).values('year', 'month').annotate(sum=Sum('amount'))
        for monthly_sum in monthly_data:
            year = monthly_sum['year']
            month = monthly_sum['month']
            month_name = f'{year:04d}-{month:02d}'
            cumulative_sum += monthly_sum['sum']
            labels.append(month_name)
            values.append(float(cumulative_sum))

        data_json = json.dumps({'labels': labels, 'values': values})
        
        accounts = Account.objects.filter(user=request.user)
        for account in accounts:
            account.update_balance()

        return render(request, 'accounts/dashboard.html', {'data_json': data_json, 'accounts': accounts})
    else:
        return render(request, 'accounts/dashboard2.html')



#################        App Structure         #################

#Add Transactions#
@login_required
def add_transaction(request):
    categories = Category.objects.filter(user=request.user)
    accounts = Account.objects.filter(user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST)
        form.fields['date'].widget = forms.DateInput(attrs={'type': 'date'})
        account_name = request.POST['account']
        account = Account.objects.filter(name=account_name, user=request.user).first()
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.account = Account.objects.get(id=form.cleaned_data['account'])
            transaction.save()
            return redirect('view_transactions')
        else:
            date = request.POST['date']
            description = request.POST['description']
            amount = request.POST['amount']
            user = request.user
            category = Category.objects.get(pk=request.POST['category'], user=request.user)
            transaction = Transaction.objects.create(
                date=date,
                description=description,
                amount=amount,
                category=category,
                account=account,
                user=user
            )
            return redirect('view_transactions')
    else:
        form = TransactionForm()
    return render(request, 'finances/add_transaction.html', {'form': form, 'categories': categories, 'accounts': accounts})



#View Transactions#
@login_required
def view_transactions(request):
    transactions = Transaction.objects.filter(user=request.user)
    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)
    account_id = request.GET.get('account', None)
    category_id = request.GET.get('category', None)
    search_query = request.GET.get('search', None)
    accounts = Account.objects.filter(user=request.user)
    categories = Category.objects.filter(user=request.user)
    sort = request.GET.get('sort', None)
    
    if start_date and end_date:
        transactions = transactions.filter(date__range=(start_date, end_date))
    if account_id:
        transactions = transactions.filter(account__id=account_id)
    if category_id:
        transactions = transactions.filter(category__id=category_id)
    if search_query:
        transactions = transactions.filter(description__icontains=search_query)

    if sort:
        transactions = transactions.order_by(sort)
    else:
        transactions = transactions.order_by('-date')

    total_amount = transactions.aggregate(Sum('amount'))['amount__sum'] or 0

    # Pagination
    paginator = Paginator(transactions, 100) # Show 100 transactions per page
    page = request.GET.get('page')
    transactions = paginator.get_page(page)

    if request.method == 'POST':
        # Get the list of transaction IDs to delete from the form data
        transaction_ids = request.POST.getlist('transaction_ids')

        # Delete the selected transactions
        Transaction.objects.filter(id__in=transaction_ids, user=request.user).delete()

        # Redirect back to the same page
        return redirect(reverse('view_transactions') + '?' + request.GET.urlencode())

    return render(request, 'finances/transactions.html', {'transactions': transactions, 'accounts': accounts, 'categories': categories, 'total_amount': total_amount, 'sort': sort})

#edit transactions#
@login_required
def edit_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    categories = Category.objects.filter(user=request.user)
    accounts = Account.objects.filter(user=request.user)
    if request.method == 'POST':
        form = TransactionForm(request.POST, instance=transaction, category_choices=categories, account_choices=accounts)
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            category_id = request.POST['category']
            transaction.category = Category.objects.get(id=category_id, user=request.user)
            account_id = request.POST['account']
            transaction.account = Account.objects.get(id=account_id, user=request.user)
            transaction.save()
            return redirect('view_transactions')
    else:
        form = TransactionForm(instance=transaction, category_choices=categories, account_choices=accounts)

    return render(request, 'finances/edit_transaction.html', {'form': form})

#Remove Transactions#
@login_required
def remove_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    if request.method == 'POST':
        transaction.delete()
        return redirect('view_transactions')
    return render(request, 'finances/delete_transaction.html', {'transaction': transaction})
    


###### CATEGORY #####

#Create Category#
@login_required
def create_category(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            form.save()
            return redirect('transactions/view_categories/')
    else:
        form = CategoryForm()
    return render(request, 'finances/create_category.html', {'form': form})

#View Categories#
@login_required
def view_categories(request):
    categories = Category.objects.filter(user=request.user)
    return render(request, 'finances/view_categories.html', {'categories': categories})

#Edit Category#
@login_required
def edit_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save(commit=False)
            category.user = request.user
            category.save()
            form.save()
            return redirect('view_categories')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'finances/edit_category.html', {'form': form})

#Delete Category#
@login_required
def delete_category(request, pk):
    category = get_object_or_404(Category, pk=pk)
    category.delete()
    return redirect('view_categories')


##### ACCOUNT #####

#Create Account#
@login_required
def create_account(request):
    if request.method == 'POST':
        form = AccountForm(request.POST)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            account.update_balance()
            return redirect('transactions/view_account/')
    else:
        form = AccountForm()
    return render(request, 'finances/create_account.html', {'form': form})

#View Accounts#
@login_required
def view_accounts(request):
    accounts = Account.objects.filter(user=request.user)
    total_amount = accounts.aggregate(Sum('balance'))['balance__sum'] or 0
    return render(request, 'finances/view_accounts.html', {'accounts': accounts, 'total_amount': total_amount})

@login_required
def recalculate_balances(request):
    accounts = Account.objects.filter(user=request.user)
    for account in accounts:
        account.update_balance()
    return redirect('view_accounts')


#Edit account#
@login_required
def edit_account(request, pk):
    account = get_object_or_404(Account, pk=pk)
    if request.method == 'POST':
        form = AccountForm(request.POST, instance=account)
        if form.is_valid():
            account = form.save(commit=False)
            account.user = request.user
            account.save()
            form.save()
            return redirect('view_accounts')
    else:
        form = AccountForm(instance=account)
    return render(request, 'finances/edit_account.html', {'form': form})

#Delete account#
@login_required
def delete_account(request, pk):
    account = get_object_or_404(Account, pk=pk)
    account.delete()
    return redirect('view_accounts')




###### REPORTS ######
@login_required
def budget_yearly(request):
    categories = Category.objects.filter(user=request.user).exclude(name="[Transfer]")
    transactions = Transaction.objects.filter(user=request.user).exclude(category__name="[Transfer]")

    year = request.GET.get('year')
    selected_year = year if year else datetime.now().year
    if year:
        transactions = transactions.filter(date__year=year)
    else:
        transactions = transactions.filter(date__year=selected_year)


    transactions_by_month_and_category = transactions.values('category__name', 'date__month').annotate(spent=Sum('amount'))

    months = {
        1: 'January',
        2: 'February',
        3: 'March',
        4: 'April',
        5: 'May',
        6: 'June',
        7: 'July',
        8: 'August',
        9: 'September',
        10: 'October',
        11: 'November',
        12: 'December',
    }

    expenses = {}
    income = {}
    for transaction in transactions_by_month_and_category:
        category = transaction['category__name']
        month = months[transaction['date__month']]
        spent = transaction['spent']
        category_budget = categories.get(name=category).monthly_budget

        if spent < 0:
            if category not in expenses:
                expenses[category] = {}
            expenses[category][month] = {
                'spent': abs(spent),
                'budget': category_budget,
                'difference': abs(spent) - category_budget,
            }
        else:
            if category not in income:
                income[category] = {}
            income[category][month] = {
                'spent': spent,
                'budget': category_budget,
                'difference': spent - category_budget,
            }

    chart_data = {}
    for transaction in transactions_by_month_and_category:
        category = transaction['category__name']
        spent = transaction['spent']
        category_budget = categories.get(name=category).monthly_budget
        chart_data[category] = {
            'budget': category_budget,
            'spent': abs(spent),
            'difference': category_budget - abs(spent),
        }

    
    current_year = datetime.now().year
    years = range(2018, current_year + 1)

    return render(request, 'finances/budgets_yearly.html', {'expenses': expenses, 'income': income, 'months': months, 'selected_year': selected_year, 'years': years})

@login_required
def budget_monthly(request):
    categories = Category.objects.filter(user=request.user)
    transactions = Transaction.objects.filter(user=request.user)

    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    

    if start_date and end_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
        num_days = (end_date - start_date).days + 1
        num_months = Decimal(num_days / Decimal(30))

        transactions = transactions.filter(date__range=[start_date, end_date])
        categories = categories.annotate(monthly_budget_adjusted=F('monthly_budget') * num_months)

    category_totals = []
    for category in categories:
        total = transactions.filter(category=category).aggregate(total=Sum('amount'))['total'] or 0
        category_totals.append((category, total))

    # Order the categories based on total spent
    categories = sorted(category_totals, key=lambda x: x[1], reverse=True)
    
    return render(request, 'finances/budgets_monthly.html', {
        'categories': categories,
        'start_date': start_date,
        'end_date': end_date,
        'category_totals': category_totals,
    })



@login_required
def compare_expenses(request):
    transactions = Transaction.objects.filter(user=request.user)
    year = request.GET.get('year')
    current_year = datetime.now().year
    selected_year = year if year else current_year
    if year:
        transactions = transactions.filter(date__year=year)
    else:
        transactions = transactions.filter(date__year=current_year)
    month_names = {1: 'January',
                   2: 'February',
                   3: 'March',
                   4: 'April',
                   5: 'May',
                   6: 'June',
                   7: 'July',
                   8: 'August',
                   9: 'September',
                   10: 'October',
                   11: 'November',
                   12: 'December'}

    data = transactions.annotate(month=ExtractMonth('date')).values('month').annotate(
        expenses=Sum(Case(When(amount__lt=0, then=F('amount')*(-1)))),
        income=Sum(Case(When(amount__gt=0, then=F('amount'))))
    ).order_by('month')

    # Replace month numbers with month names
    for item in data:
        item['month'] = month_names[item['month']]

    years = range(2018, current_year + 1)
    context = {'data': data, 'year': year, 'selected_year': selected_year, 'years': years}
    return render(request, 'reports/income-vs-expenses.html', context)



#CSV import Transactions#
@login_required
def import_expenses(request):
    if request.method == 'POST':
        form = ImportExpensesForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            contents = file.read().decode('utf-8')
            reader = csv.DictReader(contents.splitlines())
            for row in reader:
                account_name = row.get('Account')
                date_str = row.get('Date')
                description = row.get('Description')
                category_name = row.get('Category')
                amount_str = row.get('Amount')
                if not all([account_name, date_str, category_name, amount_str]):
                    continue  # skip this row if any of the required data is missing
                elif not description:
                    description = ''  # set description to an empty string if it's missing
                try:
                    amount = Decimal(amount_str.strip().replace(',', ''))
                except decimal.InvalidOperation:
                    continue  # skip this row if the amount cannot be converted
                try:
                    date = parse(date_str, fuzzy=True).date()
                except ValueError:
                    continue  # skip this row if the date cannot be parsed
                try:
                    account = Account.objects.get(name=account_name, user=request.user)
                except Account.DoesNotExist:
                    account = Account.objects.create(name=account_name, user=request.user)

                try:
                    category = Category.objects.get(name=category_name, user=request.user)
                except Category.DoesNotExist:
                    category = Category.objects.create(name=category_name, user=request.user)

                Transaction.objects.create(
                    date=date,
                    account=account,
                    description=description,
                    amount=amount,
                    category=category,
                    user=request.user
                )
            return redirect('view_transactions')
    else:
        form = ImportExpensesForm()
    return render(request, 'finances/import.html', {'form': form})



# MACHINELEARNING #


# import pandas as pd
# from sklearn.tree import DecisionTreeClassifier
# from sklearn.preprocessing import OneHotEncoder
# from sklearn.impute import SimpleImputer
# import pickle
# from sklearn.compose import ColumnTransformer
# from sklearn.preprocessing import OneHotEncoder
# from sklearn.impute import SimpleImputer
# from sklearn.tree import DecisionTreeClassifier
# from sklearn.pipeline import Pipeline
# import pickle
# import pandas as pd
# import numpy as np
# import csv
# from django.contrib.auth.decorators import login_required
# from django.shortcuts import render, redirect
# from .forms import ImportExpensesForm
# from .models import Transaction, Account, Category

# def train_model(user):
#     # Collect past transactions
#     transactions = Transaction.objects.filter(user=user)

#     # Preprocess the data
#     df = pd.DataFrame.from_records(transactions.values('account__name', 'description', 'category__name', 'amount'))
#     df = pd.get_dummies(df, columns=['account__name', 'description'])
#     df['amount'] = df['amount'].astype('float64')  # change amount to float64

#     # Impute missing values with the median
#     numeric_transformer = Pipeline(steps=[
#         ('imputer', SimpleImputer(strategy='median')),
#     ])
#     categorical_transformer = Pipeline(steps=[
#         ('imputer', SimpleImputer(strategy='most_frequent')),
#         ('onehot', OneHotEncoder(handle_unknown='ignore'))
#     ])

#     preprocessor = ColumnTransformer(
#         transformers=[
#             ('num', numeric_transformer, ['amount']),
#             ('cat', categorical_transformer, ['account__name', 'description'])
#         ])

#     X = df.drop('category__name', axis=1)
#     y = df['category__name']

#     # Train the model
#     classifier = Pipeline(steps=[
#         ('preprocessor', preprocessor),
#         ('classifier', DecisionTreeClassifier())
#     ])
#     classifier.fit(X, y)

#     # Save the model to disk
#     filename = f'model_{user.id}.pkl'
#     with open(filename, 'wb') as file:
#         pickle.dump((preprocessor, classifier), file)

#     # Get the feature names
#     feature_names = preprocessor.transformers_[1][1].named_steps['onehot'].get_feature_names_out(
#         preprocessor.transformers_[1][2])
#     feature_names_out = np.concatenate((['amount'], feature_names))

#     return feature_names_out, preprocessor, classifier


# def predict_category(user, transaction):
#     # Load the model from disk
#     filename = f'model_{user.id}.pkl'
#     with open(filename, 'rb') as file:
#         preprocessor, classifier = pickle.load(file)

#     # Preprocess the new transaction
#     df = pd.DataFrame.from_records([transaction], columns=['account__name', 'description'])
#     X = preprocessor.transform(df)

#     # Predict the category
#     y_pred = classifier.predict(X)
#     return y_pred[0]


# @login_required
# def train_model_view(request):
#     if request.method == 'POST':
#         try:
#             train_model(request.user)
#         except Exception as e:
#             print(e)
#         return redirect('model_trained')
#     else:
#         return render(request, 'model/train_model.html')


# @login_required
# def import_expenses(request):
#     if request.method == 'POST':
#         form = ImportExpensesForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             contents = file.read().decode('utf-8')
#             reader = csv.DictReader(contents.splitlines())

#             for row in reader:
#                 account_name = row['Account']
#                 date = row['Date']
#                 description = row['Description']
#                 amount = row['Amount']
#                 category_name = predict_category(request.user, {'account__name': account_name, 'description': description})

#                 try:
#                     amount = Decimal(amount.strip().replace(',', ''))
#                 except decimal.InvalidOperation:
#                     continue  # skip this row if the amount cannot be converted

#                 # Save the transaction
#                 account, created = Account.objects.get_or_create(name=account_name, user=request.user)
#                 category, created = Category.objects.get_or_create(name=category_name, user=request.user)
#                 transaction = Transaction.objects.create(date=date, description=description, amount=amount, account=account, category=category, user=request.user)

#             return redirect('import_expenses')
#     else:
#         form = ImportExpensesForm()
#         return render(request, 'finances/import.html', {'form': form})






# @login_required
# def import_expenses(request):
#     if request.method == 'POST':
#         form = ImportExpensesForm(request.POST, request.FILES)
#         if form.is_valid():
#             file = request.FILES['file']
#             contents = file.read().decode('utf-8')
#             reader = csv.DictReader(contents.splitlines())

#             for row in reader:
#                 account_name = row['Account']
#                 date = row['Date']
#                 description = row['Description']
#                 amount = row['Amount']
#                 category_name = row['Category']

#                 try:
#                     amount = Decimal(amount.strip().replace(',', ''))
#                 except decimal.InvalidOperation:
#                     continue  # skip this row if the amount cannot be converted

#                 account, _ = Account.objects.get_or_create(
#                     name=account_name,
#                     user=request.user
#                 )

#                 transaction = {
#                     'account__name': account_name,
#                     'description': description
#                 }

#                 category = predict_category(request.user, transaction) or Category.objects.get_or_create(
#                     name=category_name,
#                     user=request.user
#                 )

#                 Transaction.objects.create(
#                     date=date,
#                     account=account,
#                     description=description,
#                     amount=amount,
#                     category=category,
#                     user=request.user
#                 )

#             return redirect('transactions')
#     else:
#         form = ImportExpensesForm()
#     return render(request, 'finances/import.html', {'form': form})



#Analyze Transactions#
@login_required
def analyze_transactions(request):
    transactions = Transaction.objects.filter(user=request.user)
    categories = Category.objects.filter(user=request.user)

    end_date = request.GET.get('end_date', None)
    num_months = 1

    if end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d").date()
    else:
        end_date = datetime.today().date()

    start_date = request.GET.get('start_date', None)

    if start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d").date()
        if not end_date:  # set end date to today if not provided
            end_date = datetime.today().date()
    else:
        if not end_date:  # set start and end date to last 30 days if neither provided
            end_date = datetime.today().date()
            start_date = end_date - timedelta(days=30)
        else:
            start_date = end_date - timedelta(days=30)


    num_days = (end_date - start_date).days + 1
    num_months = Decimal(num_days / Decimal(30))

    transactions = transactions.filter(date__range=[start_date, end_date])

    # Analyze transactions by category
    category_data = {}
    for category in categories:
        if category.name == "[Transfer]":
            continue
        category_transactions = transactions.filter(category=category)
        category_amount = sum([t.amount for t in category_transactions])
        if category_amount != 0:  # only include non-zero categories
            category_data[category.name] = category_amount
            monthly_budget_adjusted = category.monthly_budget * num_months
            category_data[category.name] = {
                'amount': category_amount,
                'monthly_budget': category.monthly_budget,
                'monthly_budget_adjusted': monthly_budget_adjusted
            }

    # Calculate total expenses
    total_expenses = sum([t.amount for t in transactions])

    # Sort category data by values (descending)
    sorted_category_data = dict(sorted(category_data.items(), key=lambda item: item[1]['amount'], reverse=True))

    # Filter transactions by amount
    income_transactions = transactions.filter(amount__gt=0)
    income_categories = [t.category.name for t in income_transactions]
    income_data = [t.amount for t in income_transactions]

    expense_transactions = transactions.filter(amount__lt=0)
    expense_categories = [t.category.name for t in expense_transactions]
    expense_data = [t.amount for t in expense_transactions]

    # Create pie charts
    income_pie = px.pie(values=income_data, names=income_categories, title='Income Categories')
    expense_pie = px.pie(values=expense_data, names=expense_categories, title='Expense Categories')

    # Convert charts to HTML strings
    income_pie_html = pyo.plot(income_pie, output_type='div')
    expense_pie_html = pyo.plot(expense_pie, output_type='div')

    context = {
        'categories': categories,
        'data': sorted_category_data,
        'total_expenses': total_expenses,
        'income_pie_html': income_pie_html,
        'expense_pie_html': expense_pie_html,
        'start_date': start_date,
        'end_date': end_date,
    }
    return render(request, 'finances/analyze.html', context)




#####         TREND FOREX ##########
@login_required
def track_trend(request):
    # Define the currency pair you want to trade
    symbol = "EURUSD=X"

    # Get historical Forex prices from yfinance
    df = yf.download(symbol, interval="1d", period="1y")

    # Calculate the moving average
    df["ma_50"] = df["Close"].rolling(window=50).mean()

    # Determine the trend based on the moving average
    df["trend"] = np.where(df["Close"] > df["ma_50"], "bullish", "bearish")

    # Backtest the strategy
    investment = 100
    total_profit_loss = 0
    trades = []
    for i in range(50, len(df)):
        if df["trend"].iloc[i] == "bullish":
            entry_price = df["Close"].iloc[i]
            stop_loss = entry_price - 0.005
            take_profit = entry_price + 0.01
            for j in range(i + 1, len(df)):
                if df["Close"].iloc[j] <= stop_loss:
                    exit_price = stop_loss
                    break
                elif df["Close"].iloc[j] >= take_profit:
                    exit_price = take_profit
                    break
            else:
                exit_price = df["Close"].iloc[-1]
            profit_loss = exit_price - entry_price
            trade_result = "Win" if profit_loss > 0 else "Loss"
            trades.append({"entry_price": entry_price, "exit_price": exit_price, "stop_loss": stop_loss, "take_profit": take_profit, "trade_result": trade_result})

            if trade_result == "Win":
                total_profit_loss += investment * (take_profit - entry_price)
            else:
                total_profit_loss += investment * (stop_loss - entry_price)

    win_pct = (sum(1 for trade in trades if trade["trade_result"] == "Win") / len(trades))*100
    loss_pct = 1 - win_pct


    wins = 0
    losses = 0

    for trade in trades:
        if trade['trade_result'] == 'Win':
            wins += 1
        else:
            losses += 1

    win_rate = (wins / len(trades)) * 100


    # Calculate the total profit or loss
    # total_profit_loss = sum([t["exit_price"] - t["entry_price"] for t in trades])

    # Plot the Forex prices and moving average
    fig = go.Figure()
    fig.add_trace(go.Candlestick(x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="Price"))
    fig.add_trace(go.Scatter(x=df.index, y=df["ma_50"], mode="lines", name="50-day Moving Average"))
    for i in range(50, len(df)):
        if trades:
            entry_points = df[df["trend"] == "bullish"]["Close"]
            fig.add_trace(go.Scatter(x=entry_points.index, y=entry_points, mode="markers", name="Entry Points", marker=dict(color="red", symbol="circle")))
            fig.add_trace(go.Scatter(x=entry_points.index, y=entry_points - 0.005, mode="lines", name="Stop Losses", line=dict(color="black", dash="dash")))
            fig.add_trace(go.Scatter(x=entry_points.index, y=entry_points + 0.01, mode="lines", name="Take Profits", line=dict(color="green", dash="dash")))

    # Set layout properties
    fig.update_layout(
        margin=dict(l=50, r=50, t=50, b=50),
        xaxis_rangeslider_visible=False,
    )
    # Convert the plot to a JSON string
    graphJSON = json.dumps(fig, cls=plotly.utils.PlotlyJSONEncoder)

    # # Determine the trend based on the moving average
    if df["Close"].iloc[-1] > df["ma_50"].iloc[-1]:
        trend = "bullish"
    else:
        trend = "bearish"

    # Recommend entry points, stop loss, and take profit based on the trend
    if trend == "bullish":
        entry_point = df["Close"].iloc[-1]
        stop_loss = entry_point - 0.005
        take_profit = entry_point + 0.01
    else:
        entry_point = df["Close"].iloc[-1]
        stop_loss = entry_point + 0.005
        take_profit = entry_point - 0.01

    context = {
        "win_pct":win_pct,
        "loss_pct":loss_pct,
        "win_rate": win_rate,
        "trades":trades,
        "trend": trend,
        "entry_point": entry_point,
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "total_profit_loss": total_profit_loss,
        "graphJSON": graphJSON,
    }
    return render(request, "forex/trend.html", context)
