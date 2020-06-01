from django.test import TestCase
from django.db import IntegrityError

from ...models.targets.github import Instance

GITHUB_INSTANCE = Instance.objects.get(name='GitHub')

class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests"""
        instance = Instance.objects.get(name='GitHub')
        self.assertEqual(instance.endpoint, GITHUB_INSTANCE.endpoint)

    def test_add_one(self):
        """Add a new instance"""
        instance = Instance.objects.create(name='GitHub A',
                                           endpoint='https://api.gha.com')

        self.assertEqual(Instance.objects.count(), 2)
        found = Instance.objects.get(name='GitHub A')
        self.assertEqual(found, instance)

    def test_unique(self):
        """Instance name is unique"""

        instance = Instance.objects.create(name='GitHub A',
                                           endpoint='https://api.gha.com')
        with self.assertRaises(IntegrityError):
            instance = Instance.objects.create(name='GitHub A',
                                               endpoint='https://api.gha.com')
