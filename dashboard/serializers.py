from rest_framework import serializers
from .models import Machine
from django.utils.timezone import now


 
from .models import Machine, InspectionReport 
from rest_framework.serializers import ModelSerializer, CharField, BooleanField, ValidationError


class MachineSerializer(serializers.ModelSerializer):
    engineer_name = serializers.CharField(source="engineer.username", read_only=True)
    worker_name = serializers.CharField(source="worker.username", read_only=True)

    class Meta:
        model = Machine
        fields = '__all__'


class MachineWithDueDateSerializer(serializers.ModelSerializer):
    engineer_name = serializers.CharField(source="engineer.username", read_only=True)
    worker_name = serializers.CharField(source="worker.username", read_only=True)
    due_date = serializers.SerializerMethodField()

    class Meta:
        model = Machine
        fields = '__all__'
        extra_fields = ['engineer_name', 'worker_name', 'due_date']

    def get_due_date(self, obj):
        # This reads from context if passed, else returns today
        return self.context.get("due_date", now().date())


class AddInspectionReportSerializer(ModelSerializer):
    comment = CharField(required=False, allow_blank=True)
    is_escalated = BooleanField(required=False)

    class Meta:  
        model = InspectionReport  
        fields = ['machine', 'look', 'feel', 'sound', 'is_escalated', 'comment']  # custom 'comment'

    def validate(self, attrs):  
        user = self.context['request'].user  
        machine = attrs.get("machine")

        if machine.worker != user:  
            raise ValidationError("You are not assigned to this machine.")  
        return attrs


 