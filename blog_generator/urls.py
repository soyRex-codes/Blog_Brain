from django.urls import path
from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('login', views.user_login, name='login'),
    path('signup', views.user_signup, name='signup'),
    path('logout/', views.user_logout, name='logout'),
    path('generate-blog', views.generate_blog, name='generate-blog'),
    path('blog-list/', views.blog_list, name='blog-list'),
    path('blog-list/logout', views.user_logout, name='blog-list'),
    path('blog-list/blog-details/<int:pk>', views.blog_details, name='blog-details'),
    path('blog-list/blog-details/<int:pk>/logout', views.user_logout, name='blog-details'),
    path('blog-list/blog-details/logout', views.user_logout, name='blog-details'),

]