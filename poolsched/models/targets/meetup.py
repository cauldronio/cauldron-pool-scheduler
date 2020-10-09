from logging import getLogger

from django.db import models, IntegrityError, transaction
from django.conf import settings
from django.utils.timezone import now

from ..intentions import Intention, ArchivedIntention
from ..jobs import Job

logger = getLogger(__name__)

TABLE_PREFIX = 'poolsched_meetup'


# TODO: Finish Meetup backend

class MeetupRepo(models.Model):
    """Meetup repository"""

    # Meetup group
    repo = models.CharField(max_length=100, unique=True)
    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'


class MeetupToken(models.Model):
    """Meetup token"""

    # Maximum number of jobs using a token concurrently
    MAX_JOBS_TOKEN = 1

    # MeetupToken string
    token = models.CharField(max_length=40)
    # Refresh token in case it is necessary in the future
    refresh_token = models.CharField(max_length=50)
    # Rate limit remaining, last time it was checked
    # rate = models.IntegerField(default=0)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    # Owner of the token
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        related_name='meetuptokens',
        related_query_name='meetuptoken')
    # Jobs using the token
    jobs = models.ManyToManyField(
        Job,
        related_name='meetuptokens',
        related_query_name='meetuptoken')

    class Meta:
        db_table = TABLE_PREFIX + 'token'

    @property
    def is_ready(self):
        return now() > self.reset

