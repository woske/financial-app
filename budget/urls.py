"""budgetproject URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic.base import TemplateView
from .views import add_transaction, view_transactions, analyze_transactions, create_category, view_categories, import_expenses, register, create_account, view_accounts, edit_transaction, remove_transaction, edit_category, delete_category, edit_account, delete_account
from .views import budget_yearly, budget_monthly, profile, dashboard,login_view, recalculate_balances, delete_user, compare_expenses, logout_view, category_spending_trends, view_category_spending_trends

urlpatterns = [
    path('', dashboard, name='dashboard'),
    path('login/', login_view, name='login_view'),
    path('logout/', logout_view, name='logout'),
    path('register/', register, name='register'),
    path('transactions/add/', add_transaction, name='add_transaction'),
    path('transactions/', view_transactions, name='view_transactions'),
    path('transactions/edit/<int:transaction_id>/', edit_transaction, name='edit_transaction'),
    path('transactions/delete/<int:transaction_id>/', remove_transaction, name='remove_transaction'),
    path('transactions/analyze/', analyze_transactions, name='analyze_transactions'),
    path('transactions/import/', import_expenses, name='import_expenses'),
    path('categories/create_category/', create_category, name='create_category'),
    path('categories/', view_categories, name='view_categories'),
    path('categories/edit/<int:pk>/', edit_category, name='edit_category'),
    path('categories/delete/<int:pk>/', delete_category, name='delete_category'),
    path('accounts/edit/<int:pk>/', edit_account, name='edit_account'),
    path('accounts/delete/<int:pk>/', delete_account, name='delete_account'),
    path('accounts/add/', create_account, name='create_account'),
    path('accounts/', view_accounts, name='view_accounts'),
    path('reports/yearly/', budget_yearly, name='budget_yearly'),
    path('reports/monthly/', analyze_transactions, name='budget_monthly'),
    path('reports/income-vs-expenses/', compare_expenses, name='compare_expenses'),
    path('api/category-spending-trends/', category_spending_trends, name='category-spending-trends'),
    path('reports/category/', view_category_spending_trends, name='view-category-spending-trends'),
    path('profile/', profile, name='profile'),
    path('recalculate_balances/', recalculate_balances, name='recalculate_balances'),
    path('profile/delete_user/', delete_user, name='delete_user'),
    # path('trading/', track_trend, name='track_trend'),
    # path('train_model/', train_model_view, name='train_model'),
    # path('model_trained/', TemplateView.as_view(template_name='model/model_trained.html'), name='model_trained'),
    path('admin/', admin.site.urls),
    path('recipes/', include('budget.recipes.urls')),
]