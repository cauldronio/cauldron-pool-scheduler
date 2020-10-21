from django.contrib import admin
from .models import git, github, gitlab, meetup
from .models import Worker, Job, Intention, ArchJob


@admin.register(git.IGitRaw, git.IGitEnrich,
                github.IGHRaw, github.IGHEnrich,
                gitlab.IGLRaw, gitlab.IGLEnrich,
                meetup.IMeetupRaw, meetup.IMeetupEnrich)
class IntentionAdmin(admin.ModelAdmin):
    list_display = ('job', 'user', 'created')


@admin.register(git.IGitRawArchived, git.IGitEnrichArchived,
                github.IGHRawArchived, github.IGHEnrichArchived,
                gitlab.IGLRawArchived, gitlab.IGLEnrichArchived,
                meetup.IMeetupRawArchived, meetup.IMeetupEnrichArchived)
class ArchIntentionAdmin(admin.ModelAdmin):
    list_display = ('user', 'created', 'completed', 'status', 'arch_job')


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('created', 'worker', 'logs')


# Common
admin.site.register(Worker)
admin.site.register(Intention)
admin.site.register(ArchJob)

# Git
admin.site.register(git.GitRepo)

# GitHub
admin.site.register(github.GHRepo)
admin.site.register(github.GHToken)

# GitLab
admin.site.register(gitlab.GLRepo)
admin.site.register(gitlab.GLToken)

# Meetup
admin.site.register(meetup.MeetupRepo)
admin.site.register(meetup.MeetupToken)
