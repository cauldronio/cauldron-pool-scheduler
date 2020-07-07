import logging

from django.test import TestCase

from ....models import Intention
from ....models import Job, User, Worker
from ....models.targets.github import GHInstance, GHRepo, GHIEnrich

GITHUB_INSTANCE = GHInstance.objects.get(name='GitHub')

logger = logging.getLogger(__name__)


class TestBasicCreate(TestCase):

    def test_create(self):
        """Insert a single IEnrich into the database"""
        repo = GHRepo.objects.create(owner='owner', repo='repo',
                                     instance=GITHUB_INSTANCE)
        enrich = GHIEnrich.objects.create(repo=repo)
        found = GHIEnrich.objects.get(repo=repo)
        self.assertEqual(enrich, found)

    def test_create_2(self):
        """Insert two IEnrich into the database"""
        repo1 = GHRepo.objects.create(owner='owner1', repo='repo',
                                      instance=GITHUB_INSTANCE)
        repo2 = GHRepo.objects.create(owner='owner2', repo='repo',
                                      instance=GITHUB_INSTANCE)

        enrich1 = GHIEnrich.objects.create(repo=repo1)
        enrich2 = GHIEnrich.objects.create(repo=repo2)

        enrichs = GHIEnrich.objects.all()
        self.assertEqual(len(enrichs), 2)
        self.assertIn(enrich1, enrichs)
        self.assertIn(enrich2, enrichs)


class TestMethods(TestCase):

    def setUp(self):
        self.repo1 = GHRepo.objects.create(owner='owner1', repo='repo',
                                           instance=GITHUB_INSTANCE)
        self.user1 = User.objects.create(username='A')
        self.user2 = User.objects.create(username='B')
        self.enrich1 = GHIEnrich.objects.create(repo=self.repo1, user=self.user1)
        self.enrich2 = GHIEnrich.objects.create(repo=self.repo1, user=self.user2)
        self.worker1 = Worker.objects.create()
        self.worker2 = Worker.objects.create()

    def test_create_previous(self):
        """Test create previous method"""
        prev = self.enrich1.create_previous()
        self.assertEqual(prev[0].repo, self.enrich1.repo)
        self.assertEqual(prev[0].user, self.enrich1.user)

    def test_create_job(self):
        """Test create GitHub.GHIEnrich job"""
        job = self.enrich1.create_job(self.worker1)
        self.assertEqual(job.worker, self.worker1)
        self.assertEqual(self.enrich1.job, job)

    def test_create_job2(self):
        """Test create GitHub.GHIEnrich job with existing job"""
        job1 = self.enrich1.create_job(self.worker1)
        job2 = self.enrich1.create_job(self.worker1)
        self.assertEqual(job1.worker, self.worker1)
        self.assertEqual(job2, None)

    def test_running_job(self):
        """Test find a job for enrich1 that doesn't exist"""
        job = self.enrich1.running_job()
        self.assertEqual(job, None)

    def test_running_job2(self):
        """Test find a job for enrich2 that exists"""
        new_job = Job.objects.create()
        self.enrich1.job = new_job
        self.enrich1.save()
        job = self.enrich2.running_job()
        self.assertEqual(job, new_job)


class TestSelectableIntentions(TestCase):
    def setUp(self):
        """
        User 1: 0 intentions
        User 2: 1 intention ready
        User 3: 2 intention ready
        User 4: 1 intention ready, 1 intention running
        User 5: 1 intention ready, 1 intention with Job
        :return:
        """
        self.repo1 = GHRepo.objects.create(owner='owner1', repo='repo1',
                                           instance=GITHUB_INSTANCE)
        self.repo2 = GHRepo.objects.create(owner='owner2', repo='repo2',
                                           instance=GITHUB_INSTANCE)

        self.user1 = User.objects.create(username='1')

        self.user2 = User.objects.create(username='2')
        self.ienrich_U2_1 = GHIEnrich.objects.create(repo=self.repo1, user=self.user2,
                                                     status=Intention.Status.READY)
        self.user3 = User.objects.create(username='3')
        self.ienrich_U3_1 = GHIEnrich.objects.create(repo=self.repo1, user=self.user3,
                                                     status=Intention.Status.READY)
        self.ienrich_U3_2 = GHIEnrich.objects.create(repo=self.repo2, user=self.user3,
                                                     status=Intention.Status.READY)
        self.user4 = User.objects.create(username='4')
        self.ienrich_U4_1 = GHIEnrich.objects.create(repo=self.repo1, user=self.user4,
                                                     status=Intention.Status.READY)
        self.ienrich_U4_2 = GHIEnrich.objects.create(repo=self.repo2, user=self.user4,
                                                     status=Intention.Status.WORKING)

        self.user5 = User.objects.create(username='5')
        self.ienrich_U5_1 = GHIEnrich.objects.create(repo=self.repo1, user=self.user5,
                                                     status=Intention.Status.READY)
        self.job_U5 = Job.objects.create()
        self.ienrich_U5_2 = GHIEnrich.objects.create(repo=self.repo2, user=self.user5,
                                                     status=Intention.Status.READY,
                                                     job=self.job_U5)

    def test_user_1(self):
        """Test not available intentions"""
        intentions = GHIEnrich.objects.selectable_intentions(user=self.user1)
        self.assertEqual(len(intentions), 0)

    def test_user_2(self):
        """Test one intention ready"""
        intentions = GHIEnrich.objects.selectable_intentions(user=self.user2)
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], self.ienrich_U2_1)

    def test_user_3(self):
        """Test two intentions ready, get 1"""
        intentions = GHIEnrich.objects.selectable_intentions(user=self.user3, max=1)
        self.assertEqual(len(intentions), 1)
        self.assertIn(intentions[0], [self.ienrich_U3_1, self.ienrich_U3_2])

    def test_user_3b(self):
        """Test two intentions ready, get 2"""
        intentions = GHIEnrich.objects.selectable_intentions(user=self.user3, max=2)
        self.assertEqual(len(intentions), 2)
        self.assertListEqual(list(intentions), [self.ienrich_U3_1, self.ienrich_U3_2])

    def test_user_4(self):
        """Test one running one ready"""
        intentions = GHIEnrich.objects.selectable_intentions(user=self.user4, max=2)
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], self.ienrich_U4_1)

    def test_user_5(self):
        """Test one ready and one ready with job"""
        intentions = GHIEnrich.objects.selectable_intentions(user=self.user5, max=2)
        self.assertEqual(len(intentions), 1)
