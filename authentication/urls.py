from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from . import views

urlpatterns = [
    path('register/engineer/', views.EngineerRegistrationView.as_view(), name='register_engineer'),
    path('register/worker/', views.WorkerRegistrationView.as_view(), name='register_worker'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('users/', views.UserListView.as_view(), name='user_list'),
    path('workers/', views.EngineerWorkersListView.as_view(), name='engineer-workers-list'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('user-role/', views.UserRoleView.as_view(), name='user-role'),



]
