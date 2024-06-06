from authapp import views
from django.urls import path

urlpatterns = [
    path('signup', views.signup, name='signup'),
    path('login', views.loogin, name='login'),
    path('logout', views.loogout, name='logout'),
    path('otp-verification', views.OtpVerification, name='otpverification'),
    path('activate/<uidb64>/<token>/', views.ActivateAccountView.as_view(),
         name='activate'),
    path('request-rest-email', views.RequestRestEmailView.as_view(),
         name='request-rest-email'),
    path('set-new-password/<uidb64>/<token>',
         views.SetNewPasswordView.as_view(), name='set-new-password'),
    path('view_profile', views.view_profile, name='view_profile'),
    path('edit_profile', views.edit_profile, name='edit_profile'),
    path('change_password', views.change_password, name='change_password'),
    path('user_view_coupons', views.user_view_coupons,
         name='user_view_coupons'),
    path('manage_address', views.manage_address, name='manage_address'),
    # wallet
    path('my_wallet', views.my_wallet, name='my_wallet'),
    path('withdraw_funds', views.withdraw_funds, name='withdraw_funds'),
    path('add_to_wallet', views.add_to_wallet, name='add_to_wallet'),

]
