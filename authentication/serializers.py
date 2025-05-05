from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db import IntegrityError
from rest_framework.exceptions import ValidationError

CustomUser = get_user_model()

# 1. General User Serializer
class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'email', 'user_type', 'worker_id')
        extra_kwargs = {'password': {'write_only': True}}


# 2. Engineer Registration
class EngineerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    username = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password')

    def create(self, validated_data):
        try:
            user = CustomUser.objects.create_user(
                email=validated_data['email'],
                password=validated_data['password'],
                username=validated_data['username'],
                user_type='engineer'
            )
            return user
        except IntegrityError as e:
            raise ValidationError({"detail": "A user with this email or username already exists."})
        except Exception as e:
            print(e)
            raise ValidationError({"detail": str(e)})


# 3. Worker Registration
class WorkerRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    worker_id = serializers.CharField(required=True)
    username = serializers.CharField(required=True)

    class Meta:
        model = CustomUser
        fields = ('username', 'email', 'password', 'worker_id', 'created_by')

    def create(self, validated_data):
        request = self.context.get('request')
        created_by = request.user if request and request.user.user_type == "engineer" else None

        return CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email'),
            password=validated_data['password'],
            worker_id=validated_data['worker_id'],
            user_type='worker',
            created_by=created_by
        )


# 4. Worker List (just adding username)
class WorkerListSerializer(serializers.ModelSerializer):
    created_by_name = serializers.CharField(source='created_by.username', read_only=True)

    class Meta:
        model = CustomUser
        fields = ('id', 'username', 'worker_id', 'email', 'user_type', 'date_joined', 'created_by_name')

# 5. Login Serializer (email or worker_id + password)
class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=False)
    worker_id = serializers.CharField(required=False)
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        worker_id = data.get("worker_id")
        password = data.get("password")

        if not (email or worker_id):
            raise serializers.ValidationError("Either email or worker_id is required")

        user = None

        try:
            if email:
                user = CustomUser.objects.get(email=email)
            elif worker_id:
                user = CustomUser.objects.get(worker_id=worker_id)
        except CustomUser.DoesNotExist:
            raise serializers.ValidationError("Invalid credentials")

        if not user.check_password(password):
            raise serializers.ValidationError("Invalid credentials")

        if not user.is_active:
            raise serializers.ValidationError("This account is inactive.")

        data["user"] = user
        return data
# from rest_framework import serializers
# from django.contrib.auth import authenticate
# from .models import CustomUser
# from django.contrib.auth import get_user_model

# class UserSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = ('id', 'email', 'user_type', 'worker_id')
#         extra_kwargs = {'password': {'write_only': True}}

# class EngineerRegistrationSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)
    
#     class Meta:
#         model = CustomUser
#         fields = ('email', 'password')
    
#     def create(self, validated_data):
#         user = CustomUser.objects.create_user(
#             email=validated_data['email'],
#             password=validated_data['password'],
#             user_type='engineer'
#         )
#         return user
# class WorkerListSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = CustomUser
#         fields = ('id', 'worker_id', 'email', 'user_type', 'date_joined', 'created_by')

 
# class WorkerRegistrationSerializer(serializers.ModelSerializer):
#     password = serializers.CharField(write_only=True)
#     worker_id = serializers.CharField(required=True)
    
#     class Meta:
#         model = CustomUser
#         fields = ('email', 'password', 'worker_id', 'created_by')

#     def create(self, validated_data):
#         request = self.context.get('request')  # Get the authenticated engineer from the request
#         created_by = request.user if request and request.user.user_type == "engineer" else None
        
#         user = CustomUser.objects.create_user(
#             email=validated_data.get('email'),
#             password=validated_data.get('password'),
#             worker_id=validated_data['worker_id'],
#             user_type='worker',
#             created_by=created_by  # Assign the engineer who created this worker
#         )
#         return user

 

# CustomUser = get_user_model()

# class LoginSerializer(serializers.Serializer):
#     email = serializers.EmailField(required=False)
#     worker_id = serializers.CharField(required=False)
#     password = serializers.CharField(write_only=True)

#     def validate(self, data):
#         email = data.get("email")
#         worker_id = data.get("worker_id")
#         password = data.get("password")

#         if not (email or worker_id):
#             raise serializers.ValidationError("Either email or worker_id is required")

#         user = None

#         if email:
#             try:
#                 user = CustomUser.objects.get(email=email)
#                 if not user.check_password(password):
#                     raise serializers.ValidationError("Invalid credentials")
#             except CustomUser.DoesNotExist:
#                 raise serializers.ValidationError("Invalid credentials")

#         elif worker_id:
#             try:
#                 user = CustomUser.objects.get(worker_id=worker_id)
#                 if not user.check_password(password):
#                     raise serializers.ValidationError("Invalid credentials")
#             except CustomUser.DoesNotExist:
#                 raise serializers.ValidationError("Invalid credentials")

#         if not user.is_active:
#             raise serializers.ValidationError("This account is inactive.")

#         data["user"] = user
#         return data
