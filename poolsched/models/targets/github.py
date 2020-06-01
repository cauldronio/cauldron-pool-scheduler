from logging import getLogger

from django.db import models, IntegrityError, transaction
from django.utils.timezone import now

from ..intentions import Intention
from ..jobs import Job
from ..users import User

logger = getLogger(__name__)

TABLE_PREFIX = 'poolsched_github_'

class Instance(models.Model):
    """Instance of GitHub, or GitHub Enterprise"""

    name = models.CharField(max_length=40, unique=True)
    endpoint = models.CharField(max_length=200)

    class Meta:
        db_table = TABLE_PREFIX + 'instance'


class Repo(models.Model):
    """GitHub repository"""

    owner = models.CharField(max_length=40)
    repo = models.CharField(max_length=40)
    instance = models.ForeignKey(
        Instance, on_delete=models.SET_NULL,
        default=None, null=True, blank=True)
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        unique_together = ('owner', 'repo', 'instance')

class Token(models.Model):
    """GitHub token"""

    # Token string
    token = models.CharField(max_length=40)
    # Rate limit remaining, last time it was checked
    #rate = models.IntegerField(default=0)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        default=None, null=True, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'token'


class IRawManager(models.Manager):
    """Model manager for IGitHubRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a query for getting selectable intentions

        A intention is selectable if:
        * its user has a usable token
        * it's status is ready
        * no job is still associated with it
        * (future) in fact, either its user has a usable token,
          or there is other (public) token avilable
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user_id: id for the user to check
        :returns:       queryset
        """

        intentions = self.filter(status=Intention.Status.READY,
                                 job=None) \
            .filter(user__token__reset__lt=now())
        return intentions.all()[:max]


class IRaw(Intention):

    repo = models.ForeignKey(Repo, on_delete=models.PROTECT,
                             default=None, null=True, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
    objects = IRawManager()

    class TokenExhaustedException(Job.StopException):

        def __init__(self, token, message="Token exhausted"):
            """
            Job could not finish because token was exhausted.

            :param reset: date when the token will be reset
            """

            self.message = message
            self.token = token

        def __str__(self):
            return self.message

    # Maximum number of jobs using a token
    MAX_JOBS_TOKEN = 10

    def create_previous(self):
        "Create all needed previous intentions (no previous intention needed)"
        return []

    def running_job(self):
        """Find a job that would satisfy this intention

        If a not done job is found, which would satisfy intention,
        the intention is assigned to that job, which is returned.
        The user token is assigned to it, too.

        :param intention: intention to be satisfied
        :return:          Job object, if it was found, or None, if not
        """

        jobs = Job.objects.filter(resources=self.repo) \
            .exclude(status=Job.Status.DONE).all()
        try:
            # Job found, assign it (also) to this intention
            self.job = jobs[0]
        except IndexError:
            # No job found
            return None
        self.save()
        # Get tokens for the user, and assign them to job
        tokens = self.user.resources.filter(rgithubtoken__isnull=False)
        for token in tokens:
            self.job.resources.add(token)
        return self.job

    def create_job(self, worker):
        """Create a new job for an intention (fails if cannot be run)

        A IGitHubRaW intention cannot run if there are too many jobs
        using the available tokens.

        :param worker: Worker willing to create the job.
        """

        job = None
        # Check if there are too many jobs for all tokens
        try:
            with transaction.atomic():
                tokens = self.user.resources.filter(rgithubtoken__isnull=False)
                for token in tokens:
                    if token.job_set.count() < self.MAX_JOBS_TOKEN:
                        job = Job.objects.create(worker=worker)
                        self.job = job
                        job.resources.add(token)
        except IntegrityError:
            return None
        if job is not None:
            job.resources.add(self.repo)
            self.job = job
        return job

    def run(self, resources):
        """Run the code to fulfill this intention

        :param resources: Resource objects useful (QuerySet)
        """

        repo = self.repo
        token = resources.filter(rgithubtoken__isnull = False) \
            .first().rgithubtoken
        logger.info(f"Running GitHubRaw intention: {repo.owner}/{repo.repo}, token: {token}" )
        # raise TokenExhaustedException(token=token) if token exhausted


class IEnriched(Intention):

    repo = models.ForeignKey(Repo, on_delete=models.PROTECT,
                             default=None, null=True, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'

    def create_previous(self):
        "Create all needed previous intentions"

        raw_intention = IGitHubRaw.objects.create(repo=self.repo,
                                                  user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]
