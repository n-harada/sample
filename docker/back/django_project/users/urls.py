from django.urls import path
from django.contrib.auth.views import LoginView, LogoutView
# アプリケーションの名前空間
# https://docs.djangoproject.com/ja/2.0/intro/tutorial03/
app_name = 'users'


urlpatterns = [
    path('login/', LoginView.as_view(template_name='login.html'), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
]
