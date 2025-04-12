from django.urls import path
from .views import MachineCreateView, EngineerCreatedMachinesView, MachineByUser

urlpatterns = [
    # path('machines/', MachineListView.as_view(), name='machine-list'),  # Engineers & Admins can view all machines
    
    path('machines/create/', MachineCreateView.as_view(), name='machine-create'),  # Engineers can create machines
    path('machines/', MachineByUser.as_view(), name='worker-machines'),  # Workers can view assigned machines
    # path('machines/worker/<int:worker_id>/', WorkerAssignedMachinesView.as_view(), name='worker-machines'),  # get machine by worker 
    
    
    path('machines/engineer/', EngineerCreatedMachinesView.as_view(), name='engineer-machines'), # get machine by engineer

]
