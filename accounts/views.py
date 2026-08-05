from django.contrib.auth import get_user_model, login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST


@login_required
def home(request):
    return HttpResponse(f"Bienvenue {request.user.username}, tu es connecte.")


@require_POST
def register(request):
    username = request.POST.get("username", "").strip()
    email = request.POST.get("email", "").strip()
    password = request.POST.get("password", "")

    if not username or not email or not password:
        return render(
            request,
            "index.html",
            {
                "register_error": "Tous les champs sont obligatoires.",
                "show_register": True,
            },
        )

    User = get_user_model()

    if User.objects.filter(username=username).exists():
        return render(
            request,
            "index.html",
            {
                "register_error": "Ce pseudonyme est deja utilise.",
                "show_register": True,
            },
        )

    if User.objects.filter(email=email).exists():
        return render(
            request,
            "index.html",
            {
                "register_error": "Cette adresse e-mail est deja utilisee.",
                "show_register": True,
            },
        )

    user = User(username=username, email=email)

    try:
        validate_password(password, user=user)
    except ValidationError as error:
        return render(
            request,
            "index.html",
            {
                "register_error": " ".join(error.messages),
                "show_register": True,
            },
        )

    user.set_password(password)
    user.save()
    login(request, user)

    return redirect("home")
