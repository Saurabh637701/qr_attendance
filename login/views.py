from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import logout

def user_login(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)

            # Agar admin hai to admin dashboard pr bhejo
            if user.is_superuser:
                return redirect("/admin/")

            # Normal user ho to qr_app home pr bhejo
            return redirect("home")

        else:
            messages.error(request, "Invalid Username or Password")

    return render(request, "login/login.html")




def user_logout(request):
    logout(request)
    return redirect("user_login")
