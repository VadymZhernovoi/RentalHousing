from django.urls import path

from .views import RegisterView, LoginView, LogoutView, UserLoggedInView

urlpatterns = [
    path("user/register/", RegisterView.as_view(), name='register'),
    path("user/login/", LoginView.as_view(), name='login'),
    path('user/logout/', LogoutView.as_view(), name='logout'),
    path("user/me/", UserLoggedInView.as_view()),
]