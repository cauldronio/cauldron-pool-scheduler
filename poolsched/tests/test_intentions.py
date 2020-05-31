from django.test import TestCase

from ..models import Intention, User, IGitHubRaw, IGitHubEnriched


class TestIntentions(TestCase):

    def setUp(self):
        """Define some useful constants"""

        self.intention1 = Intention(
            job=None, user=None,
            status=Intention.Status.WAITING
        )
        self.intention2 = Intention(
            job=None, user=None,
            status=Intention.Status.WAITING
        )
        # Scale for random tests (no_tests = scale*10)
        self.scale = 100

    def test_create(self):
        """Insert a single Intention into the database"""

        intention = self.intention1
        intention.save()
        intentions = Intention.objects.all()
        self.assertEqual(len(intentions), 1)
        self.assertEqual(intentions[0], self.intention1)

    def test_create2(self):
        """Insert two Intentions into the database"""

        self.intention1.save()
        self.intention2.save()
        intentions = Intention.objects.all()
        self.assertEqual(len(intentions), 2)
        self.assertEqual(intentions[0], self.intention1)
        self.assertEqual(intentions[1], self.intention2)

    def test_default(self):
        """Create Intentions with default parameters"""

        intention = Intention()
        self.assertEqual(intention.job, None)
        self.assertEqual(intention.user, None)
        self.assertEqual(intention.status, Intention.Status.WAITING)

    def test_previous(self):
        """Create Intentions with default parameters"""

        intention1 = self.intention1
        intention1.save()
        intention2 = self.intention2
        intention2.save()
        intention1.previous.add(intention2)

    def test_previous_create(self):
        """Previous intentions (simple)"""

        expected = {1: [2], 2: []}
        intention1 = self.intention1
        intention1.save()
        intention2 = intention1.previous.create()
        intention2.save()
        intentions = Intention.objects.all()
        for intention in intentions:
            for previous in intention.previous.all():
                self.assertIn(previous.id, expected[intention.id])

    def test_previous_create2(self):
        """Previous intentions (several)"""

        expected = {1: [2, 3], 2: []}
        intention1 = self.intention1
        intention1.save()
        intention2 = intention1.previous.create()
        intention2.save()
        intention3 = intention1.previous.create()
        intention3.save()
        intentions = Intention.objects.all()
        for intention in intentions:
            for previous in intention.previous.all():
                self.assertIn(previous.id, expected[intention.id])
        intentions = Intention.objects.all()
        for intention in intentions:
            for previous in intention.previous.all():
                self.assertIn(previous.id, expected[intention.id])

    def test_user(self):
        """Direct and reverse relationship with users"""

        # Create a user, add it to two intentions
        user = User.objects.create(username='A')
        self.intention1.user = user
        self.intention1.save()
        self.intention2.user = user
        self.intention2.save()
        # Check user for intentions
        self.assertEqual(self.intention1.user, user)
        self.assertEqual(self.intention2.user, user)
        # Check intentions for user
        self.assertEqual(user.intention_set.get(pk=self.intention1.pk),
                         self.intention1)
        self.assertEqual(user.intention_set.get(pk=self.intention2.pk),
                         self.intention2)


class TestCast(TestCase):

    def test_basic(self):
        """Test casting an intention"""

        user = User.objects.create(username='A')
        intention = Intention.objects.create(
            user=user,
            status=Intention.Status.READY)
        casted = intention.cast()
        self.assertEqual(casted.__class__, Intention)

    def test_sublist(self):
        """Test the value of the list of subclasses.

        We're importing models, so we should have all subclasses
        pulled in by models.
        """

        expected = ['igithubraw', 'igithubenriched', 'igitlabraw',
            'igitraw', 'igitenriched'].sort()
        self.assertEqual(Intention._subfields().sort(), expected)

class TestQueryIntentions(TestCase):
    """Tests methods in the manager returning querysets with intentions"""

    @classmethod
    def setUpTestData(cls):
        """Populate the database"""
        cls.users = [User.objects.create(username=username)
                 for username in ['A', 'B', 'C', 'D', 'E']]
        for user in cls.users:
            intention = IGitHubRaw.objects.create (
                user=user,
                status=Intention.Status.DONE)
            intention = IGitHubEnriched.objects.create(
                user=user,
                status=Intention.Status.READY)
        for user in cls.users[:3]:
            intention = IGitHubRaw.objects.create (
                user=user,
                status=Intention.Status.READY)
            intention = IGitHubEnriched.objects.create(
                user=user,
                status=Intention.Status.WAITING)
        for user in cls.users[:1]:
            intention = IGitHubRaw.objects.create (
                user=user,
                status=Intention.Status.READY)
