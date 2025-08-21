from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from django.contrib.auth import get_user_model

User = get_user_model()

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        # If the user is already linked, nothing to do
        if sociallogin.is_existing:
            return
        
        # Try to find an existing user by email
        email = sociallogin.account.extra_data.get("email")
        if email:
            try:
                user = User.objects.get(email=email)
                # Connect the Google account to the existing user
                sociallogin.connect(request, user)
            except User.DoesNotExist:
                pass
