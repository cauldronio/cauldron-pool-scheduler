from django.test import TestCase

from ..models.intentions import Intention


class TestBasic(TestCase):

    def setUp(self):
        """Define some useful constants"""

        self.intention1 = Intention(
            job=None, user=None
        )
        self.intention2 = Intention(
            job=None, user=None
        )

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

    def test_previous(self):
        """Create intention with previous intention"""

        intention1 = self.intention1
        intention1.save()
        intention2 = self.intention2
        intention2.save()
        intention1.previous.add(intention2)

        previous = intention1.previous.get()
        self.assertEqual(previous, intention2)

        intention = Intention.objects.get(previous=intention2)
        self.assertEqual(intention, intention1)

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


class TestDeepPrevious(TestCase):

    def test_create_previous(self):
        """Give a try to _create_previous.

        Since it is returning [], no new intention should be created."""

        intention = Intention.objects.create()
        intention._create_previous()
        self.assertEqual(Intention.objects.count(), 1)

    def test_deep_previous(self):
        """Give a try to deep_previous.

        Since _create_previous is returning [], no new intentions
        should be created."""

        intention = Intention.objects.create()
        intention.deep_previous()
        self.assertEqual(Intention.objects.count(), 1)


class TestCast(TestCase):
    """Test _subfields and _subfields_list"""

    @classmethod
    def setUpTestData(cls):
        cls.subfields = ['ighraw', 'ighenrich',
                         'igitraw', 'igitenrich',
                         'iglraw', 'iglenrich',
                         'imeetupraw', 'imeetupenrich']

    def test_subfields(self):
        """Test _subfields()"""

        self.assertCountEqual(Intention._subfields(), self.subfields)

    def test_subfields_list(self):
        """Test _subfields() and _subfields_list"""

        Intention._subfields()
        self.assertCountEqual(Intention._subfields_list, self.subfields)

    def test_cast(self):
        """Test cast"""

        intention = Intention()
        casted = intention.cast()
        self.assertEqual(casted, intention)
