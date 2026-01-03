from django.contrib.auth.models import User
from django.db import models
from django.utils.translation import gettext_lazy as _

class Recipe(models.Model):
    title = models.CharField(max_length=255)
    ingredients = models.TextField()
    instructions = models.TextField()
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    featured_image = models.URLField(max_length=500, blank=True, null=True)
    original_url = models.URLField(max_length=500, blank=True, null=True)
    shared_with = models.ManyToManyField(User, related_name='shared_recipes', blank=True)

    def __str__(self):
        return self.title

class RecipeBook(models.Model):
    name = models.CharField(max_length=200)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)  # Owner of the recipe book
    recipes = models.ManyToManyField(Recipe, blank=True)
    is_shared = models.BooleanField(default=False)  # If you want a shared book option

    def __str__(self):
        return self.name
    
class GroceryList(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='grocery_lists')
    name = models.CharField(max_length=255)
    items = models.TextField()  # Store items as text or set up a more advanced structure for ingredients

    def __str__(self):
        return f"Grocery List: {self.name}"


class Comment(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='comments')
    author = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'Comment by {self.author.username} on {self.recipe.title}'

class SharedRecipeList(models.Model):
    name = models.CharField(max_length=200)
    users = models.ManyToManyField(User)
    recipes = models.ManyToManyField(Recipe, blank=True)

    def __str__(self):
        return self.name

class UserFavoriteRecipe(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='favorite_recipes')
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE, related_name='favorited_by')

    class Meta:
        unique_together = ('user', 'recipe')

    def __str__(self):
        return f'{self.user.username} likes {self.recipe.title}'

class CookbookUpload(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='cookbook_uploads')
    file = models.FileField(upload_to='cookbook_uploads/')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Upload {self.id} by {self.owner.username} - {self.status}"


class RecipeDraft(models.Model):
    upload = models.ForeignKey(CookbookUpload, on_delete=models.CASCADE, related_name='drafts')
    title_guess = models.CharField(max_length=500, blank=True)
    raw_text = models.TextField()
    parsed_title = models.CharField(max_length=500, blank=True)
    parsed_ingredients = models.JSONField(default=list, blank=True)
    parsed_steps = models.JSONField(default=list, blank=True)
    confidence = models.FloatField(default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)
    imported_recipe = models.ForeignKey(Recipe, on_delete=models.SET_NULL, null=True, blank=True, related_name='source_draft')
    imported = models.BooleanField(default=False)

    def __str__(self):
        return f"Draft: {self.parsed_title or self.title_guess} (confidence: {self.confidence})"

