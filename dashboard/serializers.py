from rest_framework import serializers
from .models import Machine

class MachineSerializer(serializers.ModelSerializer):
    engineer_name = serializers.CharField(source="engineer.username", read_only=True)
    worker_name = serializers.CharField(source="worker.username", read_only=True)

    class Meta:
        model = Machine
        fields = '__all__'
