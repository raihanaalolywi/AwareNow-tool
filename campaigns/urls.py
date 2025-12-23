from django.urls import path
from . import views

app_name = "campaigns"

urlpatterns = [
    path("phishing/", views.phishing_list, name="phishing"),
    path("phishing/create/", views.phishing_create, name="phishing-create"),
    
    path("template/preview/<int:pk>/", views.template_preview, name="template-preview"),

    #tracking
    path("t/open/<uuid:token>.png", views.track_open, name="track-open"),
    path("t/click/<uuid:token>/", views.track_click, name="track-click"),
    path("t/fall/<uuid:token>/", views.track_fall, name="track-fall"),

    path(
        "phishing/<int:campaign_id>/send/",
        views.publish_and_send,
        name="publish-send",
    ),
]
