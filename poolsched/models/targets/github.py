from logging import getLogger

from django.db import models, IntegrityError, transaction
from django.db.models import Q
from django.utils.timezone import now

from ..intentions import Intention
from ..jobs import Job
from ..users import User

logger = getLogger(__name__)

TABLE_PREFIX = 'poolsched_gh'


class GHInstance(models.Model):
    """GHInstance of GitHub, or GitHub Enterprise"""

    name = models.CharField(max_length=40, unique=True)
    endpoint = models.CharField(max_length=200)

    class Meta:
        db_table = TABLE_PREFIX + 'instance'


class GHRepo(models.Model):
    """GitHub repository"""

    # GitHub owner
    owner = models.CharField(max_length=40)
    # GitHub repo
    repo = models.CharField(max_length=100)
    # GitHub instance
    instance = models.ForeignKey(
        GHInstance, on_delete=models.SET_NULL,
        default=None, null=True, blank=True)
    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'
        # The combination (onwer, repo, instance) should be unique
        unique_together = ('owner', 'repo', 'instance')


class GHToken(models.Model):
    """GitHub token"""

    # Maximum number of jobs using a token concurrently
    MAX_JOBS_TOKEN = 3

    # GHToken string
    token = models.CharField(max_length=40)
    # Rate limit remaining, last time it was checked
    # rate = models.IntegerField(default=0)
    # Rate limit reset, last time it was checked
    reset = models.DateTimeField(default=now)
    # Owner of the token
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
        """Return a list of selectable IGHRaw intentions for a user

        A intention is selectable if:
        * its user has a usable token
        * no job is still associated with it
        * (future) in fact, either its user has a usable token,
          or there is other (public) token avilable
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGHRaw intentions
        """

        intentions = self.filter(user=user,
                                 job=None) \
            .filter(user__ghtoken__reset__lt=now())
        return intentions.all()[:max]


class IGHRaw(Intention):
    """Intention for producing raw indexes for GitHub repos"""

    # GHRepo to analyze
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
    objects = IRawManager()

    class TokenExhaustedException(Job.StopException):
        """Exception to raise if the GitHub token is exhausted

        Will be raised if the token is exhausted while the data
        for the repo is being retrieved. In this case, likely the
        retrieval was not finished."""

        def __init__(self, token, message="GHToken exhausted"):
            """
            Job could not finish because token was exhausted.

            :param reset: date when the token will be reset
            """

            self.message = message
            self.token = token

        def __str__(self):
            return self.message

    def __str__(self):
        return f'Repo({self.repo})|User({self.user})|Prev({self.previous})|Job({self.job}))'

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting, and have a token ready.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        job = None
        intention = IGHRaw.objects\
            .select_related('job').select_for_update()\
            .exclude(job=None).filter(job__worker=None).filter(job__ghtoken__reset__lt=now())\
            .first()
        if intention:
            job = intention.job
            job.worker = worker
            job.save()
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

        candidates = self.repo.ighraw_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
        except IndexError:
            # No intention with a job for the same repo found
            return None
        self.save()
        # Get tokens for the user, and assign them to job
        tokens = GHToken.objects.filter(user=self.user)
        token_included = False
        for token in tokens:
            if token.jobs.count() < token.MAX_JOBS_TOKEN:
                token_included = True
                token.jobs.add(self.job)
        if token_included:
            return self.job
        else:
            return None

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
                tokens = self.user.ghtokens.all()
                for token in tokens:
                    if token.jobs.count() < token.MAX_JOBS_TOKEN:
                        # Available token found, create job if needed
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
        token = job.ghtokens.filter(reset__lt=now()).first()
        logger.info(f"Running GitHubRaw intention: {repo.owner}/{repo.repo}, token: {token}")
        # raise TokenExhaustedException(token=token) if token exhausted

    def archive(self):
        """Archive and remove the current intention"""
        IGHRawArchived.objects.create(user=self.user,
                                      repo=self.repo,
                                      created=self.created)
        self.delete()


class IEnrichedManager(models.Manager):
    """Model manager for IGHEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IGHEnrich intentions for a user

        A intention is selectable if:
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGHRaw intentions
        """

        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IGHEnrich(Intention):
    """Intention for producing enriched indexes for GitHub repos"""
    # GHRepo to analyze
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'
    objects = IEnrichedManager()

    def __str__(self):
        return f'Repo({self.repo})|User({self.user})|Prev({self.previous})|Job({self.job})'


    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        job = None
        intention = IGHEnrich.objects\
            .select_related('job').select_for_update()\
            .exclude(job=None).filter(job__worker=None)\
            .first()
        if intention:
            job = intention.job
            job.worker = worker
            job.save()
        return job

    def create_previous(self):
        """Create all needed previous intentions"""
        raw_intention, _ = IGHRaw.objects.get_or_create(repo=self.repo,
                                                        user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """

        candidates = self.repo.ighenrich_set.filter(job__isnull=False)
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

        logger.info(f"Running GitHubEnrich intention: {self.repo.owner}/{self.repo.repo}")

    def archive(self):
        """Archive and remove the current intention"""
        IGHEnrichArchived.objects.create(user=self.user,
                                         repo=self.repo,
                                         created=self.created)
        self.delete()


class IGHRawArchived(models.Model):
    """Archived GitHub Raw intention"""
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)
    user = models.ForeignKey('User', on_delete=models.PROTECT,
                             default=None, null=True, blank=True)
    created = models.DateTimeField()
    completed = models.DateTimeField(auto_now_add=True)


class IGHEnrichArchived(models.Model):
    """Archived GitHub Enrich intention"""
    repo = models.ForeignKey(GHRepo, on_delete=models.PROTECT)
    user = models.ForeignKey('User', on_delete=models.PROTECT,
                             default=None, null=True, blank=True)
    created = models.DateTimeField()
    completed = models.DateTimeField(auto_now_add=True)
