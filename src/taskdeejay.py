#!/usr/bin/env python3

import copy
import json
import os
import platform
import shlex
import shutil
import sys
import uuid

from os.path import expanduser
from os.path import isfile
from os.path import isdir

from lib_generic.base import *
from lib_generic.typedkeyvalue import *

from lib_tj.globals import *
from lib_tj.issue import *
from lib_tj.tagtype import *
from lib_tj.usage import *

try:
    # avoid broken pipe 
    from signal import signal, SIGPIPE, SIG_DFL
    signal(SIGPIPE, SIG_DFL)
except ImportError:
    pass

VERSION = "TaskDeejay 0.11 (prototype), 2018-, Martin Auer, www.taskdeejay.com"




def pr_e(s):  print_error(s, use_colors=CONF.get("use-colors"))
def pr_w(s):  print_warn(s, use_colors=CONF.get("use-colors"))
def pr_i(s):  print_info(s, use_colors=CONF.get("use-colors"))
def pr_o(s):  print_ok(s, use_colors=CONF.get("use-colors"))
def pr_h(s):  print_hint(s, use_colors=CONF.get("use-colors"), show_hints=CONF.get("show-hints"))

def msgs__dir_is_no_issue(dname):
    pr_e("Directory '%s' is not a tracked issue" % dname)
    pr_h("Use '%s %s --add' to track this directory as issue" % (exename(), dname))

def msgs__issue_dir_not_found(dname):
    pr_e("Issue directory '%s' not found" % dname)

def msgs__dir_is_already_issue(dname):
    pr_w("Directory '%s' is already a tracked issue" % dname)

def msgs__SUCC__dir_added(dname):
    pr_o("Directory '%s' is now a tracked issue and can be tagged" % dname)
    pr_h("Use '%s %s --set <tag>=<value>' to tag it" % (exename(), dname))
    pr_h("Use '%s %s --tagspace-get' to see its valid tags" % (exename(), dname))




def cmd_tscreate(scope):
    s = scope[0]

    if isiss(s):
        tagspace = s + "/" + Glob.token_metadir + "/" + Glob.token_tagspace
        if isfile(tagspace):  
            pr_w("Issue '%s' already has a tagspace ('%s')" % (s, tagspace))
            return

        ls2file(tagspace, TagTypeHandler.default())
        pr_o("Tagspace '%s' created" % tagspace)
        pr_h("Edit it to modify tag types for '%s' and its (future) sub-issues" % s)

    elif isdir(s):
        msgs__dir_is_no_issue(s)
    else:
        msgs__issue_dir_not_found(s)


def cmd_add(scope):
    for s in scope:
        if not isdir(s):
            pr_e("Directory '%s' not found" % s)
            continue

        if isiss(s):
            #pr_w("Directory '%s' is already added as tracked issue" % s)
            msgs__dir_is_already_issue(s)
            continue

        os.mkdir("%s/%s" % (s, Glob.token_metadir))
        uuid4 = str(uuid.uuid4())
        ls2file("%s/%s/%s" % (s, Glob.token_metadir, Glob.token_id_tag), [uuid4])

        #pr_o("Directory '%s' added as tracked issue" % s)
        msgs__SUCC__dir_added(s)


def cmd_get(scope):  # todo list of fields
    for dname in scope:
        if isiss(dname):
            issue = Issue(dname)

            lls = []

            lls.append(["Issue: '" + issue.fullname + "'", ""])

            for k, tv in sorted(issue.d_tagvirt.items()):
                lls.append(tv.info())

            for k, tf in sorted(issue.d_tagfile.items()):
                if not k.startswith("_"):
                    lls.append(tf.info())

            printls(lls2ls(lls, delimiter="   "))

        elif isdir(dname):
            msgs__dir_is_no_issue(dname)
        else:
            msgs__issue_dir_not_found(dname)


def cmd_set(scope, ls):
    for dname in scope:
        if isiss(dname):
            issue = Issue(dname)
            for setter in ls:
                try:
                    s_msg = issue.set(setter)
                    pr_o("ok: %s:%s - %s" % (issue.name, setter, s_msg))
                except EUser as e:
                    pr_e("ERROR: %s:%s - %s" % (issue.name, setter, e))
        
        elif isdir(dname):
            msgs__dir_is_no_issue(dname)
        else:
            msgs__issue_dir_not_found()


def cmd_ls(scope, l_cols):
    SCOPE = []
    for dname in scope:
        if isdir(dname):
            ls = os.listdir(dname)
            ls = [x for x in ls if isiss(x)]
            lls = []
            for s in ls:
                SCOPE.append(s)
                issue = Issue(s)
                lls.append(issue.li(l_cols))
    printls(lls2ls(lls))
    return SCOPE  # todo hande scope-changing functions








CONF = TypedKeyValue(   {   "show-hints": "i", 
                            "del-m": "s", 
                            "ls-tags": "ls",
                            "ll-tags": "ls",
                            "use-colors": "i"
                        }, 
                        {   "show-hints": 1,
                            "del-m": " ",
                            "ls-tags": ["n","t","s","p","o"],
                            "ll-tags": ["n","t","s","p","o","i","pn"],
                            "use-colors": 1
                        })
_CONF_dflt = copy.deepcopy(CONF)

SCOPE = []
scope_collect = True


def json_rec(dname):    
    issue = Issue(dname)

    d_RET = issue.get_tags_as_dict()

    ls = os.listdir(issue.fullname)
    ls = [x for x in ls if isiss(issue.fullname + "/" + x)]  # issues
    d_RET["contains"] = [json_rec(s) for s in ls]  #??? maybe not use tag at all if empty

    return d_RET


def run(argv):
    global SCOPE
    global scope_collect

    while len(argv) > 0:
        cmd = argv[0]
        argv.pop(0)
        if cmd.startswith("--"):  scope_collect = False

        if cmd in ["--add"]:
            if len(SCOPE) == 0:
                raise ESys("'--add': no directories specified")  # todo better msg
            cmd_add(SCOPE)

        elif cmd == "--tagspace-create":
            if len(SCOPE) != 1:  
                raise ESys("'--tagspace-create': only operates on a single issue directory; use '%s <dir> --tagspace-create'" % exename())
            cmd_tscreate(SCOPE)

        elif cmd in ["--get"]:
            if len(SCOPE) == 0:
                SCOPE.append(".")
            cmd_get(SCOPE)  # todo select field

        elif cmd in ["--set"]:
            if len(SCOPE) == 0:  raise ESys("'--set': no issue directories specified")
            # todo also check len(ls) and raise exception here !!
            ls = get_argls(cmd, argv)
            cmd_set(SCOPE, ls)

        elif cmd == "--tagspace-get":
            if len(SCOPE) == 0:
                SCOPE.append(".")
            for s in SCOPE:
                if isiss(s):
                    issue = Issue(s)
                    fname = issue.fname_tagspace
                    if fname == "":
                        pr_e("No tagspace found for issue '%s'" % issue.name)
                        continue

                    print("Issue: '%s'" % issue.name)
                    print("Tagspace: '%s'" % issue.fname_tagspace)

                    issue.tth.p()  # todo print outside issue, just get lls..
                else:  # todo copy tamplate of error msgs from above
                    pr_e("'%s' is not a tracked issue" % s)

        elif cmd in ["--ls", "--ll"]:
            if len(SCOPE) == 0:
                SCOPE.append(".")
            ls = get_argls(cmd, argv)

            if ls == []:
                ls = CONF.get("ls-tags")
                if cmd == "--ll":
                    ls = CONF.get("ll-tags")

            SCOPE = cmd_ls(SCOPE, ls)








        elif cmd == "--version":
            print(VERSION)

        elif cmd == "-json":  # todo
            tmp = json_rec(".")
            print(json.dumps(tmp, indent=4))

        elif cmd == "--config-set":
            ls = get_argls(cmd, argv)
            if len(ls) == 0:  raise ESys("--config-set: no arguments given")
            CONF.set(ls[0], ls[1:])

        elif cmd == "--config-get":
            ls = get_argls(cmd, argv)
            if len(ls) == 0:
                print(CONF.dumps())
            else:
                for s in ls:
                    print(CONF.get(s))

        elif cmd == "--config-init":
            config_save(_CONF_dflt)

        elif cmd == "--config-save":
            config_save(CONF)

        elif cmd == "--tagspace-init":
            tagspace_init()

        elif cmd == "--reset":
            RESET()

        else:
            if scope_collect == True:
                SCOPE.append(cmd)
            else:
                raise ESys("Unknown command line option '%s'" % cmd)








def main(argv):
    if len(argv) == 0:
        usage()

    if argv[0] != "--config-ignore":
        fname = Glob.path_conffile
        if isfile(fname):
            CONF.load(fname)
    else:
        argv.pop(0)

    run(argv)




def init0():
    dname = Glob.path_confdir
    if not isdir(dname):
        os.mkdir(dname)

def config_save(d):
    init0()
    fname = Glob.path_conffile
    ls2file(fname, [d.dumps()])
    pr_o("Config file '%s' created" % fname)

def tagspace_init():
    init0()
    fname = Glob.path_tagspace_default
    ls2file(fname, TagTypeHandler.default())
    pr_o("Default tagspace '%s' created" % fname)
    pr_h("For a multi-user setup, a shared tagspace should be used; use '--tagspace-create'")

def RESET():
    dname = Glob.path_confdir
    if not isdir(dname):
        pr_i("Config dir does not exist; nothing to reset")
        return

    shutil.rmtree(dname)
    pr_o("User config and tagspace deleted")
    pr_h("Use '--config-init' and '--tagspace-init' to re-create")




if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except ESys as e:
        pr_e("ERROR_FATAL: %s" % e)
        sys.exit(99)
    except ESysInt as e:
        pr_e("ERROR_FATAL_INTERNAL: %s" % e)
        sys.exit(199)

