from logging import getLogger

from django.db import models, IntegrityError, transaction
from django.utils.timezone import now

from ..intentions import Intention
from ..jobs import Job
from ..users import User

logger = getLogger(__name__)

TABLE_PREFIX = 'poolsched_gh'

class Instance(models.Model):
    """Instance of GitHub, or GitHub Enterprise"""

    name = models.CharField(max_length=40, unique=True)
    endpoint = models.CharField(max_length=200)

    class Meta:
        db_table = TABLE_PREFIX + 'instance'


class Repo(models.Model):
    """GitHub repository"""

    # GitHub owner
    owner = models.CharField(max_length=40)
    # GitHub repo
    repo = models.CharField(max_length=40)
    # GitHub instance
    instance = models.ForeignKey(
        Instance, on_delete=models.SET_NULL,
        default=None, null=True, blank=True)
    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        # The combination (onwer, repo, instance) should be unique
        unique_together = ('owner', 'repo', 'instance')

class Token(models.Model):
    """GitHub token"""

    # Token string
    token = models.CharField(max_length=40)
    # Rate limit remaining, last time it was checked
    #rate = models.IntegerField(default=0)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    # Onwer of the token
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        related_name='ghtokens',
        related_query_name='ghtoken')
    # Jobs using the token
    jobs = models.ManyToManyField(
        Job,
        related_name='ghtokens',
        related_query_name='ghtoken')

    class Meta:
        db_table = TABLE_PREFIX + 'token'


class IRawManager(models.Manager):
    """Model manager for IGitHubRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IRaw intentions for a user

        A intention is selectable if:
        * its user has a usable token
        * it's status is ready
        * no job is still associated with it
        * (future) in fact, either its user has a usable token,
          or there is other (public) token avilable
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IRaw intentions
        """

        intentions = self.filter(status=Intention.Status.READY,
                                 user=user,
                                 job=None) \
            .filter(user__ghtoken__reset__lt=now())
        return intentions.all()[:max]


class IRaw(Intention):
    """Intention for producing raw indexes for GitHub repos"""

    # Repo to analyze
    repo = models.ForeignKey(Repo, on_delete=models.PROTECT,
                             default=None, null=True, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
    objects = IRawManager()

    class TokenExhaustedException(Job.StopException):
        """Exception to raise if the GitHub token is exhausted

        Will be raised if the token is exhausted while the data
        for the repo is being retrieved. In this case, likely the
        retrieval was not finished."""

        def __init__(self, token, message="Token exhausted"):
            """
            Job could not finish because token was exhausted.

            :param reset: date when the token will be reset
            """

            self.message = message
            self.token = token

        def __str__(self):
            return self.message

    # Maximum number of jobs using a token concurrently
    MAX_JOBS_TOKEN = 10

    @classmethod
    def next_job(cls):
        """Find the next job of this model.

        To be selected, a job should be waiting, and have a token ready.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        jobs = Job.objects.filter(status=Job.Status.WAITING) \
            .filter(ghtoken__reset__lt=now())
        job = jobs.first()
        return job


    def create_previous(self):
        "Create all needed previous intentions (no previous intention needed)"
        return []

    def running_job(self):
        """Find a job that would satisfy this intention

        If a not done job is found, which would satisfy intention,
        the intention is assigned to that job, which is returned.
        The user token is assigned to it, too.

        :return:          Job object, if it was found, or None, if not
        """

        candidates = self.repo.iraw_set.exclude(job__isnull=False)
        try:
            # Find intention with job for the sme repo, assign job to self
            self.job = candidates[0].job
        except IndexError:
            # No intention with a job for the same repo found
            return None
        self.save()
        # Get tokens for the user, and assign them to job
        tokens = Token.objects.filter(user=self.user)
        for token in tokens:
            token.jobs.add(self.job)
        return self.job

    def create_job(self, worker):
        """Create a new job for this intention, add it

        Adds the job to the intention, too.
        A IRaW intention cannot run if there are too many jobs
        using available tokens.

        :param worker: Worker willing to create the job.
        :returns:      Job created, or None
        """

        # Check for available tokens (with not too many jobs)
        try:
            with transaction.atomic():
                tokens = self.user.ghtokens.all()
                for token in tokens:
                    if token.jobs.count() < self.MAX_JOBS_TOKEN:
                        # Available token found, create job if needed
                        if self.job is None:
                            self.job = Job.objects.create(worker=worker)
                        token.jobs.add(self.job)
        except IntegrityError:
            return None
        return self.job

    def run(self, job):
        """Run the code to fulfill this intention

        :param resources: Resource objects useful (QuerySet)
        """

        repo = self.repo
        token = job.ghtokens.filter(reset__lt=now()).first()
        logger.info(f"Running GitHubRaw intention: {repo.owner}/{repo.repo}, token: {token}" )
        # raise TokenExhaustedException(token=token) if token exhausted


class IEnriched(Intention):

    repo = models.ForeignKey(Repo, on_delete=models.PROTECT,
                             default=None, null=True, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'

    def create_previous(self):
        "Create all needed previous intentions"

        raw_intention = IRaw.objects.create(repo=self.repo,
                                            user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]
