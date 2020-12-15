from django.urls import include, path
from . import views

# アプリケーションの名前空間
# https://docs.djangoproject.com/ja/2.0/intro/tutorial03/
app_name = 'prescription'

urlpatterns = [
    path('result1', views.ResultView.as_view(), name='result1'),
    path('', views.IndexView.as_view(), name='index'),
    path('report/<slug:slug>/<uuid:prescription_id>/', views.ReportRedirectPageView.as_view(), name='report'),
    path('report', views.ReportPageView.as_view(), name='report'),
]
