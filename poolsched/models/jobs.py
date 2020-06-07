from django.db import models
from django.utils.timezone import now

from . import workers


class Job(models.Model):

    class Status(models.TextChoices):
        WAITING = 'WA', "Waiting"
        WORKING = 'WO', "Working"
        DONE = 'DO', "Done"

    class StopException(Exception):
        """Raised when the job had to stop before completion.

        Usually, subclassed by the different tasks, so that
        specific arguments informing of the stop can be used.
        """

    # When the job was created (usuallu, automatic field)
    created = models.DateTimeField(default=now, blank=True)
    # Worker dealng with this job, if any
    worker = models.ForeignKey(workers.Worker, on_delete=models.SET_NULL,
                               default=None, null=True, blank=True)
    # Status of the job
    status = models.CharField(max_length=2, choices=Status.choices,
                              default=Status.WAITING)


class ArchJob(models.Model):
    """Archived job"""

    # When the original job was created
    created = models.DateTimeField(blank=True)
    # When it was archived (entered this table)
    archived = models.DateTimeField(default=now, blank=True)
    # Worker archiving it
    worker = models.ForeignKey(workers.Worker, on_delete=models.SET_NULL,
                               default=None, null=True, blank=True)