from django.http import JsonResponse


def hello_world(request):
    """Simple API endpoint that returns hello world."""
    return JsonResponse({"hello": "world"})
