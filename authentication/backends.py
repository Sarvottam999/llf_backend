from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()

class MultiFieldModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        # First, try to authenticate with the provided credentials
        if username is None:
            username = kwargs.get(User.USERNAME_FIELD)
        
        if username is None or password is None:
            return None
        
        # Check if username is an email
        if '@' in username:
            # Try to authenticate as engineer with email
            try:
                user = User.objects.get(email=username, user_type='engineer')
                if user.check_password(password):
                    return user
            except User.DoesNotExist:
                pass
        
        # Check if username might be a worker_id
        try:
            print('========= inside eworker ')
            user = User.objects.get(worker_id=username, user_type='worker')
            print('=========  user ==>', user)
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            pass
        
        # Lastly, try username for admin
        try:
            user = User.objects.get(username=username, user_type='admin')
            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        
        return None