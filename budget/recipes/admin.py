from django.contrib import admin
from .models import Recipe

@admin.register(Recipe)
class RecipeAdmin(admin.ModelAdmin):
    list_display = ('title', 'owner', 'original_url', 'featured_image')
    search_fields = ('title', 'ingredients', 'owner__username')


# Register your models here.
