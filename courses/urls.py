from django.urls import path
from . import views

app_name = 'courses'

urlpatterns = [
    # Platform Admin URLs
    path('platform-admin/', views.platform_admin_dashboard, name='platform_admin_dashboard'),
    path('courses-dashboard/', views.courses_dashboard, name='courses_dashboard'),
    path('platform-admin/courses/create/', views.create_course, name='create_course'),
    path('platform-admin/courses/<int:course_id>/edit/', views.edit_course, name='edit_course'),
    # path('platform-admin/courses/<int:course_id>/assign/', views.assign_course_to_companies, name='assign_course_to_companies'),
    path('courses/<int:course_id>/deactivate/', views.deactivate_course, name='deactivate_course'),
    path('courses/<int:course_id>/activate/', views.activate_course, name='activate_course'),
    path(
    'platform-admin/courses/<int:course_id>/companies/',
    views.course_companies_view,
    name='course_companies_view'
    ),

    path('categories/', views.category_list, name='categories_list'),
    path('categories/create/', views.create_category, name='create_category'),
    path('categories/<int:pk>/edit/', views.update_category, name='update_category'),
    path('categories/<int:pk>/delete/', views.delete_category, name='delete_category'),


]