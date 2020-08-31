"""
API for Django server to create new intentions
"""

import logging
from time import sleep

from django.forms.models import model_to_dict

from .models import Worker, Intention, User, Job, ArchJob
from .models.targets.github import IGHRaw, IGHEnrich
from .models.targets.gitlab import IGLRaw, IGLEnrich
from .models.targets.git import IGitRaw
from .models.targets.git import IGitEnrich
from .models.targets.github import GHRepo, GHInstance

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


def create_gh_repo_intention(user, owner, repo):
    """owner, repo, instance"""
    if user.ghtokens.count() < 1:
        return {'error': 'you need a token'}
    instance = GHInstance.objects.get(name='GitHub')
    gh_repo = GHRepo.objects.get_or_create(owner, repo, instance)
    raw = IGHRaw.objects.get_or_create(user=user, repo=gh_repo)
    enrich = IGHEnrich.objects.get_or_create(user=user, repo=gh_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}
