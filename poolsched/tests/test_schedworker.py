from datetime import timedelta
import logging
from unittest.mock import patch

from django.test import TestCase
from django.contrib.auth import get_user_model
from django.utils.timezone import now

from ..models import Intention, ArchJob
from ..models.targets.github import IGHRaw, GHRepo, GHToken, IGHRawArchived
from ..schedworker import SchedWorker

User = get_user_model()

logger = logging.getLogger(__name__)

call_no = 0


def mock_run(intention, job):
    """ Raise TokenExhaustedException 5 times and then return None"""
    repo = intention.repo
    token = job.ghtokens.filter(reset__lt=now()).first()
    logger.debug(f"Mock running GitHubRaw intention: {repo.owner}/{repo.repo}, token: {token}")
    global call_no
    if call_no < 5:
        call_no += 1
        logger.debug(f"Exception: {call_no}.")
        raise IGHRaw.TokenExhaustedException(token=token)
    logger.debug(f"No exception: {call_no}")


def mock_skip_run(intention, job):
    """Skip the execution of the run method and return always None"""
    logger.debug(f"Skip run method for intention {intention.id}, job {job}")
    return None


class TestRandomUserReady(TestCase):
    """Test random_user_ready"""

    @classmethod
    def setUpTestData(cls):
        """Populate the database"""

        # Scale for random tests (no_tests = scale*10)
        cls.scale = 100
        user1 = User.objects.create(username='A')
        user2 = User.objects.create(username='B')
        user3 = User.objects.create(username='C')
        user4 = User.objects.create(username='D')
        user5 = User.objects.create(username='E')
        user6 = User.objects.create(username='F')
        # For each user: [user, #intentions ready, #intentions working]
        users = [[user1, 10, 2], [user2, 20, 10],
                 [user3, 30, 3], [user4, 40, 40],
                 [user5, 0, 20], [user6, 0, 120]]
        for user in users:
            for intention in range(0, user[1]):
                Intention.objects.create(user=user[0])
            for intention in range(0, user[2]):
                intent = Intention.objects.create(user=user[0])
                intent.previous.add(Intention.objects.create())
                intent.save()

    def test_random_user_id_ready(self):
        """Some intentions from the random user"""
        worker = SchedWorker()
        occurrences = [0, 0, 0, 0]
        for cont in range(0, 10 * self.scale):
            [user] = worker._get_random_user_ready()
            occurrences[user.id - 1] += 1
        for occurrence in occurrences:
            if occurrence > 3 * self.scale:
                random = False
            elif occurrence < 2 * self.scale:
                random = False
            else:
                random = True
            self.assertTrue(random, msg="Random is not so random")

    def test_random_user_id_ready_several(self):
        """Some intentions from the random user"""
        worker = SchedWorker()
        occurrences = [0, 0, 0, 0]
        for cont in range(0, 10 * self.scale):
            [u1, u2] = worker._get_random_user_ready(max=2)
            for id in [u1.id, u2.id]:
                occurrences[id - 1] += 1
        for occurrence in occurrences:
            if occurrence > 6 * self.scale:
                random = False
            elif occurrence < 4 * self.scale:
                random = False
            else:
                random = True
            self.assertTrue(random, msg="Random is not so random: " + str(occurrences))

        occurrences = [0, 0, 0, 0]
        for cont in range(0, 10 * self.scale):
            [u1, u2, u3] = worker._get_random_user_ready(max=3)
            for id in [u1.id, u2.id, u3.id]:
                occurrences[id - 1] += 1
        for occurrence in occurrences:
            if occurrence > 9 * self.scale:
                random = False
            elif occurrence < 6 * self.scale:
                random = False
            else:
                random = True
            self.assertTrue(random, msg="Random is not so random: " + str(occurrences))


class TestPoolSched(TestCase):
    """Test poolsched module"""

    def setUp(self):
        """Populate the database

        Summary:
         * User A has three intentions (ready, ready), and one ready token
         * User B has two intentions (ready), and one ready token
         * User C has two intentions (ready), and exhausted token
         * User D has no intentions
        """

        # Some users
        self.users = [User.objects.create(username=username)
                      for username in ['A', 'B', 'C', 'D']]
        # Some repos
        self.repos = [GHRepo.objects.create(owner='owner',
                                            repo=repo)
                      for repo in ['R0', 'R1', 'R2', 'R3']]
        repo_count = 0
        # Five tokens, one per user (three exhausted)
        for user in self.users:
            repo_count = (repo_count + 1) % len(self.repos)
            token = GHToken.objects.create(
                token=user.username + "0123456789")
            # Let's have a exhausted tokens, for users C
            if user.username == 'C':
                token.reset = now() + timedelta(seconds=60)
            token.user = user
            token.save()
        # Three intentions, for users A, B, C, all ready
        for user in self.users[:3]:
            intention = IGHRaw.objects.create(
                user=user,
                repo=self.repos[repo_count]
            )
            repo_count = (repo_count + 1) % len(self.repos)
        # One more intention, for user A, ready
        for user in self.users[:1]:
            intention = IGHRaw.objects.create(
                user=user,
                repo=self.repos[repo_count]
            )

    @patch.object(IGHRaw, 'run', side_effect=mock_skip_run, autospec=True)
    def test_init(self, mock_skip_run):
        # logging.basicConfig(level=logging.DEBUG)
        worker = SchedWorker(run=True, finish=True)
        archived_IGHRaw = IGHRawArchived.objects.count()
        archived_jobs = ArchJob.objects.count()
        self.assertEqual(archived_IGHRaw, 3)
        self.assertEqual(archived_jobs, 3)

    @patch.object(IGHRaw, 'run', side_effect=mock_skip_run, autospec=True)
    def test_new_job_manual(self, mock_skip):
        """Test new_job"""

        worker = SchedWorker()
        users = worker._get_random_user_ready(max=4)
        intentions = worker._get_intentions(users=users)
        self.assertEqual(len(intentions), 1)
        job = worker._new_job(intentions)
        self.assertEqual(job.worker, worker.worker)

    @patch.object(IGHRaw, 'run', side_effect=mock_skip_run, autospec=True)
    def test_get_new_job(self, mock_skip):
        """Test new_job"""
        # logging.basicConfig(level=logging.DEBUG)
        worker = SchedWorker()
        job = worker.get_new_job(max_users=5)
        self.assertEqual(job.worker, worker.worker)
        intention = job.intention_set.first()
        tokens = job.ghtokens.all()
        self.assertEqual(len(tokens), 1)
        self.assertEqual(intention.user, tokens[0].user)

    @patch.object(IGHRaw, 'run', side_effect=mock_skip_run, autospec=True)
    def test_get_intentions(self, mock_skip_run):
        """Test get_intentions, for a single user"""

        # Expected intentions ready (per user)
        expected_intentions = {'A': 2, 'B': 1, 'C': 0, 'D': 0, 'E': 0, 'F': 0}
        worker = SchedWorker()
        # Get all users
        users = User.objects.all()
        # Check all users, one user each loop
        for user in users:
            # Check one intention returned at most
            intentions = worker._get_intentions(users=[user])
            self.assertEqual(len(intentions),
                             min(expected_intentions[user.username], 1))
            # Check all intentions are found
            intentions = worker._get_intentions(users=[user], max=4)
            self.assertEqual(len(intentions),
                             expected_intentions[user.username])
            # Check some constraints on intentions found
            for intention in intentions:
                # Find if there is at least one token with reset time in the future
                tokens = intention.user.ghtokens.all()
                token_ready = False
                for token in tokens:
                    if token.reset <= now():
                        token_ready = True
                        break
                self.assertEqual(
                    token_ready, True,
                    "No token ready, but was selected to run: " + str(tokens)
                )

    @patch.object(IGHRaw, 'run', side_effect=mock_skip_run, autospec=True)
    def test_get_intentions2(self, mock_skip_run):
        """Test get_intentions, calling it with two users"""

        # Expected intentions ready (per user)
        exp_intentions = {'A': 2, 'B': 1, 'C': 0, 'D': 0, 'E': 0, 'F': 0}
        worker = SchedWorker()
        # Get all users
        users = User.objects.all()
        # Check for several max number of intentions
        for max in range(5):
            # Check all users, two users each loop
            for i in range(len(users)):
                if i + 1 < len(users):
                    u1, u2 = i, i + 1
                else:
                    u1, u2 = i, 0
                two_users = [users[u1], users[u2]]
                expected = (exp_intentions[users[u1].username]
                            + exp_intentions[users[u2].username]) # noqa
                intentions = worker._get_intentions(users=two_users,
                                                    max=max)
                self.assertEqual(len(intentions), min(expected, max))

    @patch.object(IGHRaw, 'run', side_effect=mock_run, autospec=True)
    def test_init2(self, mock_fun):
        #        logging.basicConfig(level=logging.DEBUG)
        worker = SchedWorker(run=True, finish=True)
        # Run should run 5 times being interrupted, and 3 more (all intentions done)
        self.assertEqual(mock_fun.call_count, 8)
