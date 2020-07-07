"""
API for poolsched (scheduling of a pool of tasks)
"""

import logging
from time import sleep

from django.forms.models import model_to_dict

from .models import Worker, Intention, User, Job, ArchJob
from .models.targets.github import GHIRaw, GHIEnrich
from .models.targets.git import GitIRaw as GitIRaw
from .models.targets.git import GitIEnrich as GitIEnrich

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

"""
The precedence of a job is governed by the following rules:
- Job that is in the last phase of the analysis
- Job that needs little time to run
- Job that doesn't use a token
"""
INTENTION_ORDER = [GitIEnrich, GHIEnrich, GitIRaw, GHIRaw]


class SchedWorker:
    """Workers for which jobs are scheduled"""

    # List of workers currently working
    workers = []

    def _get_intentions(self, users, max=1):
        """Get intentions suitable to run, for a list of users

        This is called by a worker looking for new jobs

        :user_ids: list of User ids to check intentions
        :param max: maximum number of intentions to return
        """

        intentions = []
        for user in users:
            for intention_type in INTENTION_ORDER:
                intentions.extend(intention_type.objects.selectable_intentions(user=user, max=max))
            if len(intentions) >= max:
                break
        return intentions[0:max]

    def _new_job(self, intentions):
        """Create a new job for this worker, given a list of intentions

        This relies on the intention having both `running_job` and
        `create_job` methods.
        * If there is a running job of a similar intention
        (eg, one for the same repo), assign it to the intention,
        and go for the next intention.
        * If there is no running job, try to create a new job,
        return it if success, else go fot the next intention
        * If no job can be created, return None.

        :param intentions: list of intentions
        :returns:          job, with worker assigned, or None
        """

        job = None
        for intention in intentions:
            job = intention.running_job()
            if job is None:
                job = intention.create_job(self.worker)
                intention.save()
                break
        return job

    def get_new_job(self, max_users=2, max_intentions=1):
        """Get a new job to run in this worker

        Get a list of users (randomly), then a list of intentions
        for them, finally produce a job for one of the intentions.
        It is convenient to have more than one user in the
        list of users whose intentions will be checked,
        just in case some intentions are ready but not ready
        to go, because of lack of tokens or something else,
        of they are already addressed by some running job
        (which will get the intention).
        If no job can be obtained this way, None is returned

        :param max_users: maximum number of users with intentions ready to check
        :param max_intentions: maximum number of intentions to check
        :returns: job ready to run, or None
        """

        users = User.objects.random_user_ready(max=max_users)
        logger.debug("get_job() users: " + str(users))
        intentions = self._get_intentions(users=users, max=max_intentions)
        logger.debug("get_job() intentions: " + str(intentions))
        job = self._new_job(intentions)
        logger.debug("get_job() job: " + str(job))
        if job is not None:
            logger.debug("get_job() job: " + str(model_to_dict(job)))
        return job

    def next_job(self):
        """Get the next job to run, among those WAITING"""
        job = None
        for intention_type in INTENTION_ORDER:
            job = intention_type.next_job()
            if job:
                break
        return job

    def run_job(self, job):
        """Run the job

        This will run some code defined by the intention.

        :param job: Job object to run
        :return:    Job object after running
        """

        try:
            logger.debug(f"Job to run: {job}")
            intention = job.intention_set.first()
            logger.debug(f"Intention to run (casted): {intention} ({intention.cast()})")
            intention.cast().run(job)
            job.status = Job.Status.DONE
            for intention in job.intention_set.all():
                intention.status = Intention.Status.DONE
                intention.save()
            job.save()
        except Job.StopException as e:
            logger.debug(f"Intention stopped before completing: {job}")
        except Exception as e:
            logger.info(f"Other exception (error?): {job}, {e}")
        return job

    def archive_job(self, job):
        """Archive the job, it is already done"""

        logger.info("Archiving job: " + str(model_to_dict(job)))
        arch_job = ArchJob(created=job.created, worker=job.worker)
        arch_job.save()
        job.delete()

    def __init__(self, run=False, finish=False):
        """Start the party

        :param run: run the loop, or not (default: False)
        :param finish: finish when there are no more jobs
        """
        logger.info("Starting scheduler worker...")
        self.worker = Worker.objects.create()
        self.workers.append(self.worker)
        while run:
            logger.info("Waiting for new tasks...")
            # Get next job, among those available to run
            job = self.next_job()
            logger.debug(f"Job obtained from next_job(): {job}")
            if job is None:
                # No job available (but maybe there are unavailable jobs)
                worker_jobs = Job.objects.exclude(worker=None).count()
                workers_no = len(self.workers)
                logger.debug(f"Jobs in worker (workers): {worker_jobs} ({workers_no})")
                if worker_jobs < (5 * workers_no):
                    # Get a new job for worker, if we don't have too many
                    job = self.get_new_job()
                    logger.debug(f"Job obtained from get_new_job(): {job}")
            if job is not None:
                logger.debug(f"About to run job: {job},{job.status}")
                job = self.run_job(job)
                if job.status == Job.Status.DONE:
                    self.archive_job(job)
            else:
                if finish:
                    if worker_jobs == 0:
                        remaining = Intention.objects.exclude(status=Intention.Status.DONE)
                        logger.debug(f"Remaining intentions: {remaining}")
                        if remaining.count() == 0:
                            break
                sleep(3)
