from logging import getLogger

from django.db import models
from django.conf import settings

from . import jobs

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

    class Meta:
        abstract = True
