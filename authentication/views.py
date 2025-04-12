from django.shortcuts import render

# Create your views here.
from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser
from .serializers import (
    EngineerRegistrationSerializer, 
    WorkerRegistrationSerializer, 
    LoginSerializer,
    UserSerializer, 
    WorkerListSerializer
)

class IsEngineer(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'engineer'

class IsAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        return request.user.is_authenticated and request.user.user_type == 'admin'

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class EngineerRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = EngineerRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            tokens = get_tokens_for_user(user)
            return Response({
                'successs' : True
                # 'user': UserSerializer(user).data,
                # 'tokens': tokens
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WorkerRegistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEngineer | IsAdmin]

    def post(self, request):
        print('### request ====>', request.data)
        try:
            serializer = WorkerRegistrationSerializer(data=request.data, context={"request": request})  # Pass request to serializer
            if serializer.is_valid():
                user = serializer.save()
                return Response('sucess', status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({"error": 'User already exists.'}, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    # permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            tokens = get_tokens_for_user(user)
            return Response({
                'user': UserSerializer(user).data,
                'tokens': tokens
            })
        return Response('Invalid Email or Password.', status=status.HTTP_400_BAD_REQUEST)

class UserListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsAdmin | IsEngineer]
    serializer_class = UserSerializer
    
    def get_queryset(self):
        if self.request.user.user_type == 'admin':
            return CustomUser.objects.all()
        else:  # engineer can only see workers
            return CustomUser.objects.filter(user_type='worker')


class EngineerWorkersListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsEngineer]  # Only engineers can access
    serializer_class = WorkerListSerializer
 

    def get_queryset(self):
        try:

            return CustomUser.objects.filter(user_type='worker', created_by=self.request.user)
        except Exception as e:
            print(e)
            return Response({"error": e}, status=status.HTTP_400_BAD_REQUEST)

class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data.get("refresh")
            if not refresh_token:
                return Response({"error": "Refresh token is required"}, status=status.HTTP_400_BAD_REQUEST)

            token = RefreshToken(refresh_token)
            token.blacklist()

            return Response({"message": "Successfully logged out"}, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"error": "Invalid token or already logged out"}, status=status.HTTP_400_BAD_REQUEST)

 
class UserRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user_data = UserSerializer(request.user).data
        return Response(user_data, status=status.HTTP_200_OK)
