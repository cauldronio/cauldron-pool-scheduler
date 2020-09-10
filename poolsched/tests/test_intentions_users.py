from django.test import TestCase
from django.contrib.auth import get_user_model

from ..models import Intention

User = get_user_model()


class TestBasic(TestCase):

    def test_user(self):
        """Direct and reverse relationship of intentions with users"""

        # Create a user, add it to two intentions
        user = User.objects.create(username='A')
        intention1 = Intention()
        intention2 = Intention()
        intention1.user = user
        intention1.save()
        intention2.user = user
        intention2.save()
        # Check user for intentions
        self.assertEqual(intention1.user, user)
        self.assertEqual(intention2.user, user)
        # Check intentions for user
        self.assertEqual(user.intention_set.get(pk=intention1.pk),
                         intention1)
        self.assertEqual(user.intention_set.get(pk=intention2.pk),
                         intention2)
