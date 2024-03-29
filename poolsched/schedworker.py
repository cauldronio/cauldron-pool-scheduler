"""
API for poolsched (scheduling of a pool of tasks)

When you instantiate a Worker, it is important to define an intention order,
otherwise, it won't take any jobs.

The precedence of a job should be governed by the following rules:
- Job that is in the last phase of the analysis
- Job that needs little time to run
- Job that doesn't use a token

"""

import logging
import traceback
import socket
from time import sleep
from random import sample

from django.forms.models import model_to_dict
from django.contrib.auth import get_user_model

from .models import Worker, Job, ArchJob, ArchivedIntention, ScheduledIntention

User = get_user_model()

# Default global level to DEBUG. Control level with handlers
logging.getLogger().setLevel(logging.DEBUG)

logger = logging.getLogger(__name__)
LOG_LEVEL = logging.INFO


class SchedWorker:
    """Workers for which jobs are scheduled"""

    def _get_random_user_ready(self, max=1):
        """Get random user ids, for users with ready Intentions.

        Ready intentions are those that are in READY status (do not have
        pending previous intentions), and still don't have a job.

        :param max: maximum number of users
        :returns:   list of User objects
        """
        q = User.objects.filter(intention__isnull=False,
                                intention__previous=None,
                                intention__job=None).distinct()
        count = q.count()
        try:
            users = [q[i] for i in sample(range(count), min(max, count))]
        except IndexError:
            users = []
        return users

    def _get_intentions(self, users, max=1):
        """Get intentions suitable to run, for a list of users

        This is called by a worker looking for new jobs

        :user_ids: list of User ids to check intentions
        :param max: maximum number of intentions to return
        """

        intentions = []
        for user in users:
            logger.debug(user)
            for intention_type in self.intention_order:
                intentions.extend(intention_type.objects.selectable_intentions(user=user, max=max))
                if len(intentions) >= max:
                    break
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
                # Create job and assign the worker
                job = intention.create_job(self.worker)
                break
            else:
                # There is a job but not for this worker
                job = None
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

        users = self._get_random_user_ready(max=max_users)
        logger.debug("get_job() users: " + str(users))
        intentions = self._get_intentions(users=users, max=max_intentions)
        logger.debug("get_job() intentions: " + str(intentions))
        job = self._new_job(intentions)
        if job is not None:
            logger.debug("get_job() job: " + str(model_to_dict(job)))
        return job

    def next_job(self):
        """Get the next job to run, among those WAITING"""
        job = None
        for intention_type in self.intention_order:
            job = intention_type.next_job(self.worker)
            if job:
                break
        return job

    def run_job(self, job):
        """Run the job

        This will run some code defined by the intention.
        If the job is finished, it is archived and the intention marked as DONE

        :param job: Job object to run
        :return:    Job object after running
        """

        try:
            logger.info(f"Job to run: {model_to_dict(job)}")
            intention = job.intention_set.first()
            logger.info(f"Intention to run (casted): {model_to_dict(intention)} ({model_to_dict(intention.cast())})")
            completed = intention.cast().run(job)
            if completed:
                self.archive(job, ArchivedIntention.OK)
            else:
                job.worker = None
                job.save()
        except Job.StopException as e:
            logger.info(f"Intention stopped before completing: {job}")
            self.archive(job, ArchivedIntention.ERROR)
        except Exception as e:
            logger.error(f"Other exception (error?): {job}, {e}")
            traceback.print_exc()
            self.archive(job, ArchivedIntention.ERROR)
        return job

    def archive(self, job, status):
        """Archive job and intentions with the status specified"""
        intentions = list(job.intention_set.all())
        logger.info("Archiving job: " + str(model_to_dict(job)))
        arch_job = ArchJob(created=job.created, worker=job.worker, logs=job.logs)
        arch_job.save()
        for intention in intentions:
            logger.info("Archiving intention: " + str(model_to_dict(intention)))
            intention.cast().archive(status, arch_job)
        # delete the job after archiving the intentions to avoid race conditions
        job.delete()

    def configure_logging(self):
        """Configure logging for poolsched module"""
        name = f"worker_{self.worker.id}"
        scheduler_log = logging.getLogger('poolsched')
        formatter = logging.Formatter(f"[%(levelname)s - {name} - %(asctime)s] - %(message)s")
        handler = logging.StreamHandler()
        handler.setFormatter(formatter)
        handler.setLevel(LOG_LEVEL)
        scheduler_log.addHandler(handler)

    def __init__(self, run=False, finish=False, intention_order=None):
        """Start the party

        :param run: run the loop, or not (default: False)
        :param finish: finish when there are no more jobs
        :param intention_order: list of subclasses of intentions to be picked
        by the worker in the defined order
        """
        logger.info("Starting scheduler worker...")
        worker_location = socket.gethostname()
        self.intention_order = intention_order or []
        self.worker = Worker.objects.create(status=Worker.Status.UP, machine=worker_location)
        self.configure_logging()
        wait_task_msg = True
        while run:
            # Create scheduled intentions
            ScheduledIntention.objects.create_intentions(self.worker)
            if wait_task_msg:
                logger.info("Waiting for new tasks...")
                wait_task_msg = False
            # Get next job, among those available to run
            job = self.next_job()
            logger.debug(f"Job obtained from next_job(): {job}")
            if job is None:
                # No job available (but maybe there are available intentions)
                # TODO: Change the way we get the number of workers
                worker_jobs = Job.objects.exclude(worker=None).count()
                workers_no = Worker.objects.count()
                logger.debug(f"Jobs in worker (workers): {worker_jobs} ({workers_no})")
                if worker_jobs < (5 * workers_no):
                    # Get a new job for worker, if we don't have too many
                    job = self.get_new_job(max_users=4)
                    logger.debug(f"Job obtained from get_new_job(): {job}")
            if job is not None:
                if job.worker == self.worker:
                    logger.debug(f"About to run job: {job}")
                    self.run_job(job)
                    wait_task_msg = True
            else:
                if finish:
                    if worker_jobs == 0:
                        break
                sleep(3)
