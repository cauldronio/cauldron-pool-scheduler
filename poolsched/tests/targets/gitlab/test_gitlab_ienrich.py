import logging

from django.test import TestCase
from django.contrib.auth import get_user_model

from ....models import Job, Worker
from ....models.targets.gitlab import GLInstance, GLRepo, IGLEnrich

User = get_user_model()

GITLAB_INSTANCE = GLInstance.objects.get(name='GitLab')

logger = logging.getLogger(__name__)


class TestBasicCreate(TestCase):

    def test_create(self):
        """Insert a single IEnrich into the database"""
        repo = GLRepo.objects.create(owner='owner', repo='repo',
                                     instance=GITLAB_INSTANCE)
        enrich = IGLEnrich.objects.create(repo=repo)
        found = IGLEnrich.objects.get(repo=repo)
        self.assertEqual(enrich, found)

    def test_create_2(self):
        """Insert two IEnrich into the database"""
        repo1 = GLRepo.objects.create(owner='owner1', repo='repo',
                                      instance=GITLAB_INSTANCE)
        repo2 = GLRepo.objects.create(owner='owner2', repo='repo',
                                      instance=GITLAB_INSTANCE)

        enrich1 = IGLEnrich.objects.create(repo=repo1)
        enrich2 = IGLEnrich.objects.create(repo=repo2)

        enrichs = IGLEnrich.objects.all()
        self.assertEqual(len(enrichs), 2)
        self.assertIn(enrich1, enrichs)
        self.assertIn(enrich2, enrichs)


class TestMethods(TestCase):

    def setUp(self):
        self.repo1 = GLRepo.objects.create(owner='owner1', repo='repo',
                                           instance=GITLAB_INSTANCE)
        self.user1 = User.objects.create(username='A')
        self.user2 = User.objects.create(username='B')
        self.enrich1 = IGLEnrich.objects.create(repo=self.repo1, user=self.user1)
        self.enrich2 = IGLEnrich.objects.create(repo=self.repo1, user=self.user2)
        self.worker1 = Worker.objects.create()
        self.worker2 = Worker.objects.create()

    def test_create_previous(self):
        """Test create previous method"""
        prev = self.enrich1.create_previous()
        self.assertEqual(prev[0].repo, self.enrich1.repo)
        self.assertEqual(prev[0].user, self.enrich1.user)

    def test_create_job(self):
        """Test create GitLab.IGLEnrich job"""
        job = self.enrich1.create_job(self.worker1)
        self.assertEqual(job.worker, self.worker1)
        self.assertEqual(self.enrich1.job, job)

    def test_create_job2(self):
        """Test create GitLab.IGLEnrich job with existing job"""
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
        self.repo1 = GLRepo.objects.create(owner='owner1', repo='repo1',
                                           instance=GITLAB_INSTANCE)
        self.repo2 = GLRepo.objects.create(owner='owner2', repo='repo2',
                                           instance=GITLAB_INSTANCE)

        self.user1 = User.objects.create(username='1')

        self.user2 = User.objects.create(username='2')
        self.ienrich_U2_1 = IGLEnrich.objects.create(repo=self.repo1, user=self.user2)

        self.user3 = User.objects.create(username='3')
        self.ienrich_U3_1 = IGLEnrich.objects.create(repo=self.repo1, user=self.user3)
        self.ienrich_U3_2 = IGLEnrich.objects.create(repo=self.repo2, user=self.user3)

        self.user5 = User.objects.create(username='5')
        self.ienrich_U5_1 = IGLEnrich.objects.create(repo=self.repo1, user=self.user5)
        self.job_U5 = Job.objects.create()
        self.ienrich_U5_2 = IGLEnrich.objects.create(repo=self.repo2, user=self.user5,
                                                     job=self.job_U5)

    def test_user_1(self):
        """Test not available intentions"""
        intentions = IGLEnrich.objects.selectable_intentions(user=self.user1)
        self.assertEqual(len(intentions), 0)

    def test_user_2(self):
        """Test one intention ready"""
        intentions = IGLEnrich.objects.selectable_intentions(user=self.user2)
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], self.ienrich_U2_1)

    def test_user_3(self):
        """Test two intentions ready, get 1"""
        intentions = IGLEnrich.objects.selectable_intentions(user=self.user3, max=1)
        self.assertEqual(len(intentions), 1)
        self.assertIn(intentions[0], [self.ienrich_U3_1, self.ienrich_U3_2])

    def test_user_3b(self):
        """Test two intentions ready, get 2"""
        intentions = IGLEnrich.objects.selectable_intentions(user=self.user3, max=2)
        self.assertEqual(len(intentions), 2)
        self.assertListEqual(list(intentions), [self.ienrich_U3_1, self.ienrich_U3_2])

    def test_user_5(self):
        """Test one ready and one ready with job"""
        intentions = IGLEnrich.objects.selectable_intentions(user=self.user5, max=2)
        self.assertEqual(len(intentions), 1)
