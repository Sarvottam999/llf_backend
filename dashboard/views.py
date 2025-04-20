from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdmin, IsEngineer, IsWorker
from .models import Machine
from .serializers import MachineSerializer, AddInspectionReportSerializer, MachineWithDueDateSerializer
from rest_framework.generics import ListAPIView, RetrieveAPIView
from rest_framework import status, permissions
from rest_framework.views import APIView
from .models import InspectionReport, Escalation, PendingInspection
from django.utils.timezone import now
from datetime import datetime, timedelta, date
from calendar import monthrange
from django.shortcuts import get_object_or_404
import calendar
from authentication.models import CustomUser  # for fetching worker by ID
from django.db import DatabaseError
from rest_framework.exceptions import NotFound, ValidationError

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
            return Response(serializer.data
            , status=status.HTTP_200_OK)
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
    
    def list(self, request, *args, **kwargs):  
        queryset = self.get_queryset()  
        serialized_machines = self.get_serializer(queryset, many=True).data  

        # Machine Stats  
        total = queryset.count()   

        return Response({  
            "machine_stats": {  
                "total": total,  
                        "operational": queryset.filter(  worker__isnull=False).count(),
            "needs_inspection": queryset.filter( worker__isnull=False).count(),

            },  
            "machines": serialized_machines  
        })

    
# class MachineDetailView(RetrieveAPIView):
#     queryset = Machine.objects.all()
#     serializer_class = MachineSerializer
#     permission_classes = [IsAuthenticated, IsAdmin | IsEngineer | IsWorker]
#     lookup_field = 'id'
class MachineDetailView(RetrieveAPIView):
    queryset = Machine.objects.all()
    serializer_class = MachineSerializer
    permission_classes = [IsAuthenticated, IsAdmin | IsEngineer | IsWorker]
    lookup_field = 'id'

    def retrieve(self, request, *args, **kwargs):
        try:
            # Try to get the machine object, raise NotFound if not found
            machine = self.get_object()
        except Machine.DoesNotExist:
            raise NotFound(detail="Machine not found.", code=status.HTTP_404_NOT_FOUND)

        try:
            # Serialize the machine object
            serializer = self.get_serializer(machine)

            # Get the last inspection date
            last_inspection = InspectionReport.objects.filter(machine=machine).order_by('-timestamp').first()
            last_date = last_inspection.timestamp.date() if last_inspection else None

            # Get the next due date using the existing function
            next_due_date = get_machine_due_date(machine)

            # Return the response with additional data
            return Response({
                **serializer.data,
                "last_inspection_date": last_date,
                "next_due_date": next_due_date,
            }, status=status.HTTP_200_OK)

        except Exception as e:
            # Handle unexpected errors
            print(f"[ERROR] Error occurred while retrieving machine details: {str(e)}")
            return Response({
                "detail": "An error occurred while processing your request.",
                "error": str(e),
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AssignWorkerToMachineView(APIView):
    """
    Assign a worker to a machine.
    Payload:
    {
        "worker_id": 17
    }
    """
    # permission_classes = [IsAuthenticated, IsEngineeIsAdmin]

    def post(self, request):  
        machine_id = request.data.get("machine_id")  
        worker_id = request.data.get("worker_id")  

        if not machine_id or not worker_id:  
            return Response(  
                {"error": "Both 'machine_id' and 'worker_id' are required."},  
                status=status.HTTP_400_BAD_REQUEST  
            )  

        try:  
            machine = Machine.objects.get(id=machine_id)  
        except Machine.DoesNotExist:  
            return Response(  
                {"error": "Machine not found."},  
                status=status.HTTP_404_NOT_FOUND  
            )  

        try:  
            worker = CustomUser.objects.get(id=worker_id)  
        except CustomUser.DoesNotExist:  
            return Response(  
                {"error": "Worker not found."},  
                status=status.HTTP_404_NOT_FOUND  
            )  

        machine.worker = worker  
        machine.save()  

        return Response(  
            {"success": True, "message": f"Worker {worker.worker_id} assigned to Machine {machine.name}."},  
            status=status.HTTP_200_OK  
        )

# =======================   inspectio ==============================
 
class DashboardSummaryViewSet(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        try:
            user = request.user
            today = now().date()

            if user.user_type == 'worker':  # Assuming you have a role field in your CustomUser model
                print(f"[INFO] Worker Dashboard Summary requested for: {user}, Date: {today}")

                assigned_machines = Machine.objects.filter(worker=user)

                due_count = 0
                for machine in assigned_machines:
                    try:
                        if get_due_status(machine):
                            due_count += 1
                    except Exception as e:
                        print(f"[ERROR] get_due_status failed for machine ID {machine.id}: {e}")

                pending_count = PendingInspection.objects.filter(
                    machine__in=assigned_machines,
                    resolved=False
                ).count()

                escalation_count = Escalation.objects.filter(
                    machine__in=assigned_machines,
                    worker=user,
                    status='pending'
                ).count()

                return Response({
                    "role": "worker",
                    "due": due_count,
                    "pending": pending_count,
                    "escalated": escalation_count,
                }, status=status.HTTP_200_OK)

            elif user.user_type == 'engineer':
                print(f"[INFO] Engineer Dashboard Summary requested for: {user}, Date: {today}")

                # Get all machines assigned to workers under this engineer
                assigned_machines = Machine.objects.filter(engineer=user)

                # total_machines = assigned_machines.count()
                due_count = 0
                for machine in assigned_machines:
                    try:
                        if get_due_status(machine):
                            due_count += 1
                    except Exception as e:
                        print(f"[ERROR] get_due_status failed for machine ID {machine.id}: {e}")

                pending_count = PendingInspection.objects.filter(
                    machine__in=assigned_machines,
                    resolved=False
                ).count()

                escalation_count = Escalation.objects.filter(
                    engineer=user,
                    status='pending'
                ).count()

                return Response({
                    "role": "engineer",
                    "due": due_count,
                    "pending": pending_count,
                    "escalated": escalation_count,
                }, status=status.HTTP_200_OK)

            else:
                return Response({"error": "Unsupported user role."}, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(f"[ERROR] DashboardSummaryViewSet failed: {e}")
            return Response({
                "error": "Something went wrong while generating the dashboard summary."
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    
class EngineerMachineAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsEngineer]

    def get(self, request):
        user = request.user
 
        try:
            # 1. All machines created by this engineer
            total_machines = Machine.objects.filter(engineer=user)

            # 2. Assigned machines (worker is not null)
            assigned_count = total_machines.filter(worker__isnull=False).count()

            # 3. Not assigned machines
            unassigned_count = total_machines.filter(worker__isnull=True).count()

            # 4. Escalated machines (use distinct to avoid double-counting)
            escalated_count = Escalation.objects.filter(
                machine__in=total_machines,
                status='pending'
            ).values('machine').distinct().count()

            return Response({
                "total": total_machines.count(),
                "assigned": assigned_count,
                "unassigned": unassigned_count,
                "escalated": escalated_count
            }, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"[ERROR] EngineerMachineAnalyticsView failed: {e}")
            return Response({"error": "Something went wrong while fetching machine analytics."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# ---------------  get machines which are due to day ----------------

# class DueMachinesView(APIView):
#     permission_classes = [IsAuthenticated, IsWorker]

#     def get(self, request):
#         user = request.user
#         today = now().date()
#         print(f"[INFO] Worker Due Machines requested for: {user}, Date: {today}")

#         # 1. Get all machines assigned to this worker
#         assigned_machines = Machine.objects.filter(worker=user)
#         print(f"[INFO] Assigned Machines Count: {assigned_machines.count()}")

#         # 2. Filter machines that are due today
#         due_machines = []
#         for machine in assigned_machines:
#             try:
#                 if get_due_status(machine):
#                     due_machines.append(machine)
#             except Exception as e:
#                 print(f"[ERROR] get_due_status failed for machine ID {machine.id}: {e}")

#         # 3. Return due machines
#         # serializer = MachineSerializer(due_machines, many=True)
#         serializer = MachineWithDueDateSerializer(
#             due_machines,
#             many=True,
#             context={"due_date": today}
#         )

#         return Response(serializer.data, status=status.HTTP_200_OK) 


class DueMachinesView(APIView):
    permission_classes = [IsAuthenticated, IsWorker]

    def get(self, request):
        try:
            user = request.user
            today = now().date()
            view_type = request.query_params.get('type', 'due_today')  # default to 'due'
            print(f"[INFO] Worker Machine List requested for: {user}, Type: {view_type}, Date: {today}")

            # Get machines assigned to the worker
            try:
                assigned_machines = Machine.objects.filter(worker=user)
            except DatabaseError as e:
                print(f"[DB ERROR] Failed to fetch assigned machines: {e}")
                return Response({"error": "Unable to fetch assigned machines."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            result_machines = []

            if view_type == 'due_today':
                for machine in assigned_machines:
                    try:
                        if get_due_status(machine):
                            result_machines.append(machine)
                    except Exception as e:
                        print(f"[ERROR] get_due_status failed for machine ID {machine.id}: {e}")

            elif view_type == 'pending':
                try:
                    pending_qs = PendingInspection.objects.filter(
                        machine__in=assigned_machines,
                        resolved=False
                    ).select_related('machine')
                    result_machines = [pending.machine for pending in pending_qs]
                except DatabaseError as e:
                    print(f"[DB ERROR] Failed to fetch pending inspections: {e}")
                    return Response({"error": "Unable to fetch pending inspections."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            elif view_type == 'escalated':
                try:
                    escalated_qs = Escalation.objects.filter(
                        worker=user,
                        status='pending'
                    ).select_related('machine')
                    result_machines = [escalation.machine for escalation in escalated_qs]
                except DatabaseError as e:
                    print(f"[DB ERROR] Failed to fetch escalated machines: {e}")
                    return Response({"error": "Unable to fetch escalated machines."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            else:
                return Response({"error": "Invalid type. Use 'due', 'pending', or 'escalated'."},
                                status=status.HTTP_400_BAD_REQUEST)

            serializer = MachineWithDueDateSerializer(result_machines, many=True, context={"due_date": today})
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            print(f"[UNEXPECTED ERROR] DueMachinesView failed: {e}")
            return Response({"error": "Something went wrong while processing the request."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)

 
class MachineScheduleView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, machine_id):
        machine = get_object_or_404(Machine, id=machine_id)
        today = now().date()
        try:
            # Get month and year from query params, fallback to current
            month = int(request.query_params.get("month", today.month))
            year = int(request.query_params.get("year", today.year))

            # Start and end of requested month
            month_start = date(year, month, 1)
            last_day = calendar.monthrange(year, month)[1]
            month_end = date(year, month, last_day)

            if machine.inspection_frequency == "daily":
                return Response(self.get_daily_schedule(machine, today, month_start, month_end))
            elif machine.inspection_frequency == "weekly":
                return Response(self.get_weekly_schedule(machine, today, month_start, month_end))
            else:
                return Response({"message": "Monthly schedule not implemented yet"}, status=status.HTTP_501_NOT_IMPLEMENTED)
        except ValueError:
            return Response({"error": "Invalid month or year provided."}, status=status.HTTP_400_BAD_REQUEST)

    def get_daily_schedule(self, machine, today, start_date, end_date):
        schedule = []
        current_day = start_date
        day_count = 1

        while current_day <= end_date:
            label = f"Day {day_count}"

            if current_day > today:
                status_label = "scheduled"
            elif InspectionReport.objects.filter(machine=machine, due_date=current_day).exists():
                status_label = "completed"
            elif PendingInspection.objects.filter(machine=machine, date_due=current_day, resolved=False).exists():
                status_label = "pending"
            else:
                status_label = "missed" if current_day < today else "scheduled"

            schedule.append({
                "schedule": label,
                "status": status_label
            })

            current_day += timedelta(days=1)
            day_count += 1

        return schedule

    def get_weekly_schedule(self, machine, today, start_date, end_date):
        schedule = []
        week_num = 1
        current_start = start_date

        while current_start <= end_date:
            week_start = current_start
            week_end = min(week_start + timedelta(days=6), end_date)
            label = f"Week {week_num} ({week_start.strftime('%b %-d')}-{week_end.strftime('%-d')})"

            if week_end > today:
                status_label = "scheduled"
            elif InspectionReport.objects.filter(machine=machine, due_date__range=[week_start, week_end]).exists():
                status_label = "completed"
            elif PendingInspection.objects.filter(machine=machine, date_due__range=[week_start, week_end], resolved=False).exists():
                status_label = "pending"
            else:
                status_label = "missed" if week_end < today else "scheduled"

            schedule.append({
                "schedule": label,
                "status": status_label
            })

            current_start += timedelta(weeks=1)
            week_num += 1

        return schedule

class AddInspectionReportView(APIView):
    permission_classes = [IsAuthenticated]
    def post(self, request):  
        serializer = AddInspectionReportSerializer(data=request.data, context={"request": request})  
        if serializer.is_valid():  
            data = serializer.validated_data  
            machine = data['machine']  
            worker = request.user  

            # Update status to normal by default unless escalated  
            machine.status = "abnormal" if data.get("is_escalated") else "normal"  
            machine.save()

            # Resolve PendingInspection if exists  
            pending = PendingInspection.objects.filter(machine=machine, date_due=now().date(), resolved=False).first()  
            if pending:  
                pending.resolved = True  
                pending.save()

            # Create inspection report  
            report = InspectionReport.objects.create(  
                machine=machine,  
                worker=worker,  
                look=data['look'],  
                feel=data['feel'],  
                sound=data['sound'],  
                is_escalated=data.get('is_escalated', False),  
                due_date=get_machine_due_date(machine),  
            )

            # Create Escalation if needed  
            if data.get('is_escalated'):  
                Escalation.objects.create(  
                    machine=machine,  
                    worker=worker,  
                    engineer=machine.engineer,  
                    report=report,  
                    comment=data.get('comment', ''),  
                )

            return Response({"message": "Inspection submitted successfully"}, status=status.HTTP_201_CREATED)  
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)






# ---------------  get due status ----------------
def get_due_status(machine):
    today = date.today()
    #  custom date for testing
    # today = datetime(2025, 4, 30).date()
    if machine.inspection_frequency == 'daily':
        print('in  ==>', 'daily')
        inspection_done_today = InspectionReport.objects.filter(
            machine=machine,
            timestamp__date=today
        ).exists()
        print('## inspection_done_today ==>', inspection_done_today)
        return not inspection_done_today  # Due if not done today
    elif machine.inspection_frequency == 'weekly':
        print('in  ==>', 'weekly')
        # Get the start (Monday) and end (Sunday) of the current week
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=5)          # Sunday

        inspection_done_this_week = InspectionReport.objects.filter(
            machine=machine,
            timestamp__date__gte=start_of_week,
            timestamp__date__lte=today
        ).exists()

        if inspection_done_this_week:
            return False  # Already inspected this week

        if today != end_of_week:
            return False  # Not due yet

        return True  # Due today (last day of the week, no inspection yet)

    elif machine.inspection_frequency == 'monthly':
        print('in  ==>', 'monthly')
        first_day_of_month = today.replace(day=1)
        last_day = monthrange(today.year, today.month)[1]
        last_day_of_month = today.replace(day=last_day)

        inspection_done_this_month = InspectionReport.objects.filter(
            machine=machine,
            timestamp__date__gte=first_day_of_month,
            timestamp__date__lte=today
        ).exists()

        if inspection_done_this_month:
            return False

        if today != last_day_of_month:
            return False

        return True  # Due today (last day of the month, no inspection yet)


def get_machine_due_date(machine):
    today = date.today()

    if machine.inspection_frequency == 'daily':
        # It's always due today unless done already
        return today

    elif machine.inspection_frequency == 'weekly':
        # End of the current week (assuming Sunday is last day of the week)
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        due_date = start_of_week + timedelta(days=5)  # Saturday
        return due_date

    elif machine.inspection_frequency == 'monthly':
        # Get the last day of the current month
        last_day = monthrange(today.year, today.month)[1]
        due_date = today.replace(day=last_day)
        return due_date
