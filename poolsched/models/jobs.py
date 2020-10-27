import logging

from django.db import models, transaction, OperationalError, IntegrityError
from django.utils.timezone import now

from . import workers

logger = logging.getLogger(__name__)


class Log(models.Model):
    location = models.CharField(max_length=255, default=None, null=True)


class Job(models.Model):

    class StopException(Exception):
        """Raised when the job had to stop before completion.

        Usually, subclassed by the different tasks, so that
        specific arguments informing of the stop can be used.
        """

    # When the job was created (usually, automatic field)
    created = models.DateTimeField(default=now, blank=True)
    # Worker dealing with this job, if any
    worker = models.ForeignKey(workers.Worker, on_delete=models.SET_NULL,
                               default=None, null=True, blank=True)
    logs = models.ForeignKey(Log, on_delete=models.SET_NULL,
                             default=None, null=True)

    def queryset(self):
        """Function used to retrieve a queryset of this object
        for select_for_update()
        """
        return self.__class__.objects.filter(id=self.id)

    def assign_worker(self, worker):
        """Assign a new worker if the Job has no worker"""
        try:
            with transaction.atomic():
                job = self.queryset().select_for_update(nowait=True).get()
                if job.worker:
                    return None
                self.worker = worker
                self.save()
                return job
        except OperationalError:
            logger.warning(f'Job locked in next_job()')
            return None
        except IntegrityError:
            return None


class ArchJob(models.Model):
    """Archived job"""

    # When the original job was created
    created = models.DateTimeField(blank=True)
    # When it was archived (entered this table)
    archived = models.DateTimeField(default=now, blank=True)
    # Worker archiving it
    worker = models.ForeignKey(workers.Worker, on_delete=models.SET_NULL,
                               default=None, null=True, blank=True)
    logs = models.ForeignKey(Log, on_delete=models.SET_NULL,
                             default=None, null=True)
