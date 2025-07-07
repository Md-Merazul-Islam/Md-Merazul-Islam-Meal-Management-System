from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    RegisterAPIView, LoginView,
    LogoutView, RefreshTokenView, ForgotPasswordView,  PasswordChangeView, ResetPasswordView, ProfileView, PostalCodeView,
    ValidateOTPView, AllUsers, UserListView, UpdateTrialStatusView, DeliveryManListView, CommitmentForSixMonthsViewSet,CommitmentAgreementView,UserCommitmentView
)

router = DefaultRouter()
router.register(r'all-users', AllUsers, basename='allusers')
router.register('commitment-status',CommitmentForSixMonthsViewSet, basename='commitment-for-six-months')

urlpatterns = [
    # for admin
    path('', include(router.urls)),
    path('register/', RegisterAPIView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('profile/', ProfileView.as_view(), name='profile'),
    path('token/refresh/', RefreshTokenView.as_view(), name='token_refresh'),

    # --- password_change
    path('password-change/', PasswordChangeView.as_view(), name='password_change'),
    # --forgot_password
    path('otp-send/', ForgotPasswordView.as_view(), name='forgot_password'),
    path('validate-otp/', ValidateOTPView.as_view(), name='validate_otp'),
    path('set-new-password/', ResetPasswordView.as_view(), name='reset_password'),

    # check postal code
    path('postal-code/', PostalCodeView.as_view(), name='postal-code'),
    path('trial-users/', UserListView.as_view(), name='user-list'),
    path('trial-users/<int:user_id>/',
         UpdateTrialStatusView.as_view(), name='update-trial-status'),

    path('delivery-men/', DeliveryManListView.as_view(), name='delivery-man-list'),
    
    #commitment agreement
    path('commitment-agreement/', CommitmentAgreementView.as_view(), name='commitment-agreement'),
    
    path('user-commitment/', UserCommitmentView.as_view(), name='user-commitment'),

]
