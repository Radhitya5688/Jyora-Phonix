from django.contrib import admin
from django.urls import path
from phones import views

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("buy/", views.buy, name="buy"),
    path("compare/", views.compare, name="compare"),
    path("processor-lab/", views.processor_lab, name="processor_lab"),
    path("suggest-me/", views.suggest_me, name="suggest_me"),
    path("about/", views.placeholder_page, {"page_name": "About Jyora Phonix"}, name="about"),
]
