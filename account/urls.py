from django.urls import path
from . import views

app_name = 'account'
urlpatterns = [
    path("login/", views.platform_login, name="platform-login"),
    path("dashboard/", views.platform_dashboard, name="platform-dashboard"),
    path("company/dashboard/", views.company_dashboard, name="company-dashboard"),
    path("employee/dashboard/", views.employee_dashboard, name="employee-dashboard"),
    path("companies/create/", views.create_company, name="create-company"),
    # path(
    # "companies/<int:company_id>/super-admin/",
    # views.create_super_admin,
    # name="create-super-admin"
    # ),
    path("logout/", views.logout_view, name="logout"),
    path(
    "activate/<uuid:token>/",
    views.activate_account,
    name="activate-account"
),

]