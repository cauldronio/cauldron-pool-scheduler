from django.test import TestCase

from ..models import Job


class TestJobs(TestCase):

    def test_create(self):
        job = Job()
        job.save()
        jobs = Job.objects.all()
        self.assertEqual(len(jobs), 1)
        self.assertEqual(jobs[0], job)

    def test_create_n(self):
        for round in range(10):
            job = Job()
            job.save()
            jobs = Job.objects.all()
            self.assertEqual(len(jobs), round + 1)
            self.assertEqual(jobs[round], job)
