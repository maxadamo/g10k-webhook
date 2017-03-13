#!/usr/bin/python2
""" run flask CGI that will trigger g10k
    requirements:
      - python git (deb: python-git | rpm: GitPython)
      - python-flask
      - python-jinja2
      - /etc/puppetlabs/g10k.conf
      - /opt/puppetlabs/puppet/bin/g10k: https://github.com/xorpaul/g10k/
      - cache dir owned by puppet (set inside g10k.conf).
        g10k uses hardlinks and the cache must be in the same partition)
      - puppet server 4.x (it runs under /etc/puppetlabs/code/)
"""
import os
import ast
import getpass
import logging
import ConfigParser
import subprocess as sp
from datetime import datetime
import git
import jinja2
from flask import Flask
from flask import request

APP = Flask(__name__)


def loghandler(log_message, error=None):
    """ handle logging """
    config = ConfigParser.RawConfigParser()
    config.readfp(open('/etc/puppetlabs/g10k.conf'))
    g10k_log = config.get('g10k', 'g10k_log')
    log_file = g10k_log
    log_format = '%(asctime)-15s %(levelname)s %(message)s'
    logging.basicConfig(filename=log_file, level=logging.DEBUG, format=log_format)
    if error:
        logging.error(log_message)
    else:
        logging.info(log_message)


@APP.route('/g10k/<reponame>/<gitenv>/force')
@APP.route('/g10k/<reponame>/<gitenv>')
def parse_request(reponame, gitenv):
    """ check the git environment and run g10k """
    config = ConfigParser.RawConfigParser()
    config.readfp(open('/etc/puppetlabs/g10k.conf'))
    branch_list = ast.literal_eval(config.get('g10k', 'branch_list'))
    force = ast.literal_eval(config.get('g10k', 'force'))
    start_time = datetime.now()
    url_name = str(request.path)
    loghandler("======== Received trigger for branch: %s ========" % (gitenv))

    def generate(branches_list, cleanup=None):
        """ create generator with output message """
        for env_item in branches_list:
            G10k(env_item, reponame).git()
            G10k(env_item, reponame).render()
            if reponame != 'environments':
                if cleanup or force:
                    loghandler("purging modules directory")
                    G10k(env_item, reponame, cleanup=True).g10k()
                else:
                    G10k(env_item, reponame).g10k()
            yield "%s branch updated\n" % (env_item)

    if gitenv not in branch_list:
        return "%s is not a valid branch\n" % (gitenv)
    else:
        if gitenv != 'master':
            branch_list = [gitenv]
        if url_name.endswith('force'):
            result = "".join(generate(branch_list, cleanup=True))
        else:
            result = "".join(generate(branch_list))
        time_spent = (datetime.now() - start_time).seconds
        loghandler("======== Trigger processed in %s seconds ========" % (
            time_spent))
        return result


class G10k(object):
    """ g10k class: render puppet file and update puppet env """
    basedir = '/etc/puppetlabs/code/environments'

    def __init__(self, puppetenv, reponame, cleanup=None):
        self.puppetenv = puppetenv
        self.env_dir = os.path.join(self.basedir, puppetenv)
        self.config = ConfigParser.RawConfigParser()
        self.config.readfp(open('/etc/puppetlabs/g10k.conf'))
        self.cachedir = self.config.get('g10k', 'g10k_cachedir')
        self.puppetfile_vars = ast.literal_eval(self.config.get('g10k', 'puppetfile_vars'))
        self.reponame = reponame
        self.cmd_opts = '-puppetfile -verbose'
        # self.cmd_opts = '-puppetfile -verbose -maxworker %s' % (maxworker)
        if cleanup:
            self.cmd_opts += ' -force'

    def git(self):
        """ git: stash, checkout, pull """
        loghandler("==== Start update of puppet env: %s" % (self.puppetenv))
        git_cmd = git.cmd.Git(self.env_dir)
        local_branch = str(git_cmd.rev_parse('--abbrev-ref', 'HEAD'))

        try:
            git_stdout = git_cmd.stash()
        except Exception as err:
            loghandler("Failed stash changes on %s: %s" % (self.env_dir, str(err)), error=True)
        else:
            git_cmd.stash('clear')
            loghandler("stashing changes on %s: %s" % (self.env_dir, git_stdout))

        if local_branch != self.puppetenv:
            try:
                git_cmd.checkout(self.puppetenv)
            except Exception as err:
                loghandler("Failed to checkout branch: %s" % (str(err)), error=True)
            else:
                loghandler("switched to branch: %s" % (self.puppetenv))

        if self.reponame == 'environments':
            try:
                git_stdout = git_cmd.pull()
            except Exception as err:
                loghandler("Failed to pull: %s" % (str(err)), error=True)
            else:
                loghandler("pulling remote %s: %s" % (self.puppetenv, git_stdout))

    def render(self):
        """ convert jinja template to Puppetfile """
        puppetfile = os.path.join(self.env_dir, 'Puppetfile')
        self.puppetfile_vars.update({'puppetenvironment': str(self.puppetenv)})

        os.chdir(self.env_dir)
        puppetfile_content = jinja2.Environment(
            loader=jinja2.FileSystemLoader('./')
        ).get_template('Puppetfile.j2').render(self.puppetfile_vars)
        puppetfile_open = open(puppetfile, 'w+')
        puppetfile_open.write(puppetfile_content)
        puppetfile_open.close()

    def g10k(self):
        """ run g10k """
        os.chdir(self.env_dir)
        loghandler("running g10k for environment %s" % (self.puppetenv))
        g10k_cmd = 'g10k_cachedir=%s /opt/puppetlabs/puppet/bin/g10k %s' % (
            self.cachedir, self.cmd_opts)
        g10k_proc = sp.Popen(g10k_cmd, shell=True,
                             stdout=sp.PIPE, stderr=sp.STDOUT)
        g10k_proc_out = g10k_proc.communicate()[0]
        g10k_retcode = g10k_proc.returncode
        if g10k_retcode is not 0:
            loghandler(g10k_proc_out, error=True)
        else:
            loghandler(g10k_proc_out.split('\n')[-2])
        loghandler("==== End update of puppet env: %s" % (self.puppetenv))


if __name__ == '__main__':

    CONF_FILE = '/etc/puppetlabs/g10k.conf'
    BASE_DIR = '/etc/puppetlabs/code/environments'

    # check if we have read access to configuration file
    if os.access(CONF_FILE, os.R_OK):
        CONFIG = ConfigParser.RawConfigParser()
        CONFIG.readfp(open(CONF_FILE))
        G10K_LOG = CONFIG.get('g10k', 'g10k_log')
        CACHEDIR = CONFIG.get('g10k', 'g10k_cachedir')
        USER = CONFIG.get('g10k', 'g10k_user')
        PORT = int(CONFIG.get('g10k', 'port'))
        DEBUG = ast.literal_eval(CONFIG.get('g10k', 'debug'))
    else:
        print 'could not access %s' % (CONF_FILE)
        os.sys.exit(1)

    # check if everything is fine
    if getpass.getuser() != USER:
        print 'please run as %s user' % (USER)
        loghandler('please run as %s user' % (USER), error=True)
        loghandler('giving up and exiting... bye...', error=True)
        os.sys.exit(1)
    elif not os.access(CACHEDIR, os.W_OK):
        print 'could not write to %s' % (CACHEDIR)
        loghandler('could not write to %s' % (CACHEDIR), error=True)
        loghandler('giving up and exiting... bye...', error=True)
        os.sys.exit(1)
    elif hex(os.stat(BASE_DIR)[2]) != hex(os.stat(CACHEDIR)[2]):
        print '%s and %s not in the same partion. Could not create hardlinks' % (BASE_DIR, CACHEDIR)
        loghandler('%s and %s not in the same partion. Could not create hardlinks' % (
            BASE_DIR, CACHEDIR), error=True)
        loghandler('giving up and exiting... bye...', error=True)
        os.sys.exit(1)
    elif not os.access(G10K_LOG, os.W_OK):
        print 'could not write to %s' % (G10K_LOG)
        os.sys.exit(1)

    # Everything looks fine. Here we go:
    APP.run(debug=DEBUG, host='0.0.0.0', port=PORT)
