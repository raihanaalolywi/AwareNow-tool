from django.urls import path
from . import views

app_name = 'policies'

urlpatterns = [
    # Company
    # path("", views.policy_list, name="policy_list"), 
    path('company/', views.company_policy_dashboard, name='company_policies'),
    path('company/create/', views.create_policy, name='create_policy'),

    # Employee
    path('employee/', views.employee_policies, name='employee_policies'),
    path('acknowledge/<int:id>/', views.policy_acknowledge, name='policy_acknowledge'),
]
