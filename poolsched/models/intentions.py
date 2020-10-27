from logging import getLogger

from django.core.exceptions import ObjectDoesNotExist
from django.db import models, transaction, OperationalError, IntegrityError
from django.conf import settings

from . import jobs
from .jobs import Log
from .. import utils

logger = getLogger(__name__)


class Intention(models.Model):
    """Intention: Something you want to achieve

    Intentions are states you want to achieve, such as "raw index collected",
    or "enriched index built".
    """

    # Will point to a job when a job is allocated. Several intentions
    # may point to the same job
    job = models.ForeignKey(jobs.Job, on_delete=models.SET_NULL,
                            default=None, null=True, blank=True)
    # An intention is on behalf of some user
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                             default=None, null=True, blank=True)
    # Directly previous intentions (need to be done before this can be done)
    previous = models.ManyToManyField(
        'self',
        default=None, blank=True, symmetrical=False
    )

    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = False

    @property
    def process_name(self):
        raise NotImplementedError

    def _create_previous(self):
        """Create all needed previous intentions (no previous intention needed)

        Usually redefined by child classes, called by deep_previous()"""

        return []

    def deep_previous(self):
        """Create, recursively, all previous intentions"""

        intentions = self._create_previous()
        for intention in intentions:
            intentions += intention.create_deep()
        return intentions

    _subfields_list = None

    def queryset(self):
        return self.__class__.objects.filter(id=self.id)

    def create_job(self, worker):
        """Create a new job for this intention and worker
        Adds the job to the intention, too.

        If the worker didn't create the job, return None

        :param worker: Worker willing to create the job.
        :returns:      Job created by the worker, or None
        """
        try:
            with transaction.atomic():
                try:
                    intention = self.queryset().select_for_update(nowait=True).get()
                except OperationalError:
                    logger.warning('Intention locked in create_job()')
                    return None
                except ObjectDoesNotExist:
                    # The object could be already analyzed
                    return None

                # We have to check this now that we have the intention
                if intention.job:
                    # Job NOT created by the worker
                    return None

                job = jobs.Job.objects.create(worker=worker)
                self.job = job
                self.save()
        except IntegrityError:
            return None
        return job

    def update_job_worker(self, worker):
        """Update the job for this intention.
        Assign a new worker to the job of the intention if it doesn't exist.
        
        If the worker is assigned, return the Job, if not, return None
        
        :param worker: Worker willing to create the job.
        :returns:      Job assigned to the worker, or None
        """
        job = self.job
        job.assign_worker(worker)
        job.refresh_from_db()
        if job.worker == worker:
            return job
        return None

    @classmethod
    def _subfields(cls):
        """Get all fields corresponding to child classes

        We only run this the first time it is actually called"""

        if cls._subfields_list is None:
            cls._subfields_list = \
                [child._meta.model_name for child in cls.__subclasses__()]
        return cls._subfields_list

    def cast(self):
        """Cast to the children, if any

        Based on https://stackoverflow.com/a/22302235/2075265

        :return: children model, or self, if it is a child
        """
        for field in self._subfields():
            try:
                attr = getattr(self, field)
            except Exception:
                # Some subfield is not an attribute, check the rest
                pass
            else:
                # Child attribute found
                return attr
        # Exception raised, or all subfield attributes are None
        logger.debug(f"Casting as intention (error?): {self}, {self.__class__}")
        return self

    def _create_log_handler(self, job):
        job.logs = Log.objects.create(location=f"job-{job.id}.log")
        job.save()
        handler = utils.file_formatter(f"{settings.JOB_LOGS}/job-{job.id}.log")
        return handler


class ArchivedIntention(models.Model):
    """Abstract archived intention: Intention completed and not necessary anymore"""
    OK = 'OK'
    ERROR = 'ER'
    STATUS_CHOICES = [
        (OK, 'Success'),
        (ERROR, 'Error'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             default=None, null=True, blank=True)
    created = models.DateTimeField()
    completed = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=2, choices=STATUS_CHOICES, default=OK)
    arch_job = models.ForeignKey(jobs.ArchJob, on_delete=models.SET_NULL,
                            default=None, null=True, blank=True)

    @property
    def process_name(self):
        raise NotImplementedError
