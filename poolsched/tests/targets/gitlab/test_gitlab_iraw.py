import logging
import datetime

from django.test import TestCase
from django.utils.timezone import now

from ....models import Intention
from ....models import Job, User, Worker
from ....models.targets.gitlab import GLInstance, GLRepo, GLIRaw, GLToken

GITLAB_INSTANCE = GLInstance.objects.get(name='GitLab')

logger = logging.getLogger(__name__)


class TestBasic(TestCase):

    def test_create(self):
        """Insert a single GLIRaw into the database"""
        repo = GLRepo.objects.create(owner='owner', repo='repo',
                                     instance=GITLAB_INSTANCE)
        iraw = GLIRaw.objects.create(repo=repo)
        found = GLIRaw.objects.get(repo=repo)
        self.assertEqual(iraw, found)

    def test_create_2(self):
        """Insert two GLIRaw into the database"""
        repo1 = GLRepo.objects.create(owner='owner1', repo='repo',
                                      instance=GITLAB_INSTANCE)
        repo2 = GLRepo.objects.create(owner='owner2', repo='repo',
                                      instance=GITLAB_INSTANCE)

        iraw1 = GLIRaw.objects.create(repo=repo1)
        iraw2 = GLIRaw.objects.create(repo=repo2)

        iraws = GLIRaw.objects.all()
        self.assertEqual(len(iraws), 2)
        self.assertIn(iraw1, iraws)
        self.assertIn(iraw2, iraws)

    def test_token_exception(self):
        """Test the initialization of TokenExhaustedException and str method"""
        token = GLToken()
        msg = 'GLToken error'
        exc = GLIRaw.TokenExhaustedException(token=token, message=msg)
        self.assertEqual(exc.token, token)
        self.assertEqual(exc.message, msg)
        self.assertEqual(str(exc), msg)


class TestMethods(TestCase):

    def setUp(self):
        self.repo1 = GLRepo.objects.create(owner='owner1', repo='repo',
                                           instance=GITLAB_INSTANCE)
        self.user1 = User.objects.create(username='A')
        self.user2 = User.objects.create(username='B')
        self.iraw1 = GLIRaw.objects.create(repo=self.repo1, user=self.user1)
        self.iraw2 = GLIRaw.objects.create(repo=self.repo1, user=self.user2)
        self.token1 = GLToken.objects.create(token='0123456')
        self.token2 = GLToken.objects.create(token='6543210')
        self.worker1 = Worker.objects.create()
        self.worker2 = Worker.objects.create()

    def test_create_previous(self):
        """Test create previous method"""
        prev = self.iraw1.create_previous()
        self.assertEqual(prev, [])

    def test_create_job(self):
        """Test create GLIRaw job without token"""
        job = self.iraw1.create_job(self.worker1)
        self.assertEqual(job, None)

    def test_create_job2(self):
        """Test create GLIRaw job with token"""
        self.user1.gltokens.add(self.token1)
        job = self.iraw1.create_job(self.worker1)
        self.assertEqual(job.worker, self.worker1)
        self.assertEqual(self.iraw1.job, job)
        self.assertIn(self.token1, job.gltokens.all())

    def test_create_job3(self):
        """Test create GLIRaw job with existing job"""
        self.user1.gltokens.add(self.token1)
        job1 = self.iraw1.create_job(self.worker1)
        job2 = self.iraw1.create_job(self.worker1)
        self.assertEqual(job1.worker, self.worker1)
        self.assertEqual(job2, None)

    def test_running_job(self):
        """Test find a job for iraw1 that doesn't exist"""
        job = self.iraw1.running_job()
        self.assertEqual(job, None)

    def test_running_job2(self):
        """Test find a job for iraw1 that exists"""
        new_job = Job.objects.create()
        self.iraw2.job = new_job
        self.iraw2.save()
        self.iraw1.user.gltokens.add(self.token1)
        job = self.iraw1.running_job()
        self.assertEqual(job, new_job)


class TestSelectableIntentions(TestCase):

    def setUp(self):
        """
        User 1: 0 intentions
        User 2: 1 intention ready
        User 3: 2 intention ready
        User 4: 1 intention ready, 1 intention running
        User 5: 1 intention ready, 1 intention with Job
        User 6: 1 intention ready with future reset time in token
        User 7: 1 intention ready without token
        :return:
        """
        self.repo1 = GLRepo.objects.create(owner='owner1', repo='repo1',
                                           instance=GITLAB_INSTANCE)
        self.repo2 = GLRepo.objects.create(owner='owner2', repo='repo2',
                                           instance=GITLAB_INSTANCE)

        self.user1 = User.objects.create(username='1')
        self.token1 = GLToken.objects.create(token='0123456', user=self.user1)

        self.user2 = User.objects.create(username='2')
        self.token2 = GLToken.objects.create(token='0123456', user=self.user2)
        self.iraw_U2_1 = GLIRaw.objects.create(repo=self.repo1, user=self.user2,
                                               status=Intention.Status.READY)

        self.user3 = User.objects.create(username='3')
        self.token3 = GLToken.objects.create(token='0123456', user=self.user3)
        self.iraw_U3_1 = GLIRaw.objects.create(repo=self.repo1, user=self.user3,
                                               status=Intention.Status.READY)
        self.iraw_U3_2 = GLIRaw.objects.create(repo=self.repo2, user=self.user3,
                                               status=Intention.Status.READY)

        self.user4 = User.objects.create(username='4')
        self.token4 = GLToken.objects.create(token='0123456', user=self.user4)
        self.iraw_U4_1 = GLIRaw.objects.create(repo=self.repo1, user=self.user4,
                                               status=Intention.Status.READY)
        self.iraw_U4_2 = GLIRaw.objects.create(repo=self.repo2, user=self.user4,
                                               status=Intention.Status.WORKING)

        self.user5 = User.objects.create(username='5')
        self.token5 = GLToken.objects.create(token='0123456', user=self.user5)
        self.iraw_U5_1 = GLIRaw.objects.create(repo=self.repo1, user=self.user5,
                                               status=Intention.Status.READY)
        self.job_U5 = Job.objects.create()
        self.iraw_U5_2 = GLIRaw.objects.create(repo=self.repo2, user=self.user5,
                                               status=Intention.Status.READY,
                                               job=self.job_U5)

        self.user6 = User.objects.create(username='6')
        self.token6 = GLToken.objects.create(token='0123456', user=self.user6,
                                             reset=now() + datetime.timedelta(hours=1))
        self.iraw_U6_1 = GLIRaw.objects.create(repo=self.repo1, user=self.user6,
                                               status=Intention.Status.READY)

        self.user7 = User.objects.create(username='7')
        self.iraw_U7_1 = GLIRaw.objects.create(repo=self.repo1, user=self.user7,
                                               status=Intention.Status.READY)

    def test_user_1(self):
        """Test not available intentions"""
        intentions = GLIRaw.objects.selectable_intentions(user=self.user1)
        self.assertEqual(len(intentions), 0)

    def test_user_2(self):
        """Test one intention ready"""
        intentions = GLIRaw.objects.selectable_intentions(user=self.user2)
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], self.iraw_U2_1)

    def test_user_3(self):
        """Test two intentions ready, get 1"""
        intentions = GLIRaw.objects.selectable_intentions(user=self.user3, max=1)
        self.assertEqual(len(intentions), 1)
        self.assertIn(intentions[0], [self.iraw_U3_1, self.iraw_U3_2])

    def test_user_3b(self):
        """Test two intentions ready, get 2"""
        intentions = GLIRaw.objects.selectable_intentions(user=self.user3, max=2)
        self.assertEqual(len(intentions), 2)
        self.assertListEqual(list(intentions), [self.iraw_U3_1, self.iraw_U3_2])

    def test_user_4(self):
        """Test one running one ready"""
        intentions = GLIRaw.objects.selectable_intentions(user=self.user4, max=2)
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], self.iraw_U4_1)

    def test_user_5(self):
        """Test one ready and one ready with job"""
        intentions = GLIRaw.objects.selectable_intentions(user=self.user5, max=2)
        self.assertEqual(len(intentions), 1)

    def test_user_6(self):
        """Test one ready, with future reset token"""
        intentions = GLIRaw.objects.selectable_intentions(user=self.user6, max=2)
        self.assertEqual(len(intentions), 0)

    def test_user_7(self):
        """Test one ready, without token"""
        intentions = GLIRaw.objects.selectable_intentions(user=self.user7, max=2)
        self.assertEqual(len(intentions), 0)
