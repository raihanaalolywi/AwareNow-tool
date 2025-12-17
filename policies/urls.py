from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    path('', views.policy_list, name='policy_list'),
    path('create/', views.create_policy, name='create_policy'),
    path('detail/<int:id>/', views.policy_detail, name='policy_detail'),
    path('acknowledge/', views.policy_acknowledge, name='policy_acknowledge'),
]
