from logging import getLogger

from django.db import models

from . import jobs

logger = getLogger(__name__)


class IntentionManager(models.Manager):

    def data(self):
        return [intention.data() for intention in self]


class Intention(models.Model):
    """Intention: Somethig you want to achieve

    Intentions are states you want to achieve, such as "raw index collected",
    or "eniriched index built".
    """

    class Status(models.TextChoices):
        WAITING = 'WA', "Waiting" # Waiting for previous intentions
        READY = 'RE', "Ready" # All previous intentions done
        WORKING = 'WO', "Working" # Some job working for this intention
        DONE = 'DO', "Done" # This intention is done

    # Will point to a job when a job is allocated. Several intentions
    # may point to the same job
    job = models.ForeignKey(jobs.Job, on_delete=models.SET_NULL,
                            default=None, null=True, blank=True)
    # An intention os on behalf of some user
    user = models.ForeignKey('User', on_delete=models.PROTECT,
                             default=None, null=True, blank=True)
    # An intention may be in one of several states
    status = models.CharField(max_length=2, choices=Status.choices,
                              default=Status.WAITING)
    # Directly previous intentions (need to be done before this can be done)
    previous = models.ManyToManyField(
        'self',
        default=None, blank=True, symmetrical=False
    )

    class Meta:
        abstract = False
    objects = IntentionManager()

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
            except:
                # Some subfield is not an attribute, check the rest
                pass
            else:
                # Child attribute found
                return attr
        # Exception raised, or all subfield attributes are None
        logger.debug(f"Casting as intention (error?): {self}, {self.__class__}")
        return self
