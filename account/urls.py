from django.urls import path
from . import views

app_name = 'account'
urlpatterns = [
    path("login/", views.platform_login, name="platform-login"),
    path("dashboard/", views.platform_dashboard, name="platform-dashboard"),
    path("company/dashboard/", views.company_dashboard, name="company-dashboard"),
    path("employee/dashboard/", views.employee_dashboard, name="employee-dashboard"),
    path("companies/create/", views.create_company, name="create-company"),
    path("logout/", views.logout_view, name="logout"),
    path(
    "activate/<uuid:token>/",
    views.activate_account,
    name="activate-account"
    ),
    path("company/users/", views.company_users, name="company-users"),
    path("company/users/<int:user_id>/toggle-active/", views.toggle_user_active, name="toggle-user-active"),

    # path("company/groups/", views.company_groups, name="company-groups"),
    # path("company/groups/create/", views.create_group, name="create-group"),
    # path("company/groups/<int:group_id>/", views.group_detail, name="group-detail"),
    # path(
    #     "company/groups/<int:group_id>/delete/",
    #     views.delete_group,
    #     name="delete-group"
    # ),
    # path(
    #     "company/groups/<int:group_id>/remove-user/<int:user_id>/",
    #     views.remove_user_from_group,
    #     name="remove-user-from-group"
    # ),


]