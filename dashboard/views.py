from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from .permissions import IsAdmin, IsEngineer, IsWorker
from .models import Machine
from .serializers import MachineSerializer,   MachineWithDueDateSerializer, InspectionReportSerializer
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
from io import StringIO
from django.core.management import call_command
import re

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
        # print('## user.id ==>', 
        #       request.data
        #       )

        serializer = MachineSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"success": True, "message": "Machine created successfully."}, status=status.HTTP_201_CREATED)
        
        return Response({"success": False, "errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

class MachineDeleteView(APIView):
    permission_classes = [IsAuthenticated, IsEngineer | IsAdmin]

    def delete(self, request, machine_id):
        try:
            machine = Machine.objects.get(id=machine_id)

            # Only the assigned engineer or admin can delete
            if request.user.user_type == 'engineer' and machine.engineer != request.user:
                return Response({"error": "You are not authorized to delete this machine."}, status=status.HTTP_403_FORBIDDEN)

            machine.delete()
            return Response({"success": True, "message": "Machine deleted successfully."}, status=status.HTTP_200_OK)

        except Machine.DoesNotExist:
            return Response({"error": "Machine not found."}, status=status.HTTP_404_NOT_FOUND)

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

            if user.user_type == 'worker':  
                print(f"[INFO] Worker Dashboard Summary requested for: {user}, Date: {today}")

                assigned_machines = Machine.objects.filter(worker=user)

                due_count = 0
                for machine in assigned_machines:
                    try:
                        if get_due_status(machine):
                            due_count += 1
                    except Exception as e:
                        print(f"[ERROR] get_due_status failed for machine ID {machine.id}: {e}")

                
                pending_count1 =  assigned_machines.filter(
                    inspectionreport__is_escalated=True
                )
                print('pending_count1 ==>' , pending_count1)
                pending_count = PendingInspection.objects.filter(
                    machine__in=assigned_machines,
                    resolved=False
                ).exclude(
                    machine__in = pending_count1
                ).count()


                escalation_count = assigned_machines.filter(
                        inspectionreport__is_escalated=True
                    ).count()
                # result_machines = escalated_qs
                print(f" ## escalated_qs 11 ==> {escalation_count}")
                # pending_count = PendingInspection.objects.filter(
                #     machine__in=pending_count1,
                #     resolved=False
                # ).count()


                # escalation_count = Escalation.objects.filter(
                #     machine__in=assigned_machines,
                #     worker=user,
                #     status='pending'
                # ).count()
                

                return Response({
                    # "role": "worker",
                    "due": due_count,
                    "pending": pending_count,
                    "escalated": escalation_count,
                }, status=status.HTTP_200_OK)

            elif user.user_type == 'engineer':
                print(f"[INFO] Engineer Dashboard Summary requested for: {user}, Date: {today}")

                # Get all machines assigned to workers under this engineer
                assigned_machines = Machine.objects.filter(engineer=user)

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
                escalation_count = assigned_machines.filter(
                        inspectionreport__is_escalated=True
                    ).count()
                print(f"## escalation_count 21==> {escalation_count}")
                return Response({ 
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

                    # result_machines = assigned_machines.filter(
                    #     id__in=pending_qs.values_list('machine_id', flat=True).distinct(),
                    # ).distinct()
                    results = []
                    for pending in pending_qs:
                        serializer = MachineWithDueDateSerializer(
                            pending.machine,
                            context={"due_date": pending.date_due}
                        )
                        results.append(serializer.data)

                    print(f'### results ==> ', results)
                    return Response(results, status=status.HTTP_200_OK)
                    

                except DatabaseError as e:
                    print(f"[DB ERROR] Failed to fetch pending inspections: {e}")
                    return Response({"error": "Unable to fetch pending inspections."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            elif view_type == 'escalated':
                try:
                    escalated_qs = assigned_machines.filter(
                        inspectionreport__is_escalated=True
                    ).distinct()
                    result_machines = escalated_qs
                    print(f" ## escalated_qs ==> {escalated_qs}")

                    
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
            elif machine.inspection_frequency == "monthly":
                return Response(self.get_monthly_schedule(machine, today, month_start, month_end))
            else:
                return Response({"message": "Unsupported inspection frequency"}, status=status.HTTP_400_BAD_REQUEST)
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


    def get_monthly_schedule(self, machine, today, start_date, end_date):
    # You can customize this to use any fixed day, e.g., 1st, 15th, or last day of the month.
        due_date = end_date  # 1st of the month

        if due_date > today:
            status_label = "scheduled"
        elif InspectionReport.objects.filter(machine=machine, due_date=due_date).exists():
            status_label = "completed"
        elif PendingInspection.objects.filter(machine=machine, date_due=due_date, resolved=False).exists():
            status_label = "pending"
        else:
            status_label = "missed" if due_date < today else "scheduled"

        return [{
            "schedule": due_date,
            "status": status_label
        }]


# class AddInspectionReportView(APIView):
#     permission_classes = [IsAuthenticated]
#     def post(self, request):  
#         serializer = AddInspectionReportSerializer(data=request.data, context={"request": request})  
#         if serializer.is_valid():  
#             data = serializer.validated_data  
#             machine = data['machine']  
#             worker = request.user  

#             # Update status to normal by default unless escalated  
#             machine.status = "abnormal" if data.get("is_escalated") else "normal"  
#             machine.save()

#             # Resolve PendingInspection if exists  
#             pending = PendingInspection.objects.filter(machine=machine, date_due=now().date(), resolved=False).first()  
#             if pending:  
#                 pending.resolved = True  
#                 pending.save()

#             # Create inspection report  
#             report = InspectionReport.objects.create(  
#                 machine=machine,  
#                 worker=worker,  
#                 look=data['look'],  
#                 feel=data['feel'],  
#                 sound=data['sound'],  
#                 is_escalated=data.get('is_escalated', False),  
#                 due_date=get_machine_due_date(machine),  
#             )

#             # Create Escalation if needed  
#             if data.get('is_escalated'):  
#                 Escalation.objects.create(  
#                     machine=machine,  
#                     worker=worker,  
#                     engineer=machine.engineer,  
#                     report=report,  
#                     comment=data.get('comment', ''),  
#                 )

#             return Response({"message": "Inspection submitted successfully"}, status=status.HTTP_201_CREATED)  
#         return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# ================= inspection ===============
# class InspectionReportView(APIView):

#     def post(self, request):
#         try:
#             serializer = InspectionReportSerializer(data=request.data)
#             if serializer.is_valid():
#                 serializer.save()
#                 return Response(serializer.data, status=status.HTTP_201_CREATED)
#             return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
#         except Exception as e:
#             return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
class InspectionReportView(APIView):

    def post(self, request):
        try:
            user = request.user  # Assuming authenticated worker
            machine_id = request.data.get('machine')
            due_date = request.data.get('due_date')
            print('## user ==> ', user, user.id)
            print('## machine_id ==> ', machine_id)
            print('## due_date ==> ', due_date)

            try:
                due_date = datetime.strptime(due_date, '%Y-%m-%d').date()
            except (ValueError, TypeError):
                return Response({"error": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)


            if due_date > date.today():
                return Response({"error": "Due date cannot be in the future."}, status=status.HTTP_400_BAD_REQUEST)

            

            if not machine_id or not due_date:
                return Response({"error": "Machine ID  and due_date is required."}, status=status.HTTP_400_BAD_REQUEST)

            # Validate machine exists
            try:
                machine = Machine.objects.get(id=machine_id)
            except Machine.DoesNotExist:
                return Response({"error": "Machine not found."}, status=status.HTTP_404_NOT_FOUND)
            if machine.worker != user:
                return Response({"error": "You are not assigned to this machine."}, status=status.HTTP_403_FORBIDDEN)


            already_reported = InspectionReport.objects.filter(
                machine=machine,
                worker=user,
                due_date=due_date
            ).exists()

            if already_reported:
                return Response({"message": "Inspection already done."}, status=status.HTTP_400_BAD_REQUEST)


            # Fetch and validate due date from PendingInspection
            # try:
            #     pending_inspection = PendingInspection.objects.get(machine=machine, resolved=False)
            # except PendingInspection.DoesNotExist:
            #     return Response({"error": "No pending inspection found for this machine."}, status=status.HTTP_400_BAD_REQUEST)

            # Create inspection report with automatic fields
            look = request.data.get("look", True )
            feel = request.data.get("feel",True )
            sound = request.data.get("sound", True)
            print('look and feel and sound ==>', not (look and feel and sound))


            data = {
                "machine": machine.id,
                "worker": user.id,
                "due_date": due_date,
                "look": look,
                "feel": feel,
                "sound": sound,

                "look_comment": request.data.get("look_comment"),
                "feel_comment": request.data.get("feel_comment"),
                "sound_comment": request.data.get("sound_comment"),


                
                "is_escalated": not (look and feel and sound)

            }
            print('# data ==>', data)

            serializer = InspectionReportSerializer(data=data)
            if serializer.is_valid():
                serializer.save()

                try:
                    pending = PendingInspection.objects.get(machine=machine, date_due=due_date, resolved=False)
                    pending.resolved = True
                    pending.save()
                except PendingInspection.DoesNotExist:
                    pass  # Optional: return a warning or silently ignore


                # Optionally, mark pending inspection as resolved automatically
                # pending_inspection.resolved = True
                # pending_inspection.save()

                return Response(serializer.data, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        except Exception as e:
            print(e)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)




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
        # # Get the start (Monday) and end (Sunday) of the current week
        # start_of_week = today - timedelta(days=today.weekday())  # Monday
        # end_of_week = start_of_week + timedelta(days=5)          # Sunday

        # inspection_done_this_week = InspectionReport.objects.filter(
        #     machine=machine,
        #     timestamp__date__gte=start_of_week,
        #     timestamp__date__lte=today
        # ).exists()

        # if inspection_done_this_week:
        #     return False  # Already inspected this week

        # if today != end_of_week:
        #     return False  # Not due yet

        # return True  # Due today (last day of the week, no inspection yet)

        # Define the current week (Monday to Saturday)
        start_of_week = today - timedelta(days=today.weekday())  # Monday
        end_of_week = start_of_week + timedelta(days=5)  # Saturday

        # Check if inspection has already been done this week
        inspection_done_this_week = InspectionReport.objects.filter(
            machine=machine,
            timestamp__date__range=(start_of_week, today)
        ).exists()

        if inspection_done_this_week:
            return False  # Inspection already done

        if today == end_of_week:
            return True  # Due today (Saturday) and no inspection yet

        return False  # Not due yet

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


class CheckPendingAPIView(APIView):
    # Optional: add authentication or a secret token check
    permission_classes = [IsAuthenticated, IsAdmin]  # Optional

    def post(self, request):
        days = request.data.get("days")
        start = request.data.get("start")
        end = request.data.get("end")

        # Capture stdout/stderr from management command
        out = StringIO()
        err = StringIO()

        cmd_options = {
            'simple': True,  # Disable color codes
        }
        if days:
            cmd_options["days"] = int(days)
        elif start and end:
            cmd_options["start"] = start
            cmd_options["end"] = end
        else:
            return Response({"error": "Please provide either 'days' or both 'start' and 'end'."}, status=400)

        try:
            call_command("check_pending", stdout=out, stderr=err, **cmd_options)
            return Response({
                "success": True,
                "output": out.getvalue()
            }, status=200)
        except Exception as e:
            return Response({
                "success": False,
                "error": str(e),
                "details": err.getvalue()
            }, status=500)


def remove_ansi(text):
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)
