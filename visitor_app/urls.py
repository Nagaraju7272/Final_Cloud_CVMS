from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),  # Root URL for logged-in users
    path('visitors/', views.visitors, name='visitors'),
    path('add_visitor/', views.add_visitor, name='add_visitor'),
    path('manage_visitors/', views.manage_visitors, name='manage_visitors'),
    path('update_visitor/<str:phone>/', views.update_visitor, name='update_visitor'),  # New URL for updating
    path('reports/', views.reports, name='reports'),
    path('search/', views.search, name='search'),
    path('accounts/signup/', views.signup, name='signup'),
    path('accounts/signup/', views.signup, name='signup'),
    path('delete_visitor/<str:phone>/', views.delete_visitor, name='delete_visitor'),
]