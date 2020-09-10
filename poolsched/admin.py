from django.contrib import admin
from .models import git, github, gitlab
from .models import Worker, Job, Intention, ArchJob


admin.site.register(Worker)
admin.site.register(Intention)
admin.site.register(Job)
admin.site.register(ArchJob)

# Git
admin.site.register(git.GitRepo)
admin.site.register(git.IGitRaw)
admin.site.register(git.IGitEnrich)
admin.site.register(git.IGitRawArchived)
admin.site.register(git.IGitEnrichArchived)

# GitHub
admin.site.register(github.GHRepo)
admin.site.register(github.IGHRaw)
admin.site.register(github.IGHEnrich)
admin.site.register(github.IGHRawArchived)
admin.site.register(github.IGHEnrichArchived)

# GitLab
admin.site.register(gitlab.GLRepo)
admin.site.register(gitlab.IGLRaw)
admin.site.register(gitlab.IGLEnrich)
admin.site.register(gitlab.IGLRawArchived)
admin.site.register(gitlab.IGLEnrichArchived)
