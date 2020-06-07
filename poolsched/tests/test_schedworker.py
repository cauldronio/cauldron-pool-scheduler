from datetime import timedelta
import logging
from unittest.mock import patch

from django.test import TestCase
from django.utils.timezone import now

from ..models import User, Intention, Job
from ..models.targets.github import IRaw as GHIRaw, \
    Repo as GHRepo, Token as GHToken
from ..schedworker import SchedWorker

logger = logging.getLogger(__name__)
#logging.basicConfig(level=logging.WARNING)

call_no = 0

def mock_run(intention, job):
    repo = intention.repo
    token = job.token_set.filter(reset__lt=now()).first()
    logger.debug(f"Mock running GitHubRaw intention: {repo.owner}/{repo.repo}, token: {token}")
    global call_no
    if call_no < 5:
        call_no += 1
        logger.debug(f"Exception: {call_no}.")
        raise GHIRaw.TokenExhaustedException(token=token)
    logger.debug(f"No exception: {call_no}")


class TestPoolSched(TestCase):
    """Test poolsched module"""

    def setUp(self):
        """Populate the database

        Summary:
         * User A has three intentions (done, ready, ready), and one ready token
         * User B has two intentions (done, ready), and one ready token
         * User C has two intentions (done, ready), and one exhausted token
         * User D has one intention (done), and one exhausted token
         * User E has one intention (done), and one exhausted token
        """

        # Some users
        self.users = [User.objects.create(username=username)
                 for username in ['A', 'B', 'C', 'D', 'E']]
        # Some repos
        self.repos = [GHRepo.objects.create(owner='owner',
                                            repo=repo)
                     for repo in ['R0', 'R1', 'R2', 'R3']]
        repo_count = 0
        # Five intentions done, one per user, and five tokens (three exhausted)
        for user in self.users:
            intention = GHIRaw.objects.create(
                user=user,
                status=Intention.Status.DONE,
                repo=self.repos[repo_count]
            )
            repo_count = (repo_count + 1) % len(self.repos)
            token = GHToken.objects.create(
                token=user.username + "0123456789")
            # Let's have three exhausted tokens, for users C, D, E
            if user.username in ['C', 'D', 'E']:
                token.reset = now() + timedelta(seconds=2)
            token.user = user
            token.save()
        # Three more intentions, for users A, B, C, all ready
        for user in self.users[:3]:
            intention = GHIRaw.objects.create (
                user=user,
                status=Intention.Status.READY,
                repo=self.repos[repo_count]
            )
            repo_count = (repo_count + 1) % len(self.repos)
        # One more intention, for user A, ready
        for user in self.users[:1]:
            intention = GHIRaw.objects.create (
                user=user,
                status=Intention.Status.READY,
                repo=self.repos[repo_count]
            )

    def test_init(self):

#        logging.basicConfig(level=logging.DEBUG)
        worker = SchedWorker(run=True, finish=True)
        for job in Job.objects.all():
            self.assertEqual(job.status, Job.Status.DONE)
        for intention in Intention.objects.all():
            self.assertEqual(intention.status, Intention.Status.DONE)

    def test_new_job_manual(self):
        """Test new_job"""

        worker = SchedWorker()
        users = User.objects.random_user_ready(max=2)
        intentions = worker._get_intentions(users=users)
        self.assertEqual(len(intentions), 1)
        job = worker._new_job(intentions)
        self.assertEqual(job.worker, worker.worker)
        self.assertEqual(job.status, Job.Status.WAITING)

    def test_get_new_job(self):
        """Test new_job"""

        worker = SchedWorker()
        job = worker.get_new_job()
        self.assertEqual(job.worker, worker.worker)
        self.assertEqual(job.status, Job.Status.WAITING)
        intention = job.intention_set.first()
        self.assertEqual(intention.status,Intention.Status.READY)
        tokens = job.token_set.all()
        self.assertEqual(len(tokens),1)
        self.assertEqual(intention.user, tokens[0].user)

    def test_get_intentions(self):
        """Test get_intentions, for a single user"""

        # Expected intentions ready (per user)
        expected_intentions = {'A': 2, 'B': 1, 'C': 0, 'D': 0, 'E': 0}
        worker = SchedWorker()
        # Get all users
        users = User.objects.all()
        # Check all users, one user each loop
        for user in users:
            # Check one intention returned at most
            intentions = worker._get_intentions(users=[user])
            self.assertEqual(len(intentions),
                             min(expected_intentions[user.username],1))
            # Check all intentions are found
            intentions = worker._get_intentions(users=[user], max=4)
            self.assertEqual(len(intentions),
                             expected_intentions[user.username])
            # Check some constraints on intentions found
            for intention in intentions:
                # Intention is ready
                self.assertEqual(intention.status, Intention.Status.READY)
                # Find if there is at least one token with reset time in the future
                tokens = intention.user.token_set.all()
                token_ready = False
                for token in tokens:
                    if token.reset <= now():
                        token_ready = True
                        break
                self.assertEqual(
                    token_ready, True,
                    "No token ready, but was selected to run: " + str(tokens)
                )

    def test_get_intentions2(self):
        """Test get_intentions, calling it with two users"""

        # Expected intentions ready (per user)
        exp_intentions = {'A': 2, 'B': 1, 'C': 0, 'D': 0, 'E': 0}
        worker = SchedWorker()
        # Get all users
        users = User.objects.all()
        # Check for several max number of intentions
        for max in range(5):
            # Check all users, two users each loop
            for i in range(len(users)):
                if i+1 < len(users):
                    u1, u2 = i, i + 1
                else:
                    u1, u2 = i, 0
                two_users = [users[u1], users[u2]]
                expected = exp_intentions[users[u1].username] + \
                    exp_intentions[users[u2].username]
                intentions = worker._get_intentions(users=two_users,
                                                    max=max)
                self.assertEqual(len(intentions), min(expected, max))

    @patch.object(GHIRaw, 'run', side_effect=mock_run, autospec=True)
    def test_init2(self, mock_fun):
#        logging.basicConfig(level=logging.DEBUG)
        worker = SchedWorker(run=True, finish=True)
        # Run should run 5 times being interrupted, and 4 more (all intentions done)
        self.assertEqual(mock_fun.call_count, 9)