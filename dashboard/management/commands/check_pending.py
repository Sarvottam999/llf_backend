from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta, date
from calendar import monthrange

from dashboard.models import Machine, InspectionReport, PendingInspection


class Command(BaseCommand):
    help = "Check machines that were due for inspection yesterday and mark as pending if missed."

    def handle(self, *args, **kwargs):
        today = now().date()
        yesterday = today + timedelta(days=1)
        # yesterday = today 
        print (f"date: {yesterday}")
        machines = Machine.objects.all()
        new_pendings = 0

        for machine in machines:
            due_yesterday = self.was_due_on(machine, yesterday)
            if not due_yesterday:
                continue

            inspected = InspectionReport.objects.filter(
                machine=machine,
                due_date=yesterday
            ).exists()

            if not inspected:
                already_pending = PendingInspection.objects.filter(
                    machine=machine,
                    date_due=yesterday
                ).exists()

                if not already_pending:
                    PendingInspection.objects.create(
                        machine=machine,
                        date_due=yesterday
                    )
                    new_pendings += 1

        self.stdout.write(self.style.SUCCESS(
            f"✅ Done. {new_pendings} new pending inspections recorded for {yesterday}."
        ))

    def was_due_on(self, machine, target_date):
        freq = machine.inspection_frequency

        if freq == 'daily':
            return True

        elif freq == 'weekly':
            # Was it Sunday (end of the week)?
            end_of_week = target_date - timedelta(days=target_date.weekday() - 5) if target_date.weekday() < 6 else target_date
            return target_date == end_of_week

        elif freq == 'monthly':
            last_day = monthrange(target_date.year, target_date.month)[1]
            return target_date.day == last_day

        return False
