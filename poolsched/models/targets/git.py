from logging import getLogger

from django.db import models, IntegrityError, transaction
from django.utils.timezone import now

from ..intentions import Intention
from ..jobs import Job

logger = getLogger(__name__)

TABLE_PREFIX = 'poolsched_git'


class GitRepo(models.Model):
    """Git repository"""

    url = models.CharField(max_length=256, unique=True)

    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'


class IRawManager(models.Manager):
    """Model manager for IGitRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable GitIRaw intentions for a user

        A intention is selectable if:
        * it's status is ready
        * no job is still associated with it
        It's not important if there is other job for the same url,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of GitIRaw intentions
        """

        intentions = self.filter(status=Intention.Status.READY,
                                 user=user,
                                 job=None)
        return intentions.all()[:max]


class GitIRaw(Intention):
    """Intention for producing raw indexes for Git repos"""

    # GitRepo to analyze
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
    objects = IRawManager()

    @classmethod
    def next_job(cls):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """

        jobs = Job.objects.filter(status=Job.Status.WAITING)
        job = jobs.first()
        return job

    def create_previous(self):
        """Create all needed previous intentions (no previous intention needed)"""
        return []

    def running_job(self):
        """Find a job that would satisfy this intention

        If a not done job is found, which would satisfy intention,
        the intention is assigned to that job, which is returned.

        :return:          Job object, if it was found, or None, if not
        """

        candidates = self.repo.gitiraw_set.filter(job__isnull=False)
        try:
            # Find intention with job for the same repo, assign job to self
            self.job = candidates[0].job
        except IndexError:
            # No intention with a job for the same repo found
            return None
        self.save()
        return self.job

    def create_job(self, worker):
        """Create a new job for this intention, add it

        Adds the job to the intention, too.

        :param worker: Worker willing to create the job.
        :returns:      Job created, or None
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

    def run(self, job):
        """Run the code to fulfill this intention

        :param job: job to be run
        """

        repo = self.repo
        logger.info(f"Running GitRaw intention: {repo.url}")


class IEnrichedManager(models.Manager):
    """Model manager for GitIEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable GitIEnrich intentions for a user

        A intention is selectable if:
        * it's status is ready
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of GitIRaw intentions
        """

        intentions = self.filter(status=Intention.Status.READY,
                                 user=user,
                                 job=None)
        return intentions.all()[:max]


class GitIEnrich(Intention):
    """Intention for producing enriched indexes for Git repos"""

    # GitRepo to analyze
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

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

        raw_intention = GitIRaw.objects.create(repo=self.repo,
                                               user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """

        candidates = self.repo.gitienrich_set.filter(job__isnull=False)
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
        logger.info(f"Running GitEnrich intention: {self.repo.url}")
