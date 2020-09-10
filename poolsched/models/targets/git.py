import logging

from django.db import models, IntegrityError, transaction
from django.conf import settings
from django.utils.timezone import now

from poolsched import utils
from ..intentions import Intention
from ..jobs import Job

try:
    from mordred.backends.git import GitEnrich, GitRaw
except ImportError as exc:
    logging.error(f'[EXPECTED] {exc}')
    GitEnrich = utils.mordred_not_imported
    GitRaw = utils.mordred_not_imported

logger = logging.getLogger(__name__)
global_logger = logging.getLogger()

TABLE_PREFIX = 'poolsched_git'


class GitRepo(models.Model):
    """Git repository"""

    url = models.CharField(max_length=255, unique=True)

    # When the repo was created in the scheduler
    created = models.DateTimeField(default=now, blank=True)

    class Meta:
        db_table = TABLE_PREFIX + 'repo'


class IRawManager(models.Manager):
    """Model manager for IGitRaw"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IGitRaw intentions for a user

        A intention is selectable if:
        * it's status is ready
        * no job is still associated with it
        It's not important if there is other job for the same url,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGitRaw intentions
        """

        intentions = self.filter(user=user,
                                 job=None)
        return intentions.all()[:max]


class IGitRaw(Intention):
    """Intention for producing raw indexes for Git repos"""

    # GitRepo to analyze
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'iraw'
    objects = IRawManager()

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """
        job = None
        intention = IGitRaw.objects\
            .select_related('job').select_for_update()\
            .exclude(job=None).filter(job__worker=None)\
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

        :return:          Job object, if it was found, or None, if not
        """

        candidates = self.repo.igitraw_set.filter(job__isnull=False)
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
        logger.info(f"Running GitRaw intention: {self.repo.url}")
        fh = utils.file_formatter(f"job-{job.id}.log")
        global_logger.addHandler(fh)
        runner = GitRaw(self.repo.url)
        output = runner.run()
        global_logger.removeHandler(fh)
        if output:
            raise Job.StopException

    def archive(self):
        """Archive and remove the current intention"""
        IGitRawArchived.objects.create(user=self.user,
                                       repo=self.repo,
                                       created=self.created)
        self.delete()


class IEnrichedManager(models.Manager):
    """Model manager for IGitEnrich"""

    def selectable_intentions(self, user, max=1):
        """Return a list of selectable IGitEnrich intentions for a user

        A intention is selectable if:
        * it's status is ready
        * no job is still associated with it
        It's not important if there is other job for the same repo,
        that will be checked later.

        :param user: user to check
        :param max:  maximum number of intentions to return
        :returns:    list of IGitRaw intentions
        """

        intentions = self.filter(user=user,
                                 job=None,
                                 previous=None)
        return intentions.all()[:max]


class IGitEnrich(Intention):
    """Intention for producing enriched indexes for Git repos"""

    # GitRepo to analyze
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)

    class Meta:
        db_table = TABLE_PREFIX + 'ienriched'
    objects = IEnrichedManager()

    @classmethod
    @transaction.atomic
    def next_job(cls, worker):
        """Find the next job of this model.

        To be selected, a job should be waiting.
        Usually, this will be chained to the query for the jobs in a worker.

        :return:           selected job (None if none is ready)
        """
        job = None
        intention = IGitEnrich.objects\
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

        raw_intention, _ = IGitRaw.objects.get_or_create(repo=self.repo,
                                                         user=self.user)
        self.previous.add(raw_intention)
        return [raw_intention]

    def running_job(self):
        """Find a Job that satisfies this intention

        If a not done job is found, the intention is assigned
        and the job is returned.

        :return: Job object, if it was found, or None, if not
        """

        candidates = self.repo.igitenrich_set.filter(job__isnull=False)
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
                    self.save()
        except IntegrityError:
            return None
        return job

    def run(self, job):
        """Run the code to fulfill this intention

        :return:
        """
        logger.info(f"Running GitEnrich intention: {self.repo.url}")
        fh = utils.file_formatter(f"job-{job.id}.log")
        global_logger.addHandler(fh)
        runner = GitEnrich(self.repo.url)
        output = runner.run()
        global_logger.removeHandler(fh)
        if output:
            raise Job.StopException

    def archive(self):
        """Archive and remove the current intention"""
        IGitEnrichArchived.objects.create(user=self.user,
                                          repo=self.repo,
                                          created=self.created)
        self.delete()


class IGitRawArchived(models.Model):
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             default=None, null=True, blank=True)
    created = models.DateTimeField()
    completed = models.DateTimeField(auto_now_add=True)


class IGitEnrichArchived(models.Model):
    repo = models.ForeignKey(GitRepo, on_delete=models.PROTECT)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT,
                             default=None, null=True, blank=True)
    created = models.DateTimeField()
    completed = models.DateTimeField(auto_now_add=True)
