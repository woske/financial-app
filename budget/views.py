from django.shortcuts import render, redirect, get_object_or_404
from django import forms
from .models import Transaction, Category, Account
from django.contrib.auth.decorators import login_required
from .helpers import analyze_transactions
from .forms import TransactionForm, CategoryForm, ImportExpensesForm, AccountForm, UserChangeForm
import csv, datetime
from django.db.models import Sum
import plotly.express as px
import plotly.offline as pyo
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.models import User
from django.core.cache import cache
from django.core.paginator import Paginator
from django.contrib import messages

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
    return redirect('home')

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
            return redirect('')
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
    else:
        form_user = UserChangeForm(instance=request.user)
        form_password = PasswordChangeForm(request.user)
    return render(request, 'accounts/profile.html', {'form_user': form_user, 'form_password': form_password, 'user': request.user})






def dashboard(request):
    if request.user.is_authenticated:
        return render(request, 'accounts/dashboard.html')
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
        account = Account.objects.filter(name=account_name).first()
        if form.is_valid():
            transaction = form.save(commit=False)
            transaction.user = request.user
            transaction.account = Account.objects.get(id=form.cleaned_data['account'])
            transaction.save()
            return redirect('transactions')
        else:
            date = request.POST['date']
            description = request.POST['description']
            amount = request.POST['amount']
            user = request.user
            category = Category.objects.get(pk=request.POST['category'])
            transaction = Transaction.objects.create(
                date=date,
                description=description,
                amount=amount,
                category=category,
                account=account,
                user=user
            )
            return redirect('transactions')
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
    accounts = Account.objects.filter(user=request.user)
    categories = Category.objects.filter(user=request.user)
    sort = request.GET.get('sort', None)
    
    if start_date and end_date:
        transactions = transactions.filter(date__range=(start_date, end_date))
    if account_id:
        transactions = transactions.filter(account__id=account_id)
    if category_id:
        transactions = transactions.filter(category__id=category_id)

    if sort:
        transactions = transactions.order_by(sort)
    else:
        transactions = transactions.order_by('-date')

    total_amount = transactions.aggregate(Sum('amount'))['amount__sum'] or 0

    # Pagination
    paginator = Paginator(transactions, 100) # Show 100 transactions per page
    page = request.GET.get('page')
    transactions = paginator.get_page(page)

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
            return redirect('transactions')
    else:
        form = TransactionForm(instance=transaction, category_choices=categories, account_choices=accounts)

    return render(request, 'finances/edit_transaction.html', {'form': form})

#Remove Transactions#
@login_required
def remove_transaction(request, transaction_id):
    transaction = get_object_or_404(Transaction, id=transaction_id, user=request.user)
    if request.method == 'POST':
        transaction.delete()
        return redirect('transactions')
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
    return render(request, 'finances/view_accounts.html', {'accounts': accounts})

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




###### BUDGETS ######
def view_monthly_transactions(request):
    categories = Category.objects.filter(user=request.user)
    transactions = Transaction.objects.filter(user=request.user)

    year = request.GET.get('year')
    selected_year = year if year else None
    if year:
        transactions = transactions.filter(date__year=year)

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

    data = {}
    for transaction in transactions_by_month_and_category:
        category = transaction['category__name']
        month = months[transaction['date__month']]
        budget = Category.objects.get(name=category).monthly_budget
        spent = transaction['spent']
        difference = spent - budget

        if category not in data:
            data[category] = {}
        
        
        data[category][month] = {
            'budget': budget,
            'spent': spent,
            'difference': difference,
            'years': range(2010, 2023),
            'selected_year': selected_year,
        }

    return render(request, 'finances/view_monthly_transactions.html', {'data': data, 'months': months})







#CSV import Transactions#
@login_required
def import_expenses(request):
    if request.method == 'POST':
        form = ImportExpensesForm(request.POST, request.FILES)
        if form.is_valid():
            file = request.FILES['file']
            contents = file.read().decode('utf-8')
            reader = csv.reader(contents.splitlines())
            headers = next(reader)
            for row in reader:
                account, date, description, category, amount = row
                category, _ = Category.objects.get_or_create(
                    name=category,
                    user=request.user
                )
                account, _ = Account.objects.get_or_create(
                    name=account,
                    user=request.user
                )
                Transaction.objects.create(
                    date=date,
                    account=account,
                    description=description,
                    amount=amount,
                    category=category,
                    user=request.user
                )
            return redirect('transactions')
    else:
        form = ImportExpensesForm()
    return render(request, 'finances/import.html', {'form': form})




#Analyze Transactions#
@login_required
def analyze_transactions(request):
    transactions = Transaction.objects.filter(user=request.user)
    categories = Category.objects.filter(user=request.user)

    start_date = request.GET.get('start_date', None)
    end_date = request.GET.get('end_date', None)

    if start_date and end_date:
        transactions = transactions.filter(date__range=(start_date, end_date))

    # Analyze transactions by category
    category_data = {}
    for category in categories:
        if category.name == "[Transfer]":
            continue
        category_transactions = transactions.filter(category=category)
        category_amount = sum([t.amount for t in category_transactions])
        category_data[category.name] = category_amount

    # Calculate total expenses
    total_expenses = sum([t.amount for t in transactions])

    # Sort category data by values (descending)
    sorted_category_data = dict(sorted(category_data.items(), key=lambda item: item[1], reverse=True))

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
    'data': sorted_category_data,
    'total_expenses': total_expenses,
    'income_pie_html': income_pie_html,
    'expense_pie_html': expense_pie_html,
    }
    return render(request, 'finances/analyze.html', context)



