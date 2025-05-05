from django.core.management.base import BaseCommand
from django.utils.timezone import now
from datetime import timedelta
from calendar import monthrange
from datetime import datetime

from dashboard.models import Machine, InspectionReport, PendingInspection


class Command(BaseCommand):
    help = "Check machines that were due for inspection on past days and mark as pending if missed."
    def add_arguments(self, parser):
        parser.add_argument(
            '--days',
            type=int,
            default=None,
            help='Number of past days to check (ignored if --start and --end are provided)'
        )
        parser.add_argument(
            '--start',
            type=str,
            help='Start date in YYYY-MM-DD format'
        )
        parser.add_argument(
            '--end',
            type=str,
            help='End date in YYYY-MM-DD format'
        )

    def handle(self, *args, **options):
        start = options.get('start')
        end = options.get('end')
        today = now().date()
        
        if start and end:
            try:
                start_date = datetime.strptime(start, '%Y-%m-%d').date()
                end_date = datetime.strptime(end, '%Y-%m-%d').date()
            except ValueError:
                self.stderr.write("❌ Invalid date format. Use YYYY-MM-DD.")
                return
            if start_date > end_date:
                self.stderr.write("❌ Start date must be before or equal to end date.")
                return
        elif options.get('days') is not None:
            days = options['days']
            end_date = today - timedelta(days=1)
            start_date = today - timedelta(days=days)
        else:
            self.stderr.write("❌ Provide either --days or both --start and --end.")
            return

        total_new_pendings = 0
        machines = Machine.objects.all()

        for delta in range((end_date - start_date).days + 1):
            check_date = start_date + timedelta(days=delta)
            new_pendings = 0
            for machine in machines:
                if not self.was_due_on(machine, check_date):
                    continue

                inspected = InspectionReport.objects.filter(
                    machine=machine,
                    due_date=check_date
                ).exists()

                if not inspected:
                    already_pending = PendingInspection.objects.filter(
                        machine=machine,
                        date_due=check_date,
                        resolved=False
                    ).exists()

                    if not already_pending:
                        PendingInspection.objects.create(
                            machine=machine,
                            date_due=check_date,
                        )
                        new_pendings += 1

            total_new_pendings += new_pendings
            self.stdout.write(self.style.SUCCESS(
                f"✅ {new_pendings} new pending inspections recorded for {check_date.strftime('%a - %d - %B - %Y')}."
            ))

        self.stdout.write(self.style.SUCCESS(
            f"🎯 Total new pending inspections recorded from {start_date.strftime('%a - %d - %B - %Y')} to {end_date.strftime('%a - %d - %B - %Y')}: {total_new_pendings}."
        ))

    def was_due_on(self, machine, target_date):
        freq = machine.inspection_frequency

        if freq == 'daily':
            return True

        elif freq == 'weekly':
            return target_date.weekday() == 5  # Saturday

        elif freq == 'monthly':
            last_day = monthrange(target_date.year, target_date.month)[1]
            return target_date.day == last_day

        return False
# from django.core.management.base import BaseCommand
# from django.utils.timezone import now
# from datetime import timedelta, date
# from calendar import monthrange

# from dashboard.models import Machine, InspectionReport, PendingInspection


# class Command(BaseCommand):
#     help = "Check machines that were due for inspection yesterday and mark as pending if missed."

#     def handle(self, *args, **kwargs):
#         today = now().date()
#         # yesterday = today 
#         yesterday = today - timedelta(days=1)

#         # yesterday = today 
#         print (f"date: {yesterday}")
#         machines = Machine.objects.all()
#         new_pendings = 0
#         print(f'# total machines ==> {machines}')
#         for machine in machines:
#             due_yesterday = self.was_due_on(machine, yesterday)
#             if not due_yesterday:
#                 continue

#             inspected = InspectionReport.objects.filter(
#                 machine=machine,
#                 due_date=yesterday
#             ).exists()

#             if not inspected:
#                 already_pending = PendingInspection.objects.filter(
#                     machine=machine,
#                     date_due=yesterday,
#                         resolved=False


#                 ).exists()

#                 if not already_pending:
#                     PendingInspection.objects.create(
#                         machine=machine,
#                         date_due=yesterday,
#                     )
#                     new_pendings += 1

#         self.stdout.write(self.style.SUCCESS(
#             f"✅ Done. {new_pendings} new pending inspections recorded for {yesterday}."
#         ))

#     def was_due_on(self, machine, target_date):
#         freq = machine.inspection_frequency

#         if freq == 'daily':
#             return True

#         elif freq == 'weekly': 
#             return target_date.weekday() == 5

#         elif freq == 'monthly':
#             last_day = monthrange(target_date.year, target_date.month)[1]
#             return target_date.day == last_day

#         return False
