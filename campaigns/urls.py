from django.urls import path
from . import views

app_name = "campaigns"

urlpatterns = [
    path("phishing/", views.phishing_page, name="phishing"),
]
