"""
API for Django server to create new intentions
"""

import logging

from poolsched.models.targets.github import IGHRaw, IGHEnrich, GHToken, GHRepo, GHInstance
from poolsched.models.targets.git import IGitRaw, IGitEnrich, GitRepo
from poolsched.models import User

logger = logging.getLogger(__name__)


def analyze_gh_repo(user, owner, repo):
    """owner, repo, instance"""
    if user.ghtokens.count() < 1:
        return {'error': 'you need a token'}
    instance = GHInstance.objects.get(name='GitHub')
    gh_repo, _ = GHRepo.objects.get_or_create(owner=owner, repo=repo, instance=instance)
    raw, _ = IGHRaw.objects.get_or_create(user=user, repo=gh_repo)
    enrich, _ = IGHEnrich.objects.get_or_create(user=user, repo=gh_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def analyze_git_repo(user, url):
    """owner, repo, instance"""
    git_repo, _ = GitRepo.objects.get_or_create(url=url)
    raw, _ = IGitRaw.objects.get_or_create(user=user, repo=git_repo)
    enrich, _ = IGitEnrich.objects.get_or_create(user=user, repo=git_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def create_user(name):
    user = User.objects.create(username=name)
    GHToken.objects.create(token='', user=user)
    return user
