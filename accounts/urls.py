from django.urls import path

from . import views


urlpatterns = [
    # Halaman auth server-rendered (dipakai template login/register/logout)
    path('login/', views.AccountLoginView.as_view(), name='login'),
    path('register/', views.RegisterView.as_view(), name='register'),
    path('logout/', views.AccountLogoutView.as_view(), name='logout'),

    # Profil tamu & preferensi akun
    path('profile/', views.GuestProfileView.as_view(), name='profile'),
    path('password/', views.AccountPasswordChangeView.as_view(), name='password_change'),

    # API JSON (dipakai untuk user management / integrasi terpisah)
    path('api/register/', views.register, name='api_register'),
    path('api/login/', views.login_view, name='api_login'),
    path('api/logout/', views.logout_view, name='api_logout'),
    path('api/me/', views.me, name='me'),
    path('api/users/', views.users, name='users'),
    path('api/users/<int:pk>/', views.user_detail, name='user_detail'),
]
