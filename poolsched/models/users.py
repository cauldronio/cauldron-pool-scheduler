from random import sample

from django.contrib.auth.models import AbstractUser

from django.db import models

from .intentions import Intention


class UserManager(models.Manager):

    def random_user_ready(self, max=1):
        """Get random user ids, for users with ready Intentions.

        Ready intentions are those that are in READY status (do not have
        pending previous intentions), and still don't have a job.

        :param max: maximum number of users
        :returns:   list of User objects
        """

        q = User.objects.filter(intention__status=Intention.Status.READY,
                                intention__job=None).distinct()
        count = q.count()
        users = [q[i] for i in sample(range(count), min(max, count))]
        return users


class User(AbstractUser):
    objects = UserManager()
