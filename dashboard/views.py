from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdmin, IsEngineer, IsWorker
from .models import Machine
from .serializers import MachineSerializer
from rest_framework.generics import ListAPIView
from rest_framework import status


# #########################   machine ##############################
class MachineListView(APIView):
    """Only Engineers & Admins can view the list of machines."""
    permission_classes = [IsAuthenticated, IsEngineer | IsAdmin]

    def get(self, request):
        machines = Machine.objects.all()
        serializer = MachineSerializer(machines, many=True)
        return Response(serializer.data)

#  -----------  create a machine --------------
class MachineCreateView(APIView):

    """
    {
        "name": "Lathe Machine",
        "worker": 17,
        "status": "normal",
        "inspection_frequency": "daily",
        "location": "Factory Floor A"
    }
    """
    """Only Engineers and Admins can create machines."""
    permission_classes = [IsAuthenticated, IsEngineer | IsAdmin]

    def post(self, request):
        user = request.user  # Get the logged-in user

        if user.user_type not in ["engineer", "admin"]:
            return Response({"error": "Only engineers and admins can create machines."}, status=403)

        # Automatically assign the logged-in engineer
        request.data["engineer"] = user.id
        print('## user.id ==>', 
              request.data
              )

        serializer = MachineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "message": "Machine created successfully."}, status=status.HTTP_201_CREATED)
        
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


# class WorkerMachineListView(APIView):
    # """Workers can only view their assigned machines."""
    # permission_classes = [IsAuthenticated, IsWorker]

    # def get(self, request):
    #     machines = Machine.objects.filter(worker=request.user)

    #     if machines.exists():
    #         serializer = MachineSerializer(machines, many=True)
    #         return Response({
    #             "success": True,
    #             "message": "Machines retrieved successfully.",
    #             "data": serializer.data
    #         }, status=200)
    #     else:
    #         return Response({
    #             "success": False,
    #             "message": "No machines assigned to this worker."
    #         }, status=404)

    
class MachineByUser(ListAPIView):
    serializer_class = MachineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user

        if user.user_type == "worker":
            return Machine.objects.filter(worker__worker_id=user.worker_id)

        elif user.user_type == "engineer":
            return Machine.objects.filter(engineer=user)

        elif user.user_type == "admin":
            return Machine.objects.all()

        return Machine.objects.none()

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        if queryset.exists():
            serializer = self.get_serializer(queryset, many=True)
            return Response({
                "success": True,
                "message": "Machines retrieved successfully.",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "success": False,
                "message": "No machines found for the current user."
            }, status=status.HTTP_404_NOT_FOUND)

class EngineerCreatedMachinesView(ListAPIView):
    print('## = user ##')

    serializer_class = MachineSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        print('## = user', user)
        print('## = user', user, user.user_type)

        # Ensure the logged-in user is an engineer or admin
        if user.user_type == "engineer":
            return Machine.objects.filter(engineer=user)
        elif user.user_type == "admin":
            return Machine.objects.all()  # Admin can see all machines

        # If the user is neither an engineer nor an admin, deny access
        return Machine.objects.none()  # Return empty queryset to avoid permission errors
