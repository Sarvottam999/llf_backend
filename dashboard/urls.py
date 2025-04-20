from django.urls import path
from .views import MachineCreateView, EngineerCreatedMachinesView, MachineByUser, MachineDetailView, AssignWorkerToMachineView, DashboardSummaryViewSet, DueMachinesView, AddInspectionReportView, MachineScheduleView, EngineerMachineAnalyticsView

urlpatterns = [
    # path('machines/', MachineListView.as_view(), name='machine-list'),  # Engineers & Admins can view all machines
    
    path('machines/create/', MachineCreateView.as_view(), name='machine-create'),  # Engineers can create machines
    path('machines/', MachineByUser.as_view(), name='worker-machines'),  # Workers can view assigned machines
    path('machines/<int:id>/', MachineDetailView.as_view(), name='worker-machines'),  # get machine by worker 
    path('machines/assign-worker/', AssignWorkerToMachineView.as_view(), name='assign-worker'),
    path('machines/engineer/', EngineerCreatedMachinesView.as_view(), name='engineer-machines'), # get machine by engineer
    path('machines/<int:machine_id>/schedule/', MachineScheduleView.as_view(), name='machine-schedule'),

    # inspectio
    path('dashboard-summary/', DashboardSummaryViewSet.as_view(), name='worker-dashboard-summary'), # get machine by engineer
    path('engineer/machine-analytics/', EngineerMachineAnalyticsView.as_view(), name='engineer-machine-analytics'),
    path('worker/due-machine-list/', DueMachinesView.as_view(), name='engineer-dashboard-summary'), # get machine by engineer
    path('worker/add-inspection/', AddInspectionReportView.as_view(), name='add-inspection'), # get machine by engineer


]
