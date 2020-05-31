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

class TestBasic(TestCase):
    """Test with several jobs (creation, deletion, find from worker...)"""

    def test_workers(self):
        """Create and delter several jobs for a worker"""

        worker = Worker.objects.create()
        for round in range(10):
            job = Job(worker=worker)
            job.save()
            jobs = Job.objects.all()
            self.assertEqual(len(jobs), round+1)
            self.assertEqual(jobs[round], job)
            the_job = worker.job_set.get(id=job.id)
            self.assertEqual(the_job, job)

        for round in range(10,0,-1):
            job = Job.objects.filter(id=round)
            job.delete()
            jobs = Job.objects.all()
            self.assertEqual(len(jobs), round-1)

        self.assertEqual(Worker.objects.all()[0], worker)
