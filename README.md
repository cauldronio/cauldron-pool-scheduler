# Pool Scheduling

Some early tries towards a simple Python pool scheduler for Cauldron 

## Main elements

* Intentions: Intentions to be acomplished by the workers, at some point.
Intentions are defined as "goals" (for example, having a raw index produced
for a given repository). To acomplish an intention, maybe other intentions
have to be acomplished previously (for example, for having the enriched
index for a repository, you need the raw repository for that repository first).
Intentions are ordered by users.

* Jobs: Jobs are produced to acomplish intentions. Workers will work
with jobs, and a job will be assigned to a worker to run.
A certain job can be used to acomplish more than one intention.
For exmple, to fulfill two different intentions of producing the raw index
for a repository, ordered by two different users, a single job could be used.
For producing their output, jobs may need some resources
(such as an API token, etc.). A job serving several intentions
could use resources available to all the users ordering those intentions.
Jobs are in a common pool, and allocated to a worker when they can be run in it.
During their lifetime, jobs may be working (active in the worker),
or waiting (because they cannot be working now, for lack of some resource).

* Users: Extensions of Django users. Users will be linked to intentions:
the intentions they ordered.

## Jobs lifecycle

Workers are always hungry for jobs. Whenever they become idle
(no job ready to run), they ask for new jobs.
The process is as follows:

* Some worker is idle (no job to run), so it asks the scheduler
for a new job.

* The scheduler checks if there is some job,
ready to run but waiting, and if so, it is returned to the worker as
a job to be run.

* Else, to produce a new job, the scheduler selects an intention with no job,
with all previous intentions done, and with enough resources to run.

* If there is already a job (for any worker) who could acomplish this
intention (for example, I asked for producing the enriched index
for a repository, and there is already a job doing that), the
intention is assigned to that job, new resources are allocated to
the job, if needed, and we come back to the previous step (a new
intention is selected).

* If there is no job who could acomplish this intention,
a new job is produced, and assigned to the selected intention.
Resources are allocated to it, and the worker who asked for a new job
is assigned to it.

* The job is returned to the worker.

When a job is done, workers try to run some other job assigned to them.
If they don't have a job ready to run, they ask for a new one.
The process is as follows:

* The worker tells the scheduler that the job is done.

* The scheduler labels the corresponding intention(s) as done.
If the intention was finalist (it is not previous to any other
intention), it and all its previous intentions are archived.

* The scheduler archives the job.

* The worker selects the next job (assigned to it) to run.

* If there is no job ready to run, among those assigned to the worker,
the worker will ask the scheduler for a new job.

## Strategies for selection intention to run

In principle, any intention with `READY` state (meaning all previous
intentions are done), is a candidate to run. However, we don't want to
select any intention, for (at least) two reasons:

* We want selection to be "proportional" to users. That is, all users should
have the same probability of having an intention selected. This deals well with
the scenario in which a user with a lot of ready intentions prevents another one,
with just a few intentions ready, to have some of them selected.

* Once we have selected an intention, we still have to check if it has
all the needed resources. In principle, this could be done in the same query,
just by making it more complex. But checking resources is something dependent
on the kind of intention, so it is very difficult to have mainteinable code
(query, in this case) that can work properly when we add more intentions.

So, the strategy we will use will be:

* Select a user among those with ready intentions.
* For all intentions for that user, check (by kind) all intentions, to check
which ones have resources ready.
* When we find intentions with resources for a certain kind, select the oldest one.

To avoid locking the database for too long, all of this would be done without
locking. That could mean that when we finally have an intention, for some reason
(for example, some other intention using the same resources is selected),
that intention is no longer runable. If that's the case, we will try a new one.
For this, we will use a "hold and check" procedure:

* Start a transaction, for preventing any other worker of "hold and ckecking" at the same time
* Create job
* Hold resources (add them to the job), if they are still available
* Finish the transaction

If the transaction is committed, the worker starts with the new job.
If not, we consider this as if the intention was not able of running,
and start over again.

## Targets

Targets is how kinds of intentions are modelled. A target is, for example,
GitHub, or Git. Each target will have its own set of concepts. For example,
for GitHub, we need tokens, repositories, instances (deployments of
GitHub or GitHub Enterprise). Each target is built around one or more
"kinds" of intentions. For example, for GitHub, we need intentions to
get a list of repositories for an owner, to get the enriched index for
a repo, to get the raw index for a repo, etc. Some of them may have
precedences: for example, for getting the enriched index, you need the
raw index first. A target intention may also create (when done) other
intentions. For example, when the intention to get the list of repos
for a GitHub owner is done, it could create enriched GitHub index and
enriched Git indexes for all of them.

Targets are implemented in separate files in `targets` directory.
Those files are Python modules implementing classes for the intentions
(inheriting from Intention, with a separate table), and other auxiliary
classes. For example, for GitHub, we have Instance, Repo, and Token as
auxiliary model classes, and IRaw and IEnriched as Intention classes.