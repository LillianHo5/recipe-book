from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("recipe/<str:recipe_id>/", views.recipe_detail, name="recipe_detail"),
    path("top/", views.top_recipes, name="top_recipes"),
    path("stats/", views.recipe_statistics, name="recipe_stats"),
    path(
        "ingredient-search/", views.ingredient_vector_search, name="ingredient_search"
    ),

]