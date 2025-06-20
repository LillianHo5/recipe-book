from django.shortcuts import render
import voyageai
from bson import ObjectId
from bson.errors import InvalidId
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from dotenv import load_dotenv

from .models import Recipe

load_dotenv()

# Create your views here.
def index(request):
    return render(request, "index.html", {"message": "Recipes App"})

def top_recipes(request):
    recipes = Recipe.objects.all().order_by("title")[:20]

    return render(request, "top_recipes.html", {"recipes": recipes})

def recipe_detail(request, recipe_id):
    """
    Display a recipe by its MongoDB ObjectId

    Args:
        request: Django request object
        recipe_id: String representation of the MongoDB ObjectId
    """
    # Convert string ID to MongoDB ObjectId
    try:
        object_id = ObjectId(recipe_id)
    except InvalidId:
        raise Http404(f"Invalid recipe ID format: {recipe_id}")

    # Get the recipe or return 404
    recipe = get_object_or_404(Recipe, id=object_id)

    # Create context with all needed data
    context = {"recipe": recipe}

    return render(request, "recipe_detail.html", context)

def recipe_statistics(request):

    # Define the aggregation pipeline
    pipeline = [
        # Stage 1: Extract cuisine from the features subdocument
        {"$project": {"_id": 1, "cuisine": "$features.cuisine"}},
        # Stage 2: Group by cuisine and count occurrences
        {"$group": {"_id": "$cuisine", "count": {"$sum": 1}}},
        # Stage 3: Sort by count in descending order
        {"$sort": {"count": -1}},
        # Stage 4: Reshape the output for better readability
        {
            "$project": {
                "_id": 1,
                "cuisine": {"$ifNull": ["$_id", "Unspecified"]},
                "count": 1,
            }
        },
    ]

    stats = Recipe.objects.raw_aggregate(pipeline)
    result = list(stats)

    return render(
        request,
        "statistics.html",
        {"cuisine_stats": result},
    )

def perform_vector_search(query_text, limit=10, num_candidates=None):
    if num_candidates is None:
        num_candidates = limit * 3

    try:
        # Generate embedding for the search query
        vo = voyageai.Client()  # Uses VOYAGE_API_KEY from environment
        query_embedding = vo.embed(
            [query_text], model="voyage-lite-01-instruct", input_type="query"
        ).embeddings[0]

        # Use Django's raw_aggregate to perform vector search
        results = Recipe.objects.raw_aggregate([
            {
                "$vectorSearch": {
                    "index": "recipe_vector_index",
                    "path": "voyage_embedding",
                    "queryVector": query_embedding,
                    "numCandidates": num_candidates,
                    "limit": limit,
                }
            },
            {
                "$project": {
                    "_id": 1,
                    "title": 1,
                    "ingredients": 1,
                    "instructions": 1,
                    "features": 1,
                    "score": {"$meta": "vectorSearchScore"},
                }
            },
        ])

        # Format the results - accessing attributes directly
        recipes = []
        for recipe in results:
            try:
                # Try direct attribute access first
                recipe_dict = {
                    "id": str(recipe.id),
                    "title": recipe.title,
                    "ingredients": recipe.ingredients,
                    "instructions": getattr(recipe, "instructions", ""),
                    "features": getattr(recipe, "features", {}),
                    "similarity_score": getattr(recipe, "score", 0),
                }
                recipes.append(recipe_dict)
            except Exception as e:
                print(f"Error formatting recipe: {str(e)}")
        return recipes

    except Exception as e:
        print(f"Error in vector search: {str(e)}")
        return []
    
def ingredient_vector_search(request):
    """
    View for searching recipes by ingredients using vector search
    """
    query = request.GET.get("query", "")
    results = []

    if query:
        ingredient_query = f"Ingredients: {query}"
        results = perform_vector_search(ingredient_query, limit=10)

    context = {"query": query, "results": results}
    return render(request, "vector_search.html", context)

