"""
API for Django server to create new intentions
"""

import logging

from django.contrib.auth import get_user_model

from poolsched.models.targets.github import IGHRaw, IGHEnrich, GHToken, GHRepo, GHInstance
from poolsched.models.targets.gitlab import IGLRaw, IGLEnrich, GLToken, GLRepo, GLInstance
from poolsched.models.targets.git import IGitRaw, IGitEnrich, GitRepo
from poolsched.models.targets.meetup import IMeetupRaw, IMeetupEnrich


User = get_user_model()

logger = logging.getLogger(__name__)


def analyze_gh_repo(user, owner, repo):
    """owner, repo"""
    # TODO: Define instance
    if user.ghtokens.count() < 1:
        return None
    instance = GHInstance.objects.get(name='GitHub')
    gh_repo, _ = GHRepo.objects.get_or_create(owner=owner, repo=repo, instance=instance)
    raw, _ = IGHRaw.objects.get_or_create(user=user, repo=gh_repo)
    enrich, _ = IGHEnrich.objects.get_or_create(user=user, repo=gh_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def analyze_gh_repo_obj(user, gh_repo):
    if user.ghtokens.count() < 1:
        return None
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
    return git_repo


def analyze_git_repo_obj(user, git_repo):
    """owner, repo, instance"""
    raw, _ = IGitRaw.objects.get_or_create(user=user, repo=git_repo)
    enrich, _ = IGitEnrich.objects.get_or_create(user=user, repo=git_repo)
    enrich.previous.add(raw)
    return git_repo


def analyze_gl_repo(user, owner, repo):
    """owner, repo"""
    # TODO: Define instance
    if user.gltokens.count() < 1:
        return None
    instance = GLInstance.objects.get(name='GitLab')
    gl_repo, _ = GLRepo.objects.get_or_create(owner=owner, repo=repo, instance=instance)
    raw, _ = IGLRaw.objects.get_or_create(user=user, repo=gl_repo)
    enrich, _ = IGLEnrich.objects.get_or_create(user=user, repo=gl_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def analyze_gl_repo_obj(user, gl_repo):
    if user.gltokens.count() < 1:
        return None
    raw, _ = IGLRaw.objects.get_or_create(user=user, repo=gl_repo)
    enrich, _ = IGLEnrich.objects.get_or_create(user=user, repo=gl_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def analyze_meetup_repo_obj(user, meetup_repo):
    if user.meetuptokens.count() < 1:
        return None
    raw, _ = IMeetupRaw.objects.get_or_create(user=user, repo=meetup_repo)
    enrich, _ = IMeetupEnrich.objects.get_or_create(user=user, repo=meetup_repo)
    enrich.previous.add(raw)
    return {'ok': 'tasks created'}


def create_user(name):
    user = User.objects.create(username=name)
    GHToken.objects.create(token='', user=user)
    GLToken.objects.create(token='', user=user)
    return user
