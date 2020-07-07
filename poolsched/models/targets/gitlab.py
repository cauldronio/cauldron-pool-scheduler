from logging import getLogger

from django.db import models, IntegrityError, transaction
from django.utils.timezone import now

from ..intentions import Intention
from ..jobs import Job
from ..users import User

logger = getLogger(__name__)

TABLE_PREFIX = 'poolsched_gl'


class GLInstance(models.Model):
    """GLInstance of GitLab, or GitLab Enterprise"""

    name = models.CharField(max_length=40, unique=True)
    endpoint = models.CharField(max_length=200)

    class Meta:
        db_table = TABLE_PREFIX + 'instance'


class GLRepo(models.Model):
    """GitLab repository"""

    # GitLab owner
    owner = models.CharField(max_length=40)
    # GitLab repo
    repo = models.CharField(max_length=100)
    # GitLab instance
    instance = models.ForeignKey(
        GLInstance, on_delete=models.SET_NULL,
        default=None, null=True, blank=True)
    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        # The combination (onwer, repo, instance) should be unique
        unique_together = ('owner', 'repo', 'instance')


class GLToken(models.Model):
    """GitLab token"""

    # Maximum number of jobs using a token concurrently
    MAX_JOBS_TOKEN = 3

    # GLToken string
    token = models.CharField(max_length=40)
    # Rate limit remaining, last time it was checked
    # rate = models.IntegerField(default=0)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    # Owner of the token
    user = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        default=None, null=True, blank=True,
        related_name='gltokens',
        related_query_name='gltoken')
    # Jobs using the token
    jobs = models.ManyToManyField(
        Job,
        related_name='gltokens',
        related_query_name='gltoken')

    class Meta:
        db_table = TABLE_PREFIX + 'token'


class IRawManager(models.Manager):
    """Model manager for IGitLabRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable GLIRaw intentions for a user

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
        :returns:    list of GLIRaw intentions
        """

        intentions = self.filter(status=Intention.Status.READY,
                                 user=user,
                                 job=None) \
            .filter(user__gltoken__reset__lt=now())
        return intentions.all()[:max]


class GLIRaw(Intention):
    """Intention for producing raw indexes for GitLab repos"""

    # GLRepo to analyze
    repo = models.ForeignKey(GLRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
    objects = IRawManager()

    class TokenExhaustedException(Job.StopException):
        """Exception to raise if the GitLab token is exhausted

        Will be raised if the token is exhausted while the data
        for the repo is being retrieved. In this case, likely the
        retrieval was not finished."""

        def __init__(self, token, message="GLToken exhausted"):
            """
            Job could not finish because token was exhausted.

            :param reset: date when the token will be reset
            """

            self.message = message
            self.token = token

        def __str__(self):
            return self.message

    @classmethod
    def next_job(cls):
        """Find the next job of this model.

        To be selected, a job should be waiting, and have a token ready.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        jobs = Job.objects.filter(status=Job.Status.WAITING) \
            .filter(gltoken__reset__lt=now())
        job = jobs.first()
        return job

    def create_previous(self):
        """Create all needed previous intentions (no previous intention needed)"""
        return []

    def running_job(self):
        """Find a job that would satisfy this intention

        If a not done job is found, which would satisfy intention,
        the intention is assigned to that job, which is returned.
        The user token is assigned to it, too.

        :return:          Job object, if it was found, or None, if not
        """

        candidates = self.repo.gliraw_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
        except IndexError:
            # No intention with a job for the same repo found
            return None
        self.save()
        # Get tokens for the user, and assign them to job
        tokens = GLToken.objects.filter(user=self.user)
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
        job = None
        try:
            with transaction.atomic():
                tokens = self.user.gltokens.all()
                for token in tokens:
                    if token.jobs.count() < token.MAX_JOBS_TOKEN:
                        # Available token found, create job if needed
                        # TODO: Race condition?
                        if self.job is None:
                            job = Job.objects.create(worker=worker)
                            self.job = job
                        token.jobs.add(self.job)
        except IntegrityError:
            return None
        return job

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        repo = self.repo
        token = job.gltokens.filter(reset__lt=now()).first()
        logger.info(f"Running GitLabRaw intention: {repo.owner}/{repo.repo}, token: {token}")
        # raise TokenExhaustedException(token=token) if token exhausted


class IEnrichedManager(models.Manager):
    """Model manager for GLIEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable GLIEnrich intentions for a user

        A intention is selectable if:
        * it's status is ready
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of GLIRaw intentions
        """

        intentions = self.filter(status=Intention.Status.READY,
                                 user=user,
                                 job=None)
        return intentions.all()[:max]


class GLIEnrich(Intention):
    """Intention for producing enriched indexes for GitLab repos"""

    # GLRepo to analyze
    repo = models.ForeignKey(GLRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'
    objects = IEnrichedManager()

    @classmethod
    def next_job(cls):
        """Find the next job of this model.

        To be selected, a job should be waiting.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        jobs = Job.objects.filter(status=Job.Status.WAITING)
        job = jobs.first()
        return job

    def create_previous(self):
        """Create all needed previous intentions"""

        raw_intention = GLIRaw.objects.create(repo=self.repo,
                                              user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """

        candidates = self.repo.glienrich_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
            self.save()
        except IndexError:
            # No intention with a job for the same repo found
            return None
        return self.job

    def create_job(self, worker):
        """Create a new job for this intention and assign it

        :param worker: Worker willing to create the job.
        :return: Job created or None
        """
        job = None
        try:
            with transaction.atomic():
                # TODO: Race condition?
                if self.job is None:
                    job = Job.objects.create(worker=worker)
                    self.job = job
        except IntegrityError:
            return None
        return job

    def run(self):
        """Run the code to fulfill this intention

        :return:
        """

        logger.info(f"Running GitLabEnrich intention: {self.repo.owner}/{self.repo.repo}")
