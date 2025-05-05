from django.shortcuts import render
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
                'success': True,
                'user': UserSerializer(user).data,
                'tokens': tokens
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class WorkerRegistrationView(APIView):
    permission_classes = [permissions.IsAuthenticated, IsEngineer | IsAdmin]

    def post(self, request):
        try:
            serializer = WorkerRegistrationSerializer(data=request.data, context={"request": request})
            if serializer.is_valid():
                user = serializer.save()
                return Response({
                    'success': True,
                    'user': UserSerializer(user).data
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(e)
            return Response({"error": "User already exists."}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
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
        else:
            return CustomUser.objects.filter(user_type='worker')

class EngineerWorkersListView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated, IsEngineer]
    serializer_class = WorkerListSerializer

    def get_queryset(self):
        return CustomUser.objects.filter(user_type='worker', created_by=self.request.user)

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



class DeleteUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, user_id):
        try:
            user = CustomUser.objects.get(id=user_id)

            # Allow only Admins or Engineers who created the user
            if request.user.user_type not in ['admin', 'engineer']:
                return Response({"error": "Not authorized."}, status=status.HTTP_403_FORBIDDEN)

            if request.user.user_type == 'engineer' and user.created_by != request.user:
                return Response({"error": "You can only delete workers you created."}, status=status.HTTP_403_FORBIDDEN)

            user.delete()
            return Response({"success": True, "message": "User deleted successfully."}, status=status.HTTP_200_OK)

        except CustomUser.DoesNotExist:
            return Response({"error": "User not found."}, status=status.HTTP_404_NOT_FOUND)
