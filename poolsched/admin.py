from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from .models import Worker, Job, Intention, ArchJob, ArchivedIntention, Log, ScheduledIntention


def user_name(obj):
    try:
        return obj.user.first_name
    except AttributeError:
        return None


def previous_count(obj):
    return obj.previous.count()


class RunningInAWorker(admin.SimpleListFilter):
    title = _('running in a worker')

    # Parameter for the filter that will be used in the URL query.
    parameter_name = 'in_worker'

    def lookups(self, request, model_admin):
        """
        Returns a list of tuples. The first element in each
        tuple is the coded value for the option that will
        appear in the URL query. The second element is the
        human-readable name for the option that will appear
        in the right sidebar.
        """
        return (
            ('Yes', _('Running in a worker')),
            ('No', _('Not running in a worker')),
        )

    def queryset(self, request, queryset):
        """
        Returns the filtered queryset based on the value
        provided in the query string and retrievable via
        `self.value()`.
        """
        # Check if there is a Job with a worker and compare with the filter.
        if self.value() == 'Yes':
            return queryset.filter(job__isnull=False, job__worker__isnull=False)
        else:
            return queryset


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'worker', 'logs_file')
    search_fields = ('id',)
    list_filter = ('created',)
    ordering = ('created', )

    def logs_file(self, obj):
        try:
            return obj.logs.location
        except AttributeError:
            return None


@admin.register(ArchJob)
class ArchJobAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'archived', 'worker', 'worker_machine', 'logs_file')
    search_fields = ('id',)
    list_filter = ('created', 'archived')
    ordering = ('archived', )

    def worker_machine(self, obj):
        try:
            return obj.worker.machine
        except AttributeError:
            return None

    def logs_file(self, obj):
        try:
            return obj.logs.location
        except AttributeError:
            return None


@admin.register(Intention)
class IntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'started', 'job_id', 'worker', user_name, previous_count, 'child', 'logs')
    search_fields = ('id', 'user__first_name')
    list_filter = ('created', RunningInAWorker)
    ordering = ('created', )

    def started(self, obj):
        try:
            return obj.job.created
        except AttributeError:
            return None

    def job_id(self, obj):
        try:
            return obj.job.id
        except AttributeError:
            return None

    def child(self, obj):
        try:
            child = obj.cast()
            return f"{child._meta.model_name}({child.id})"
        except AttributeError:
            return None

    def worker(self, obj):
        try:
            return obj.job.worker.machine
        except AttributeError:
            return None

    def logs(self, obj):
        try:
            url = "/logs/" + str(obj.job.id)
            return format_html("<a href='{url}'>Show</a>", url=url)
        except AttributeError:
            return None


@admin.register(ArchivedIntention)
class ArchivedIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'created', 'started', 'completed', user_name, 'status', 'worker', 'logs', 'child')
    search_fields = ('id', 'user__first_name', 'status')
    list_filter = ('status', 'created', 'completed')
    ordering = ('-completed', )

    def started(self, obj):
        try:
            return obj.arch_job.created
        except AttributeError:
            return None

    def worker(self, obj):
        try:
            return obj.arch_job.worker.machine
        except AttributeError:
            return None

    def logs(self, obj):
        try:
            job_id = obj.arch_job.logs.location.split('-')[1].split('.')[0]
            url = "/logs/" + str(job_id)
            return format_html("<a href='{url}'>Show</a>", url=url)
        except AttributeError:
            return None

    def child(self, obj):
        for name in dir(obj):
            try:
                attr = getattr(obj, name)
                if isinstance(attr, obj.__class__):
                    url = "/admin/{}/{}/?q={}".format(attr._meta.app_label, attr._meta.model_name, attr.id)
                    return format_html("<a href='{url}'>{name}</a>", url=url, name=attr._meta.model_name)
            except:
                pass
        return obj

@admin.register(Worker)
class WorkerAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'machine', 'running_job')
    search_fields = ('id', 'status')
    list_filter = ('status', 'machine')
    ordering = ('-id', )

    def running_job(self, obj):
        return obj.job_set.first()


@admin.register(Log)
class Log(admin.ModelAdmin):
    list_display = ('id', 'location')
    search_fields = ('id', 'location')


@admin.register(ScheduledIntention)
class ScheduledIntentionAdmin(admin.ModelAdmin):
    list_display = ('id', 'intention_class', 'kwargs', user_name, 'scheduled_at', 'depends_on', 'repeat', 'worker_name')
    search_fields = ('id', 'intention_class', 'user__first_name')
    list_filter = ('intention_class', 'scheduled_at')
    ordering = ('-scheduled_at',)

    def worker_name(self, obj):
        try:
            return obj.worker.machine
        except AttributeError:
            return None
