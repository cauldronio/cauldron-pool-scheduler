import datetime
import logging
import importlib

from django.db import models
from django.conf import settings
from django.utils.timezone import now

logger = logging.getLogger(__name__)


class SchedulerManager(models.Manager):
    def create_intentions(self, worker):
        """Create all ready scheduled intentions"""

        # Update intentions to the worker name
        self.filter(worker=None)\
            .exclude(scheduled_at=None)\
            .filter(scheduled_at__lt=now())\
            .update(worker=worker)
        # Get all the intentions for this worker
        intentions = self.filter(worker=worker)
        try:
            for intention in intentions:
                intention.create_intention()
        except Exception as e:
            # Too broad exception to avoid stopping scheduled intentions
            logger.exception(f'Error creating the scheduled intentions.')
        finally:
            intentions.update(worker=None)


class ScheduledIntention(models.Model):
    """
    This model represents an intention that is scheduled
    to run at a specific time with some arguments.

    A worker will create a new intention using the 'intention_class'
    and its arguments (kwargs) from this model.

    Some intentions depends on others, so you don't want to run
    them at a specific time. In that case, you don't need to define
    'scheduled_at' and instead use 'depends_on'.
    When an 'scheduled_at' intention is created, it will create the
    dependent intentions (children).
    You should not define 'scheduled_at' and 'depends_on' in the same
    scheduled intention, unless necessary.

    You can define after how many hours the intention should be executed,
    by default is 24 hours. 0 or None for not repeating. This parameter is
    ignored when `scheduled_at` is not defined.
    """

    # Reference to the intention to be created (ex. 'cauldron_apps.poolsched_github.models.IGHRaw')
    intention_class = models.CharField(max_length=250, blank=False)
    # Keyword arguments for the intention when it is created
    kwargs = models.JSONField()
    # User that created this scheduled intention
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    # Time at what this intention will be created
    scheduled_at = models.DateTimeField(default=None, null=True)
    # Previous intention after which this intention will be executed
    depends_on = models.ForeignKey('self', on_delete=models.CASCADE, related_name='children_intentions', null=True, default=None)
    # Repeat every N hours (0 or None for not repeating)
    repeat = models.IntegerField(default=24, null=True)
    # Worker running this schedule (to avoid having race conditions)
    worker = models.ForeignKey('poolsched.Worker', null=True, default=None, on_delete=models.SET_NULL)

    objects = SchedulerManager()

    def create_intention(self, parent_intention=None):
        """
        Initialize a new intention with the defined arguments.

        If is any other intention depends on this one, create it.

        If this is a repeating intention, reschedule it again.
        """
        logger.info(f'Creating intention {self.intention_class}({self.kwargs})')

        module_name, class_name = self.intention_class.rsplit('.', 1)
        module = importlib.import_module(module_name)
        iclass = getattr(module, class_name)
        intention, _ = iclass.objects.get_or_create(**self.kwargs)
        intention.previous.add(parent_intention)

        children = self.children_intentions.all()
        for child in children:
            child.create_intention(parent_intention=intention)

        if self.scheduled_at and self.repeat:
            self.scheduled_at += datetime.timedelta(hours=self.repeat)
            self.save()
