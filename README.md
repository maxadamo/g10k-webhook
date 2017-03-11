# g10k-webhook

`g10k-webhook` is `r10k_gitlab_webhook` with steroids, intended for use with `g10k`

`g10k` is `r10k` with steroids and it can be downloaded here: [g10k](https://github.com/xorpaul/g10k)

## Requirements:

```
- python git (deb: python-git | rpm: GitPython)
- python-flask
- python-jinja2
- /opt/puppetlabs/puppet/bin/g10k: https://github.com/xorpaul/g10k/
- /opt/puppetlabs/g10k/cache (owned by puppet)
- /var/log/g10k.log (owned by puppet. Do not forget a logrotate)
- puppet server 4.x (the modules are stored inside /etc/puppetlabs/code/)
```

## How does it work:

- `/opt/puppetlabs/puppet/bin/g10k_gitlab_webhook.py` will run a webserver on your puppet server (default port is `8000`).

- your git server will trigger a post-commit hook (see example below: I called it `curl2puppet.sh`).

- your puppet server will receive the trigger and will start fetching the modules.

## How to use it:

The core file is: `/opt/puppetlabs/puppet/bin/g10k_gitlab_webhook.py` (You pull it from this repository)

My setup has 3 branches and a master branch that in some case is being used across other branches.

The base directory is: /etc/puppetlabs/code/environments/`branch-goes-here`/ and it will contain the following files:

- `.gitignore` containining at least this line: `Puppetfile`

- `Puppetfile` will be renamed to `Puppetfile.j2` (check `config_samples` directory for a sample file)

Other files:

- `/etc/puppetlabs/g10.conf` (You pull it from this repository)

Other files (if you still use upstart, otherwise, please create a pull request to add a `Systemd` or `SysV` script):

- `/etc/init/g10k-webhook.conf` (You pull it from this repository)

## curl2puppet.sh:

This is the script that you run on your git server as `post-commit` hook. It extracts repository name and branch name and sends it to puppet:


	#!/bin/bash
	#
	FLOCKDIR="/var/opt/gitlab/flock_dir"
	REPONAME=$(basename $(basename "$PWD") '.git')

	while read oldrev newrev refname; do
	    BRANCH=$(git rev-parse --symbolic --abbrev-ref $refname)
	    echo "flock ${FLOCKDIR}/puppet01.domain.com.lock curl http://puppet01.domain.com:8000/g10k/${REPONAME}/${BRANCH} &>/dev/null && rm -f ${FLOCKDIR}/puppet01.domain.com.lock" | at now
	done

**N.B.**: `flock` is only necessary, if you intend to use more than one puppet server. Actually, the script uses `flask` in single threaded mode, and `flock` becomes a bit useless. Future versions of g10k will have an option to limit the number of concurrent Go routines, and the use of `flock` will not be necessary any longer.
