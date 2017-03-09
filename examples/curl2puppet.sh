#!/bin/bash
#
FLOCKDIR="/var/opt/gitlab/flock_dir"
REPONAME=$(basename $(basename "$PWD") '.git')

while read oldrev newrev refname; do
    BRANCH=$(git rev-parse --symbolic --abbrev-ref $refname)
    echo "flock ${FLOCKDIR}/puppet01.domain.com.lock curl http://puppet01.domain.com:8000/g10k/${REPONAME}/${BRANCH} &>/dev/null && rm -f ${FLOCKDIR}/puppet01.domain.com.lock" | at now
done
