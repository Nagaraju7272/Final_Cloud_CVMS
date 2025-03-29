from django.contrib import admin
from django.urls import path, include  # Add 'include' here
from visitor_app import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('visitor_app.urls')),  # This line now works with 'include' imported
    path('accounts/', include('django.contrib.auth.urls')),
    path('accounts/signup/', views.signup, name='signup'),
]