from django.urls import path

from . import views

app_name = "authentication"

urlpatterns = [
    path("signup/", views.signup_view, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    
    path("profile/", views.profile_view, name="profile"),
    path("profile/activity/", views.activity_view, name="activity"),
    path("profile/rentals/", views.rentals_view, name="rentals"),            
    path("profile/shop-report/", views.shop_report_view, name="shop_report"), 
    path("profile/edit/", views.edit_profile_view, name="edit_profile"),

    path("profile/password/", views.change_password_view, name="change_password"),
    path("profile/delete/", views.delete_account_view, name="delete_account"),
]
