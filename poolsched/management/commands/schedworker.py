from django.core.management.base import BaseCommand
from poolsched import schedworker


class Command(BaseCommand):
    help = 'Run the scheduler worker'

    def handle(self, *args, **options):
        schedworker.SchedWorker(run=True)
