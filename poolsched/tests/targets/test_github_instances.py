from django.test import TestCase

from ...models.targets.github import Instance

GITHUB_INSTANCE = Instance.objects.get(name='GitHub')

class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests"""
        instance = Instance.objects.get(name='GitHub')
        self.assertEqual(instance.endpoint, GITHUB_INSTANCE.endpoint)

    def add_one(self):
        """Add a new instance"""
        instance = Instance.objects.create(name='GitHub A',
                                           endpoint='https://api.gha.com')

        self.assertEqual(Instance.objects.count(), 2)
        found = Instance.objects.get(name='GitHub A')
        self.assertEqual(found, instance)