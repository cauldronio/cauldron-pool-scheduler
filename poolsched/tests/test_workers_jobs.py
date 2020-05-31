from django.test import TestCase

from ..models import Worker, Job

class TestBasic(TestCase):
    """Test basic relatinships from jobs to workers, and viceversa"""

    @classmethod
    def setUpTestData(cls):
        cls.worker = Worker.objects.create(status=Worker.Status.UP)
        cls.job = Job.objects.create(status=Job.Status.WORKING,
                                     worker=cls.worker)

    def test_job(self):
        """Find the job created, from the worker"""

        self.assertEqual(self.worker.job_set.first(), self.job)

        job = Job.objects.get(worker=self.worker)
        self.assertEqual(job, self.job)

    def test_worker(self):
        """Find the worker, from the job"""

        self.assertEqual(self.job.worker, self.worker)

        worker = Worker.objects.get(job=self.job)
        self.assertEqual(worker, self.worker)
