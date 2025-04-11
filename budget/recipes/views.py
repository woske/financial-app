from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth import login, logout, authenticate,update_session_auth_hash
from django.contrib import messages
from .models import Recipe, SharedRecipeList, Comment, UserFavoriteRecipe, RecipeBook
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.urls import reverse
from recipe_scrapers import SCRAPERS
from .custom_scrapers import CustomScraper
import requests
import traceback

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
}

def home_page(request):
    if request.user.is_authenticated:
        return redirect('view_saved_recipes')
    return render(request, 'recipes/home.html')


def logging_page(request):
    if request.user.is_authenticated:
        return redirect('view_saved_recipes')

    if request.method == 'POST':
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            next_url = request.POST.get('next') or reverse('view_saved_recipes')
            return redirect(next_url)
        else:
            return render(request, 'recipes/logging.html', {
                'error': 'Invalid username or password',
                'next': request.GET.get('next', ''),
            })

    return render(request, 'recipes/logging.html', {
        'next': request.GET.get('next', ''),
    })

@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('home')

def signup_page(request):
    if request.method == 'POST':
        username = request.POST['username']
        first_name = request.POST['first_name']
        last_name = request.POST['last_name']
        email = request.POST['email']
        password = request.POST['password']
        password_confirmation = request.POST['password_confirmation']

        if password != password_confirmation:
            messages.error(request, "Passwords do not match.")
            return render(request, 'recipes/signup.html')

        try:
            user = User.objects.create_user(
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                email=email
            )
            user.save()
            login(request, user)
            return redirect(reverse('view_saved_recipes'))
        except Exception as e:
            messages.error(request, f"Error: {str(e)}")

    return render(request, 'recipes/signup.html')

@login_required
def account_page(request):
    if request.method == 'POST':
        user = request.user
        first_name = request.POST.get('first_name', user.first_name)
        last_name = request.POST.get('last_name', user.last_name)
        email = request.POST.get('email', user.email)

        user.first_name = first_name
        user.last_name = last_name
        user.email = email

        if 'password' in request.POST and 'password_confirmation' in request.POST:
            password = request.POST['password']
            password_confirmation = request.POST['password_confirmation']
            if password == password_confirmation:
                user.set_password(password)
                update_session_auth_hash(request, user)
            else:
                messages.error(request, "Passwords do not match.")
                return redirect('account')

        user.save()
        messages.success(request, "Account updated successfully.")
        return redirect('account')

    return render(request, 'recipes/account.html')

@login_required
def delete_account(request):
    if request.method == 'POST':
        request.user.delete()
        messages.success(request, "Account deleted successfully.")
        return redirect('home')

    return render(request, 'recipes/delete_account.html')

def test_scrape_image(request):
    url = request.GET.get('url')
    if not url:
        return JsonResponse({'error': 'No URL provided'}, status=400)

    try:
        # Fetch the webpage content
        response = requests.get(url)
        response.raise_for_status()

        # Use the custom scraper to get the image
        scraper = CustomScraper(response.content, url)
        image_url = scraper.featured_image()

        return JsonResponse({'image_url': image_url})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def scrape_recipe(request):
    url = request.POST.get('url') or request.GET.get('url')

    if not url:
        print("⚠️ No URL provided.")
        return JsonResponse({'error': 'No URL provided'}, status=400)

    try:
        print(f"🔍 Trying to scrape: {url}")

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
        }

        response = requests.get(url, headers=headers)
        response.raise_for_status()

        scraper_class = next((scraper for site, scraper in SCRAPERS.items() if site in url), None)
        scraper = scraper_class(response.content, url=url) if scraper_class else CustomScraper(response.content, url=url)

        image = scraper.image() if hasattr(scraper, 'image') else scraper.featured_image()

        recipe_data = {
            'title': scraper.title(),
            'ingredients': scraper.ingredients(),
            'instructions': scraper.instructions(),
            'image': image,
            'original_url': url
        }

        print("✅ Scraping successful!")
        return JsonResponse(recipe_data)

    except Exception as e:
        print("❌ Scrape error:")
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)



def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Log the user in after registration
            login(request, user)
            return redirect('view_recipes')
    else:
        form = UserCreationForm()

    return render(request, 'recipes/register.html', {'form': form})

@login_required
def add_recipe(request):
    if request.method == 'POST':
        title = request.POST['title']
        ingredients = request.POST['ingredients']
        instructions = request.POST['instructions']
        recipe = Recipe.objects.create(
            title=title,
            ingredients=ingredients,
            instructions=instructions,
            owner=request.user
        )
        return redirect('view_recipes')

    return render(request, 'recipes/add_recipe.html')

@login_required
def view_recipes(request):
    recipes = Recipe.objects.filter(owner=request.user)
    shared_lists = SharedRecipeList.objects.filter(users=request.user)
    return render(request, 'recipes/view_recipes.html', {
        'recipes': recipes,
        'shared_lists': shared_lists
    })

@login_required
def view_saved_recipes(request):
    query = request.GET.get('q')
    saved_recipes = Recipe.objects.filter(owner=request.user)

    if query:
        saved_recipes = saved_recipes.filter(Q(title__icontains=query) | Q(ingredients__icontains=query))

    return render(request, 'recipes/view_saved_recipes.html', {'saved_recipes': saved_recipes})


@login_required
def add_to_shared_list(request, list_id):
    shared_list = SharedRecipeList.objects.get(id=list_id)
    recipe_id = request.POST['recipe_id']
    recipe = Recipe.objects.get(id=recipe_id)
    shared_list.recipes.add(recipe)
    return redirect('view_recipes')

@login_required
def create_shared_list(request):
    if request.method == 'POST':
        list_name = request.POST['list_name']
        shared_list = SharedRecipeList.objects.create(name=list_name)
        shared_list.users.add(request.user)
        return redirect('view_recipes')

    return render(request, 'recipes/create_shared_list.html')

from django.db.models import Q

@login_required
def create_recipe_book(request):
    if request.method == 'POST':
        book_name = request.POST.get('book_name')
        if book_name:
            RecipeBook.objects.create(name=book_name, owner=request.user)
            messages.success(request, "Recipe book created successfully!")
            return redirect('view_recipe_books')

    return render(request, 'recipes/create_recipe_book.html')


@login_required
def view_recipe_books(request):
    recipe_books = RecipeBook.objects.filter(owner=request.user)  # Filter by owner
    return render(request, 'recipes/view_recipe_books.html', {'recipe_books': recipe_books})

@login_required
def view_recipe_book(request, book_id):
    book = get_object_or_404(RecipeBook, id=book_id, owner=request.user)  # Filter by owner
    recipes = book.recipes.all()
    return render(request, 'recipes/view_recipe_book.html', {
        'book': book,
        'recipes': recipes
    })

@login_required
def add_recipe_to_book(request, book_id):
    if request.method == 'POST':
        recipe_id = request.POST.get('recipe_id')  # Get recipe_id from POST data
        book = get_object_or_404(RecipeBook, id=book_id, user=request.user)
        recipe = get_object_or_404(Recipe, id=recipe_id, owner=request.user)
        book.recipes.add(recipe)
        return redirect('view_recipe_books')
    return JsonResponse({'error': 'Invalid request'}, status=400)



@login_required
def add_recipe_to_book_from_view(request, recipe_id):
    if request.method == 'POST':
        book_id = request.POST.get('recipe_book')
        recipe = get_object_or_404(Recipe, id=recipe_id)
        recipe_book = get_object_or_404(RecipeBook, id=book_id, owner=request.user)

        # Add the recipe to the selected book
        recipe_book.recipes.add(recipe)
        messages.success(request, f"{recipe.title} has been added to {recipe_book.name}.")
        
        return redirect('view_recipe', recipe_id=recipe_id)

    return redirect('view_recipe', recipe_id=recipe_id)

@login_required
def remove_recipe_from_book(request, book_id, recipe_id):
    recipe_book = get_object_or_404(RecipeBook, id=book_id, owner=request.user, is_recipe_book=True)
    recipe = get_object_or_404(Recipe, id=recipe_id)
    recipe_book.recipes.remove(recipe)
    messages.info(request, f"{recipe.title} removed from {recipe_book.name}")
    return redirect('view_recipe_books')

@login_required
def edit_recipe_book(request, book_id):
    book = get_object_or_404(RecipeBook, id=book_id, owner=request.user)
    if request.method == 'POST':
        new_name = request.POST.get('book_name')
        if new_name:
            book.name = new_name
            book.save()
            messages.success(request, "Recipe book name updated!")
            return redirect('view_recipe_book', book_id=book.id)
    return render(request, 'recipes/edit_recipe_book.html', {'book': book})

@login_required
def delete_recipe_book(request, book_id):
    book = get_object_or_404(RecipeBook, id=book_id, owner=request.user)
    if request.method == 'POST':
        book.delete()
        messages.success(request, "Recipe book deleted.")
        return redirect('view_recipe_books')
    return redirect('view_recipe_book', book_id=book.id)



@login_required
def save_recipe(request):
    if request.method == 'POST':
        title = request.POST.get('title')
        ingredients = request.POST.get('ingredients')
        instructions = request.POST.get('instructions')
        original_url = request.POST.get('original_url')  # Get the original URL
        featured_image = request.POST.get('featured_image')  # Get the featured image

        if not title or not ingredients or not instructions:
            return JsonResponse({'message': 'All fields are required'}, status=400)

        try:
            # Save the recipe to the database
            recipe = Recipe.objects.create(
                title=title,
                ingredients=ingredients,
                instructions=instructions,
                original_url=original_url if original_url else "",  # Save the URL if present
                featured_image=featured_image if featured_image else "",  # Save the image if present
                owner=request.user
            )

            return JsonResponse({'message': 'Recipe saved successfully!'})
        except Exception as e:
            print(f"Error saving recipe: {e}")
            return JsonResponse({'message': 'An error occurred while saving the recipe'}, status=500)

    return JsonResponse({'message': 'Invalid request'}, status=400)


@login_required
def view_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    comments = recipe.comments.all()

    # Check if the recipe is in the user's favorites
    is_favorited = UserFavoriteRecipe.objects.filter(user=request.user, recipe=recipe).exists()

    return render(request, 'recipes/view_recipe.html', {
        'recipe': recipe,
        'comments': comments,
        'is_favorited': is_favorited,
    })

@login_required
def edit_recipe(request, recipe_id):
    # Edit the recipe
    recipe = get_object_or_404(Recipe, id=recipe_id, owner=request.user)
    if request.method == 'POST':
        recipe.title = request.POST.get('title', recipe.title)
        recipe.ingredients = request.POST.get('ingredients', recipe.ingredients)
        recipe.instructions = request.POST.get('instructions', recipe.instructions)
        recipe.save()
        return redirect('view_recipe', recipe_id=recipe.id)
    return render(request, 'recipes/edit_recipe.html', {'recipe': recipe})

@login_required
def delete_recipe(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)

    # Check if the current user is the owner of the recipe
    if recipe.owner != request.user:
        messages.error(request, "You do not have permission to delete this recipe.")
        return redirect('view_recipe', recipe_id=recipe.id)

    # Delete the recipe and show a success message
    recipe.delete()
    messages.success(request, "Recipe deleted successfully.")
    return redirect('view_saved_recipes')

@login_required
def add_comment(request, recipe_id):
    # Add a comment to the recipe
    recipe = get_object_or_404(Recipe, id=recipe_id)
    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Comment.objects.create(recipe=recipe, author=request.user, content=content)
        return redirect('view_recipe', recipe_id=recipe.id)
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def add_reply(request, comment_id):
    if request.method == 'POST':
        parent_comment = get_object_or_404(Comment, id=comment_id)
        content = request.POST.get('reply_content')
        if content:
            # Create a new reply as a Comment
            Comment.objects.create(
                recipe=parent_comment.recipe,
                author=request.user,
                content=content
            )
        return redirect('view_recipe', recipe_id=parent_comment.recipe.id)
    return redirect('view_saved_recipes')

@login_required
def toggle_favorite(request, recipe_id):
    recipe = get_object_or_404(Recipe, id=recipe_id)
    user = request.user

    # Check if the UserFavoriteRecipe relationship already exists
    favorite_relationship = UserFavoriteRecipe.objects.filter(user=user, recipe=recipe).first()

    if favorite_relationship:
        # If it exists, remove it to unfavorite the recipe
        favorite_relationship.delete()
    else:
        # If it does not exist, create it to favorite the recipe
        UserFavoriteRecipe.objects.create(user=user, recipe=recipe)

    return redirect('view_recipe', recipe_id=recipe.id)

@login_required
def view_favorite_recipes(request):
    # Get all favorite recipes for the logged-in user
    favorite_recipes = UserFavoriteRecipe.objects.filter(user=request.user).select_related('recipe')
    
    # Debug: Print out the favorite recipes and their featured images
    for favorite in favorite_recipes:
        print(f"Recipe: {favorite.recipe.title}, Image URL: {favorite.recipe.featured_image}")
    
    return render(request, 'recipes/view_favorite_recipes.html', {'favorite_recipes': favorite_recipes})
