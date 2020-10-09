# The container produced with this file contains all GrimoireLab libraries and executables.
# It is configured for getting tasks from a database and running them
# Build this container from the root of the repository

FROM cauldronio/grimoirelab:0.2.45-py3.7

ENV CODE_WORKER /code

USER root

RUN apt-get update && apt-get install -y default-libmysqlclient-dev

# Add code from src folder
ADD . ${CODE_WORKER}
WORKDIR ${CODE_WORKER}
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Install requirements
RUN pip install -q -r requirements.txt

RUN mkdir -p /job_logs
RUN mkdir -p /git_repositories
RUN chown grimoirelab /job_logs
RUN chown grimoirelab /git_repositories

VOLUME ["/job_logs"]
VOLUME ["/git_repositories"]

USER grimoirelab

ENTRYPOINT ["/entrypoint.sh"]
