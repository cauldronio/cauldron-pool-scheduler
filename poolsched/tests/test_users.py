from django.test import TestCase

from ..models import User, Intention


class TestUsers(TestCase):

    def test_create(self):
        """Insert a single user into the database"""

        user = User(username='pp')
        user.save()
        users = User.objects.all()
        self.assertEqual(len(users), 1)
        self.assertEqual(users[0], user)


class TestRandomUserReady(TestCase):
    """Test random_user_ready"""

    @classmethod
    def setUpTestData(cls):
        """Populate the database"""

        # Scale for random tests (no_tests = scale*10)
        cls.scale = 100
        user1 = User.objects.create(username='A')
        user2 = User.objects.create(username='B')
        user3 = User.objects.create(username='C')
        user4 = User.objects.create(username='D')
        user5 = User.objects.create(username='E')
        user6 = User.objects.create(username='F')
        # For each user: [user, #intentions ready, #intentions working]
        users = [[user1, 10, 2], [user2, 20, 10],
                 [user3, 30, 3], [user4, 40, 40],
                 [user5, 0, 20], [user6, 0, 120]]
        for user in users:
            for intention in range(0, user[1]):
                Intention.objects.create(user=user[0],
                                         status=Intention.Status.READY)
            for intention in range(0, user[2]):
                Intention.objects.create(user=user[0],
                                         status=Intention.Status.WORKING)

    def test_random_user_id_ready(self):
        """Some intentions from the random user"""

        occurrences = [0, 0, 0, 0]
        for cont in range(0, 10 * self.scale):
            [user] = User.objects.random_user_ready()
            occurrences[user.id - 1] += 1
        for occurrence in occurrences:
            if occurrence > 3 * self.scale:
                random = False
            elif occurrence < 2 * self.scale:
                random = False
            else:
                random = True
            self.assertTrue(random, msg="Random is not so random")

    def test_random_user_id_ready_several(self):
        """Some intentions from the random user"""

        occurrences = [0, 0, 0, 0]
        for cont in range(0, 10 * self.scale):
            [u1, u2] = User.objects.random_user_ready(max=2)
            for id in [u1.id, u2.id]:
                occurrences[id - 1] += 1
        for occurrence in occurrences:
            if occurrence > 6 * self.scale:
                random = False
            elif occurrence < 4 * self.scale:
                random = False
            else:
                random = True
            self.assertTrue(random, msg="Random is not so random: " + str(occurrences))

        occurrences = [0, 0, 0, 0]
        for cont in range(0, 10 * self.scale):
            [u1, u2, u3] = User.objects.random_user_ready(max=3)
            for id in [u1.id, u2.id, u3.id]:
                occurrences[id - 1] += 1
        for occurrence in occurrences:
            if occurrence > 9 * self.scale:
                random = False
            elif occurrence < 6 * self.scale:
                random = False
            else:
                random = True
            self.assertTrue(random, msg="Random is not so random: " + str(occurrences))
