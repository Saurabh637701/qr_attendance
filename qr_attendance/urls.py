from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("qr_app.urls")),
    path('login/', include("login.urls")),# ✅ qr_app से connect
    path('', lambda request: redirect('user_login')),
]



