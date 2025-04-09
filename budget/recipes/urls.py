from django.urls import path, include
from . import views

urlpatterns = [
    path('', views.home_page, name='home'),
    path('login/', views.logging_page, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('signup/', views.signup_page, name='signup'),
    path('register/', views.register, name='register'),
    path('account/', views.account_page, name='account'),
    path('account/delete/', views.delete_account, name='delete_account'),
    path('add_recipe/', views.add_recipe, name='add_recipe'),
    path('scrape_recipes/', views.view_recipes, name='view_recipes'),
    path('create_shared_list/', views.create_shared_list, name='create_shared_list'),
    path('add_to_shared_list/<int:list_id>/', views.add_to_shared_list, name='add_to_shared_list'),
    path('scrape_recipe/', views.scrape_recipe, name='scrape_recipe'),  # New route for recipe scraping
    path('save_recipe/', views.save_recipe, name='save_recipe'),
    path('saved_recipes/', views.view_saved_recipes, name='view_saved_recipes'),
    path('recipe/<int:recipe_id>/', views.view_recipe, name='view_recipe'),
    path('recipe/<int:recipe_id>/edit/', views.edit_recipe, name='edit_recipe'),
    path('recipe/<int:recipe_id>/add_comment/', views.add_comment, name='add_comment'),
    path('recipe/<int:recipe_id>/toggle_favorite/', views.toggle_favorite, name='toggle_favorite'),
    path('comment/<int:comment_id>/add_reply/', views.add_reply, name='add_reply'),
    path('favorites/', views.view_favorite_recipes, name='view_favorite_recipes'),
    path('recipe/<int:recipe_id>/delete/', views.delete_recipe, name='delete_recipe'),
    path('test_scrape_image/', views.test_scrape_image, name='test_scrape_image'),
    path('recipe_books/', views.view_recipe_books, name='view_recipe_books'),
    path('recipe_books/create/', views.create_recipe_book, name='create_recipe_book'),
    path('recipe_books/<int:book_id>/add/', views.add_recipe_to_book, name='add_recipe_to_book'),
    path('recipe_books/<int:book_id>/', views.view_recipe_book, name='view_recipe_book'),
    path('recipe_books/<int:book_id>/remove/<int:recipe_id>/', views.remove_recipe_from_book, name='remove_recipe_from_book'),
    path('recipe_books/add/<int:recipe_id>/', views.add_recipe_to_book_from_view, name='add_recipe_to_book_from_view'),
]