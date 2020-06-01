from django.test import TestCase
from django.db import IntegrityError

from ...models.targets.github import Instance, Repo

GITHUB_INSTANCE = Instance.objects.get(name='GitHub')

class TestBasic(TestCase):

    def test_basic(self):
        """Basic tests."""

        repo = Repo.objects.create(owner='owner', repo='repo',
                                   instance=GITHUB_INSTANCE)

        found = Repo.objects.get(owner='owner', repo='repo')
        self.assertEqual(found, repo)

    def test_unique(self):
        """Pair (owner, repo) are unique for the same instance."""

        Repo.objects.create(owner='owner', repo='repo',
                            instance=GITHUB_INSTANCE)
        with self.assertRaises(IntegrityError):
            Repo.objects.create(owner='owner', repo='repo',
                                instance=GITHUB_INSTANCE)
