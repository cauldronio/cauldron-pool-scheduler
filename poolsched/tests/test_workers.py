from django.test import TestCase

from ..models import Worker

class TestBasic(TestCase):

    def test_create(self):

        worker = Worker.objects.create(status=Worker.Status.UP)
        the_worker = Worker.objects.first()
        self.assertEqual(the_worker, worker)

    def test_default(self):

        worker = Worker.objects.create()
        the_worker = Worker.objects.first()
        self.assertEqual(the_worker.status, Worker.Status.DOWN)

        the_worker.status = Worker.Status.UP
        the_worker.save()
        count = Worker.objects.count()
        self.assertEqual(count, 1)

        the_worker = Worker.objects.get(status=Worker.Status.UP)
        self.assertEqual(the_worker, worker)