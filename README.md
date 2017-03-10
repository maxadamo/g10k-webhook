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

- `/opt/puppetlabs/puppet/bin/g10k_gitlab_webhook.py` will run a webserver on port `8000` on your puppet server.

- your git server will trigger the post-commit hook `curl2puppet.sh` (Check this file inside the directory `config_samples`. (`flock` is necessary, only if you intend to use more than one puppet server. Actually, the script uses `flask` in single threaded mode, and `flock` becomes a bit useless.

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

- `/etc/default/g10k-webhook` (You pull it from this repository)
