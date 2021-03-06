#!/usr/local/bin/python33
#####!/usr/local/bin/python3

import os
import platform
import shlex
import subprocess
import sys
import json
from os.path import expanduser
from os.path import isfile
from os.path import isdir

# avoid broken pipe 
from signal import signal, SIGPIPE, SIG_DFL
signal(SIGPIPE, SIG_DFL)



EXENAME = os.path.basename(sys.argv[0])
VERSION = "TaskDeejay 0.1 (prototype), 2018-, Martin Auer, www.taskdeejay.com"

def usage():
    msg = """
TaskDeejay allows to collaboratively track hierarchical tasks or *issues*.

An issue is simply a directory with some special metadata in it.
Each new or existing directory can be made into a tracked issue.
Issues can then be tagged, e.g., with 'status=todo'.
Issues directories can still contain normal files, for example deliverables, as well as other issues.
(They have unique internal IDs, so renaming directories will not break dependencies.)



START TUTORIAL:

1. First-time setup (only run once):
>{EXENAME} -INIT                                                # set up some tag definitions (a 'tagspace') and editable config files

2. Create and tag an issue:
>mkdir myProject
>{EXENAME} myProject -new                                       # make directory into a tracked issue
>{EXENAME} myProject -tag type=project status=inpr              # set some tags
>{EXENAME} myProject -i                                         # get info on issue

3. Create and tag three more issues, faster:
>cd myProject
>{EXENAME} myFirstEpic -n -t type=epic s=inpr
>{EXENAME} mySecondEpic myThirdEpic -n -t t=epic s=todo p=hi o+Barbara

4. List issues:
>{EXENAME} -l                                                   # list issues (and their tags) in current directory
>{EXENAME} -l name status id    (or: '-l n s i')                # the same, but show only some tags 
>{EXENAME} -ll                                                  # more info



USAGE:

Creating issues:
>{EXENAME} <dir1> <dir2> .. -n[ew]                              # create issues from directories (and create dirs if needed)

Tagging:
>{EXENAME} -ts                                                  # show valids tags for current dir
>{EXENAME} <dir1> <dir2> .. -t[ag] <tag1>=<v1> <tag2>=<v2> ..   # tag issues
>{EXENAME} -t[ag] <tag1>=<v1> ..                                # no issues given -> tag current directory/issue

Reports:
>{EXENAME} -l                                                   # list issues in current dir with default tags
>{EXENAME} -l <tag1> <tag2> ..                                  # list with specific tags
>{EXENAME} -ll                                                  # list with most tags
>{EXENAME} -i[nfo]                                              # info on current dir/issue
>{EXENAME} <dir1> <dir2> .. -i                                  # info on issues

Command combination/pipe:
>{EXENAME} <dir> -n -t <tag1>=<v1> -i                           # creates, tags, and shows info on issue

Configuration:
>{EXENAME} -INIT                                                # create config dir in home
>{EXENAME} -RESET                                               # remove config dir in home

>{EXENAME} -p conf                                              # print global variables (e.g., quiet,..)
>{EXENAME} -set <variable> <value>                              # temporarily override config variable

"""
    print(msg.replace("{EXENAME}", EXENAME), file=sys.stderr, end="")
    sys.exit(2)
    ## todo above: filter & sort


# generic helper functions

def EXIT(text):
    print("ERROR_FATAL: " + EXENAME + ": " + text, file=sys.stderr)
    sys.exit(99)

def EXIT_INTERNAL(text):
    print("ERROR_FATAL_INTERNAL: " + EXENAME + ": " + text, file=sys.stderr)
    sys.exit(199)

def printu(s):  # to suppress ok actions, or to suppress completely in pipe
    print(s)

def printe(s):
    print(s, file=sys.stderr)

def printh(s):  # to suppress hints
    if CONF.v("show_hints") == 1:
        print(s)


class ESys(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
class ESysInt(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg
class EUser(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg


def s2x(s, type):  # conversion helper
    if type == "s":
        return True, s
    try:
        if type == "i":
            return True, int(s)
        elif type == "f":
            return True, float(s)
        return False, "invalid type '%s'" % type
    except:
        return False, "can't convert string '%s' to type '%s'" % (s, type)


def get_args(cmd, argv, l_type):  # helper function to process command line arguments with fixed-length, type-safe sub-parameters
    RET = []
    if len(l_type) > len(argv):  raise ESys("command line option '%s': not enough arguments" % cmd)

    for i in range(len(l_type)):
        type = l_type[i]
        s_arg = argv[i]
        success, v_new = s2x(s_arg, type)
        if not success:  raise ESys("command line option '%s':" % cmd + v_new)
        RET.append(v_new)
    for i in range(len(l_type)):
        argv.pop(0)
    if len(RET) > 1:
        return RET  # as list..
    return RET[0]  # ..or only 1st element


def get_argls(cmd, argv):  # helper function to process command line arguments with variable-length, option-delimited string sub-parameters
    RET = []
    for arg in argv:
        if arg.startswith("-"):
            break
        RET.append(arg)
    for i in range(len(RET)):
        argv.pop(0)
    return RET


def file2ls(fname, remove_comments=True, remove_empty=True, allow_empty=False):  # converts file to (l)ist of (s)trings
    RET = []
    try:
        for s in open(fname):
            s = s.rstrip()
            if remove_empty and len(s) == 0:
                continue
            if remove_comments and len(s) >= 1 and s[0] == '#':
                continue
            RET.append(s)
    except:
        raise ESys("error reading file '%s'" % fname)

    if allow_empty == False and len(RET) == 0:  raise ESys("file '%s' is empty" % fname)

    return RET


def file2lls(fname, remove_comments=True, remove_empty=True, allow_empty=False, delimiter='|', same_length=True):  # converts file to string matrix
    RET = []
    ls = file2ls(fname, remove_comments, remove_empty, allow_empty)

    for s in ls:
        RET.append(s.split(delimiter))

    if same_length:
        for ls in RET[1:]:
            if len(ls) != len(RET[0]):  raise ESys("file format error in '%s': all lines must have same length" % fname)

    return RET


def ls2file(fname, ls):
    file = open(fname, "w")
    for s in ls:
        file.write(s)
        file.write("\n")
    file.close()


def lls2file(fname, lls, delimiter=" "):
    tmp = []
    for ls in lls:
        tmp.append(delimiter.join(ls))
    ls2file(fname, tmp)


def lls2ls(lls, mode="human", l_align=[], fit_to_screen=False, delimiter=" ", ignore_header=False):
    if len(lls) == 0:  return [""]

    RET = []
    if mode == "machine":
        for ls in lls:
            #RET.append(delimiter.join(ls))
            RET.append(CONF.v("del_m").join(ls))
        return RET

    if len(l_align) == 0:  l_align = ["<"] * len(lls[0])
    max_chars = [max(li) for li in [[len(ls[i]) for ls in lls] for i in range(len(lls[0]))]]

    # pretty
    for ls in lls:
        ls_new = ["{message: {align}{width}}".format(message=s, align=a, width=w) for s, a, w in
                  zip(ls, l_align, max_chars)]
        RET.append(delimiter.join(ls_new))

    return RET


def exe(cmd, l_fname_in=[], l_fname_out=[], skip=True):
    # check if all output files exist
    if skip and len(l_fname_out) > 0:
        ret = True
        for fname in l_fname_out:
            if isfile(fname):
                INFO2("output file '%s' already exists.." % fname)
            else:
                INFO2("output file '%s' not found; enforcing execution" % fname)
                ret = False

        if ret:  return ["__skipped__"], ["__skipped__"]

    for fname in l_fname_in:
        if not isfile(fname):
            raise ESys("input file '%s' does not exist (full command:  >>>  %s  <<<)" % (fname, cmd))

    p = subprocess.Popen("set -o pipefail ; " + cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    o, e = p.communicate()

    lo = o.decode(encoding="UTF-8").split("\n")[:-1]
    le = e.decode(encoding="UTF-8").split("\n")[:-1]

    if p.returncode != 0:
        raise ESys("exe: non-zero return code in command:\n'%s'\n%s" % (cmd, "\n".join(le)))

    return lo, le


def p(ls):
    for s in ls:
        print(s)







class Glob():
    token_metadir = ".__tj_meta"
    token_id_tag = "_id"
    token_tagspace = "tagspace.txt"
    path_home = expanduser("~")
    name_confdir = ".tj"
    path_confdir = path_home + "/" + name_confdir
    name_conffile_default = "conf_default.txt"
    path_conffile_default = path_confdir + "/" + name_conffile_default
    name_conffile_user_override = "conf_user_override.txt"
    path_conffile_user_override = path_confdir + "/" + name_conffile_user_override
    path_tagspace_default = path_confdir + "/" + token_tagspace


class Conf:
    def __init__(self):
        self.d_V = {}  # types: s, i, f
        self.d_V["show_hints"] = ["i", 1]
        self.d_V["del_m"] = ["s", " "]
        self.d_V["l_tags"] = ["s", "n t s p o"]
        self.d_V["ll_tags"] = ["s", "n t s p o i pn"]
        self.d_V["use_cur_dir"] = ["i", 1]


    def default():
        tmp = [
            "",
            "###",
            "show_hints             1                               # turn hints on/off",
            "",
            "###",
            "del_m                  |                             # column delimiter for machine output",
            "",
            "###",
            "l_tags                 name type status prio owners    # default tags for '-l' (could also be given as 'n t s p o')",
            "",
            "###",
            "ll_tags                n t s p o i pn                  # default tags for '-ll'",
            "",
            "###",
            "use_cur_dir            1                               # use current dir as default issue if no issues are given",
            ""
        ]
        return tmp

    def v(self, name):
        if name not in self.d_V:  raise ESys("Unknown global variable '%s'" % name)
        return self.d_V[name][1]

    def p(self):
        for key in sorted(self.d_V):
            print("%s %s" % (key, str(self.d_V[key][1])))

    def set(self, name, s_value):
        if name not in self.d_V:  raise ESys("Unknown global variable '%s'" % name)
        success, v_new = s2x(s_value, self.d_V[name][0])
        if not success:  raise ESys(v_new)
        self.d_V[name][1] = v_new

    def conf(self, fname):
        tmp = file2ls(fname, allow_empty=True)
        for s in tmp:
            tmp = " ".join(list(shlex.shlex(s)))    # ugly 1, removes comments
            ls = shlex.split(tmp)                   # ugly 2, removes enclosing quotation
            tmp = " ".join(ls[1:])
            self.set(ls[0], tmp)

    def save(self, fname):
        lls = []
        for k in sorted(self.d_V):
            ls = [k, str(self.d_V[k][1])]
            lls.append(ls)
        lls2file(fname, lls)






def isiss(dname):  # todo create value&list_of_values funtion
    return isdir(dname + "/" + Glob.token_metadir)


class Direc():
    def __init__(self, dname):
        self.name_ = dname  # could also, e.g., be '.' ..
        self.fullname = os.path.abspath(self.name_)
        self.name = os.path.basename(self.fullname)

        # parent
        tmp = "/".join( self.fullname.split("/")[:-1] )  #todo Windows compatibility
        self.parentname = os.path.basename(tmp)
        #print("XXXXXXXXXXXX" + self.parentname)

        #self.infix_current = "current " if self.name_ == "." else ""


class TagFile():
    def __init__(self, name, fname, issue):
        self.name = name
        self.fname = fname
        self.issue = issue  # to get tagspace

        self.V = []  # for newly created tags
        if isfile(fname):
            self.V = file2ls(fname, allow_empty=True, remove_comments=False)

        self.tth = self.issue.tth
        self.tt = self.tth.get_tagtype(self.name)

    def is_valid(self):
        is_valid,s_err = self.tt.is_tvalue_valid(self.V)
        return is_valid, s_err

    def get_svalue(self):
        return ",".join(self.V)  #todo call TT function for formatting

    def info(self):
        is_valid,s_err = self.is_valid()
        if is_valid:
            return "%s=%s" % (self.name, self.get_svalue()), ""
        return "%s=%s" % (self.name, self.get_svalue()), "(warning: %s)" % s_err

    def modify(self, operation, Vnew):
        succ, VALUE, s_msg = self.tt.V(self.V, operation, Vnew)
        ls2file(self.fname, VALUE)
        return s_msg #todo also return succ, for exit code handling

class TagVirtualName():
    def __init__(self, name, issue):
        self.name = name
        self.issue = issue

    def get_svalue(self):
        return self.issue.name

    def info(self):
        return ["name=" + self.get_svalue(), "(read-only)"]

class TagVirtualParentname():
    def __init__(self, name, issue):
        self.name = name
        self.issue = issue

    def get_svalue(self):
        return self.issue.parentname

    def info(self):
        return ["parentname=" + self.get_svalue(), "(read-only)"]

class TagVirtualId():
    def __init__(self, name, issue):
        self.name = name
        self.issue = issue

    def get_svalue(self):
        return self.issue.d_tagfile["_id"].get_svalue()  #todo use const string

    def info(self):
        return ["id=" + self.get_svalue(), "(read-only)"]

class TagVirtualTagspace():
    def __init__(self, name, issue):
        self.name = name
        self.issue = issue

    def get_svalue(self):
        #succ,fname_tagspace = Issue.find_tagspace(self.issue.fullname)
        #return fname_tagspace  #todo use const string
        return self.issue.fname_tagspace

    def info(self):
        return ["tagspace=" + self.get_svalue(), "(read-only)"]

class Issue(Direc):
    def __init__(self, dname):
        super().__init__(dname)
        self.d_tagfile = {}
        self.d_tagvirt = {}

        self.tth = TagTypeHandler()
        succ,self.fname_tagspace = Issue.find_tagspace(self.fullname)  # get override filename
        if succ == True:
            self.tth.init(self.fname_tagspace)

        self.init_tags()

    def get_metadir(self):
        return self.fullname + "/" + Glob.token_metadir

    def init_tags(self):
        # tags, virtual
        self.d_tagvirt["name"] = TagVirtualName("name", self)
        self.d_tagvirt["id"] = TagVirtualId("id", self)
        self.d_tagvirt["tagspace"] = TagVirtualTagspace("tagspace", self)
        self.d_tagvirt["parentname"] = TagVirtualParentname("parentname", self)

        # tagfiles
        # todo shorten
        ls = os.listdir(self.get_metadir())  # todo only files
        #ls = [x for x in ls if isfile(self.get_metadir() + "/" + x)]
        ls = [x for x in ls if isfile(self.get_metadir() + "/" + x)]
        # todo remove
        for s in ls:
            if s == Glob.token_tagspace:  continue
            tf = TagFile(s, self.get_metadir() + "/" + s, self)
            self.d_tagfile[tf.name] = tf

    #todo get() tag by name, including virtual tags

    def set(self, setter):
        #todo alow return of VALUE-list with more than 1 element
        succ, tagname, operation, VALUE, s_err = self.tth.parse_setter(setter)

        tagname = self.tth.get_full_tagname(tagname)

        tmp_tagfile = TagFile(tagname, self.fullname + "/" + Glob.token_metadir + "/" + tagname, self)
        if tagname in self.d_tagfile:
            if tagname.startswith("_"):  raise EUser("tag '%s' is read-only" % tagname)
            tmp_tagfile = self.d_tagfile[tagname]

        s_msg = tmp_tagfile.modify(operation, VALUE)
        return s_msg

    def li(self, ls):
        RET = []
        for s in ls:
            s = self.tth.get_full_tagname(s)  # idempotent

            if s in self.d_tagvirt:
                RET.append(self.d_tagvirt[s].get_svalue())  #todo: consider continue to avoid double output is shortcuts are wrong; 
                continue                                    #better: make sure shortcuts are better handled

            if s in self.d_tagfile:
                RET.append(self.d_tagfile[s].get_svalue())
            else:
                RET.append("")
        return RET 

    def get_tags_as_dict(self):
        RET = {}
        for k in self.d_tagvirt:
            RET[k] = self.d_tagvirt[k].get_svalue()
        for k in self.d_tagfile:
            RET[k] = self.d_tagfile[k].get_svalue()
        return RET

    @staticmethod
    def find_tagspace(fullname):
        ls = fullname[1:].split("/")
        for i in range(len(ls), -1, -1):
            superpath = "/" + "/".join(ls[0:i])
            tagspace = superpath + "/" + Glob.token_metadir + "/" + Glob.token_tagspace
            if isfile(tagspace):
                #print("AAAAA " + tagspace)
                return (True, tagspace)
            #else:
            #    print("XXXXX " + tagspace)
        # no tagspace found in hierarchy
        if isfile(Glob.path_tagspace_default):
            return (True, Glob.path_tagspace_default)
        return (False, "")










class TagType():
    def __init__(self, name, shortname):  # todo shortname, so it doesn expand to filenames!!!
        self.name = name
        self.shortname = shortname


class TagTypeUnknown(TagType):  # used for tags that are not in current tagspace
    def __init__(self, name):
        super().__init__(name, "")  # todo maybe remove name at all
        self.tname = "?"

    def is_tvalue_valid(self, V):
        return False, "tag '%s' not valid in current tagspace" % self.name  # todo add tagspace name

    def V(self, Vold, op, Vnew):
        raise EUser(self.is_tvalue_valid([])[1])

class TagTypeElem1(TagType):
    def __init__(self, name, shortname, valid_values):
        super().__init__(name, shortname)
        self.tname = "elem1"
        self.valid_ops = "="
        self.valid_values = valid_values
        if len(valid_values) == 0:  raise ESys("XXX")  # todo
        self.desc_allowed = "1 in {%s}" % ", ".join(self.valid_values)

    def is_tvalue_valid(self, V):
        if len(V) > 1:  return False, "multiple entries for tag type '%s'" % self.tname
        for v in V:
            if v not in self.valid_values:  return False, "current value '%s' invalid" % v
        return True, ""

    def V(self, Vold, op, Vnew):
        valid,s_err = self.is_tvalue_valid(Vold)
        if not valid:  raise EUser(s_err)

        if op not in self.valid_ops:
            raise EUser("operation '%s' invalid for tag type '%s'" % (op, self.tname))

        if len(Vnew) == 0:
            return True, Vnew, "cleared"
        elif len(Vnew) == 1:
            if Vnew[0] not in self.valid_values:
                raise EUser("new value '%s' invalid" % Vnew[0])    
            return True, [Vnew[0]], "'%s' set to '%s'" % (self.name, Vnew[0])
        raise EUser("multiple entries not allowed")

class TagTypeElemN(TagType):
    def __init__(self, name, shortname, valid_values):
        super().__init__(name, shortname)
        self.tname = "elemN"
        self.valid_ops = "=+-"
        self.valid_values = valid_values
        if len(valid_values) == 0:  raise ESys("XXX")  # todo
        self.desc_allowed = "N in {%s}" % ", ".join(self.valid_values)

    def is_tvalue_valid(self, V):
        if len(V) != len(set(V)):  return False, "duplicate entries"
        for v in V:
            if v not in self.valid_values:  return False, "invalid value '%s'" % v
        return True, ""

    def V(self, Vold, op, Vnew):
        valid,s_err = self.is_tvalue_valid(Vold)
        if not valid:  raise EUser(s_err)

        if op not in self.valid_ops:
            raise EUser("operation '%s' invalid for tag type '%s'" % (op, self.tname))

        if len(Vnew) == 0:
            return True, Vnew, "cleared"

        valid,s_err = self.is_tvalue_valid(Vnew)
        if not valid:  raise EUser(s_err)

        if op == "+":
            tmp = Vold[:]
            tmp.extend(Vnew)
            tmp = list(set(tmp))
            return True, tmp, "added '%s'" % (",".join(Vnew))  #todo x3 also mention self.name like in Elem1
        elif op == "=":
            tmp = Vnew[:]
            tmp = list(set(tmp))
            return True, tmp, "set to '%s'" % (",".join(Vnew))
        elif op == "-":
            tmp = set(Vold[:])
            tmp2 = set(Vnew)
            tmp = list(tmp - tmp2)
            return True, tmp, "removed '%s'" % (",".join(Vnew))
        else:
            raise ESysInt("TagTypeStrN.V(): invalid operation")

class TagTypeStr1(TagType):
    def __init__(self, name, shortname, valid_values):
        super().__init__(name, shortname)
        self.tname = "str1"
        self.valid_ops = "="
        self.desc_allowed = "*"
        if len(valid_values) != 0:  raise ESys("XXX")  # todo

    @staticmethod
    def is_tvalue_valid(V):
        if len(V) > 1:  return False, "multiple values for tag type 'str1'"
        for v in V:
            if len(v) == 0:  return False, "empty value for tag type 'str1'"  # todo load with empty+comments
        return True, ""

    def V(self, Vold, op, Vnew):
        valid,s_err = self.is_tvalue_valid(Vold)
        if not valid:  raise EUser(s_err)

        if op not in self.valid_ops:
            raise EUser("operation '%s' invalid for tag type '%s'" % (op, self.tname))

        if len(Vnew) == 0:
            return True, Vnew, "cleared"
        elif len(Vnew) == 1:
            #todo check for allowd string format
            return True, [Vnew[0]], "set to '%s'" % Vnew[0]  #todo also mention self.name
        raise EUser("multiple entries not allowed")

class TagTypeStrN(TagType):
    def __init__(self, name, shortname, valid_values):
        super().__init__(name, shortname)
        self.tname = "strN"
        self.valid_ops = "=+-"
        self.desc_allowed = "*, *, .."
        if len(valid_values) != 0:  raise ESys("XXX")  # todo

    @staticmethod
    def is_tvalue_valid(V):
        for v in V:
            succ, s_err = TagTypeStr1.is_tvalue_valid([v])
            if not succ:  return False, s_err
        return True, ""
        #todo check for duplicate values

    def V(self, Vold, op, Vnew):
        valid,s_err = TagTypeStrN.is_tvalue_valid(Vold)
        if not valid:  raise EUser(s_err)

        if op not in self.valid_ops:
            raise EUser("operation '%s' invalid for tag type '%s'" % (op, self.tname))

        if len(Vnew) == 0:
            return True, Vnew, "cleared"

        #todo ? allow empty strings
        #todo ? ';' in tag content?
        if op == "+":
            tmp = Vold[:]
            tmp.extend(Vnew)
            tmp = list(set(tmp))
            #print(tmp)
            return True, tmp, "added '%s'" % (",".join(Vnew))  ##todo x3 also mention self.name
        elif op == "=":
            tmp = Vnew[:]
            tmp = list(set(tmp))
            return True, tmp, "set to '%s'" % (",".join(Vnew))
        elif op == "-":
            tmp = set(Vold[:])
            tmp2 = set(Vnew)
            tmp = list(tmp - tmp2)
            return True, tmp, "removed '%s'" % (",".join(Vnew))
        else:
            raise ESysInt("TagTypeStrN.V(): invalid operation")


class TagTypeHandler():
    def __init__(self):
        self.d_TT = {}
        self.d_TTs = {}  # for shortcuts; string2string

        self.d_TT["_id"] = TagTypeStr1("_id", "", [])
        #self.d_TT["_creator"] = TagTypeStr1("_creator", "", [])  #todo make virtual

        self.d_TTs["n"] = "name"
        self.d_TTs["i"] = "id"
        self.d_TTs["ts"] = "tagspace"
        self.d_TTs["pn"] = "parentname"

        self.fname = "<internal default>"

    def init(self, fname):
        self.fname = fname
        ls = file2ls(fname)  # todo: check what can happen with exception here
        for s in ls:
            ls = shlex.split(s)
            if len(ls) < 2:  raise ESys("Tag format error in tagspace line '%s'" % s)
            name = ls[0].split("|")[0]  # todo avoid several |.   #todo avoid duplicate entries in tagspace
            shortname = ls[0][len(name) + 1:]
            typename = ls[1]
            if typename == "elem1":  # todo switch
                self.d_TT[name] = TagTypeElem1(name, shortname, ls[2:])
            elif typename == "elemN":
                self.d_TT[name] = TagTypeElemN(name, shortname, ls[2:])
            elif typename == "str1":
                self.d_TT[name] = TagTypeStr1(name, shortname, ls[2:])
            elif typename == "strN":
                self.d_TT[name] = TagTypeStrN(name, shortname, ls[2:])
            else:
                raise ESysInt("TagTypeHandler.init(): tagtype '%s' unknown" % typename)

            if shortname != "":
                if shortname not in self.d_TTs:
                    self.d_TTs[shortname] = name
                else:
                    raise ESysInt("TagTypeHandler.init(): tagtype shortname '%s' already used" % shortname)

    def default():  #todo rename; default is in <init>, this is 'recommended'
        tmp = [
            "",
            "#Name          Type                Possible values",
            "",
            "type|t         elem1               project epic story task subtask",
            "status|s       elem1               todo inpr done",
            "prio|p         elem1               crit hi med lo",
            "due|d          elem1               18q4 19q1 19q2 19q3 19q4 20q1 20q2 20q3 20q4 21q1 21q2 21q3 21q4",
            "",
            "owners|o       strN",
            "watchers|w     strN",
            "",
            "develop|dev    elemN               inpr_specdone inpr_impldone inpr_testdone inpr_rolloutdone",
            ""
        ]
        return tmp

    def get_tagtype(self, tagname):
        if tagname in self.d_TT:
            return self.d_TT[tagname]
        return TagTypeUnknown(tagname)

    def get_full_tagname(self, s):
        if s in self.d_TTs:
            return self.d_TTs[s]
        return s

    def p(self):
        lls = []
        lls.append(["Tag", "Short", "Allowed", "Tagtype"])
        lls.append(["name", "n", "(read-only)", "(virtual)"])
        lls.append(["id", "i", "(read-only)", "(virtual)"])
        lls.append(["parentname", "pn", "(read-only)", "(virtual)"])
        lls.append(["tagspace", "ts", "(read-only)", "(virtual)"])
        for k in sorted(self.d_TT):
            if k.startswith("_"):  continue
            tt = self.d_TT[k]
            lls.append([tt.name, tt.shortname, tt.desc_allowed, tt.tname])
        p(lls2ls(lls, l_align=["<", "^", "<", "<"], delimiter=" | "))

    @staticmethod
    def hlp_condense_str(s, valid_chars):
        return "".join([c for c in s if c in valid_chars])
    @staticmethod
    def parse_setter(s):
        delimiter = TagTypeHandler.hlp_condense_str(s, "=+-")  ##todo copy function over!!!!
        if len(delimiter) < 1:
            raise EUser("no operation specified; one of '= + -' required")
        if len(delimiter) > 1:
            raise EUser("multiple operations specified; only one of '= + -' allowed")
        operation = delimiter

        tmp = s.split(delimiter)
        tagname = tmp[0]
        # if len(tagname) == 0:  tagname = "_labels"
        if len(tagname) == 0:
            raise EUser("no tag specified; format must be '<tag>[=|+|-]<value>'")

        value = tmp[1]  ##todo shlex splitter
        V = [value]  ##todo proper
        if value=="":  V=[]  ##todo
        
        return True, tagname, operation, V, ""






def new(scope):
    for s in scope:
        if isiss(s):
            printu("Directory '%s' exists and is already added as tracked issue" % s)
            continue

        infix = ""
        if not isdir(s):
            exe("mkdir %s" % s)
            infix = "created and "

        exe("mkdir %s/%s" % (s, Glob.token_metadir))
        if platform.system() == "Darwin":
            lo,le = exe("uuidgen")
        else:
            lo,le = exe("cat /proc/sys/kernel/random/uuid")

        if len(lo) != 1:  raise ESys("create: error in creating UUID")
        tjID = lo[0]
        exe("echo '%s' > %s/%s/%s" % (tjID, s, Glob.token_metadir, Glob.token_id_tag))

        printu("Directory '%s' %sadded as issue" % (s, infix))

    return scope


def TS(scope):
    s = scope[0]
    if not isiss(s):  raise ESys("'%s' not a valid issue; use '-new' to create or add as tracked item" % s)

    tagspace = s + "/" + Glob.token_metadir + "/" + Glob.token_tagspace
    if isfile(tagspace):  raise ESys("'%s' already contains the tagspace '%s'; delete it and re-run '-TS' if you want a new one" % (s, tagspace))

    ls2file(tagspace, TagTypeHandler.default())
    printu("Tagspace '%s' created; edit this file to modify tag definitions for '%s' and all its (future) sub-issues" % (
            tagspace, s))

    return scope


class color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    DARKCYAN = '\033[36m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'


def info(scope, expert):
    for dname in scope:
        if isiss(dname):
            issue = Issue(dname)

            lls = []  # todo one scope higher

            # print("Issue: " + issue.name)
            lls.append(["Issue: '" + issue.fullname + "'", ""])
            #if expert == True:
            #    if issue.fname_tagspace == "":
            #        # printu("Tagspace not defined; use '-INIT' to create default tagspace, or '-TS' the create shared one")
            #        lls.append(["Tagspace: <not defined>", "(tagspace not defined; use '-INIT' to create default tagspace, or '-TS' the create shared one)"])
            #    else:    
            #        lls.append(["Tagspace: " + issue.fname_tagspace, ""])

            for k, tv in sorted(issue.d_tagvirt.items()):
                lls.append(tv.info())

            for k, tf in sorted(issue.d_tagfile.items()):
                if not k.startswith("_"):
                    lls.append(tf.info())

            p(lls2ls(lls, delimiter="   "))
            continue

        if isdir(dname):
            direc = Direc(dname)
            printu("The directory '%s' is not yet tracked as issue" % (direc.name))
            printu("(Use 'tj %s -new' to add)" % direc.name)
            # todo print something in lls
            continue

        # todo print something in lls
        printu("'%s' is not a directory" % dname)

    return scope


def tag(scope, ls):
    for dname in scope:
        if isiss(dname):
            issue = Issue(dname)
            for setter in ls:
                try:
                    s_msg = issue.set(setter)
                    print("ok %s:%s - %s" % (issue.name, setter, s_msg))
                except EUser as e:
                    print("ERROR %s:%s - %s" % (issue.name, setter, e))
        else:
            print("ERROR '%s' is not a valid issue" % dname)


def li(scope, l_cols):
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
    p(lls2ls(lls))
    return SCOPE


CONF = Conf()






def json_rec(dname):    
    issue = Issue(dname)

    d_RET = issue.get_tags_as_dict()

    ls = os.listdir(issue.fullname)
    ls = [x for x in ls if isiss(issue.fullname + "/" + x)]  # issues
    d_RET["contains"] = [json_rec(s) for s in ls]  #??? maybe not use tag at all if empty

    return d_RET

def run(argv):
    autoscope = True

    SCOPE = []

    while len(argv) > 0:
        cmd = argv[0]
        argv.pop(0)

        if cmd in ["-new", "-n"]:
            autoscope = False
            if len(SCOPE) == 0:
                if CONF.v("use_cur_dir") != 1:
                    raise ESys("'-create' must be preceded with one or more directory names, e.g., 'myProject -create'")
                else:
                    SCOPE.append(".")
            SCOPE = new(SCOPE)
            # SCOPE = add(SCOPE)

        elif cmd == "-TS":
            autoscope = False
            if len(SCOPE) == 0:
                if CONF.v("use_cur_dir") != 1:
                    raise ESys("'-TS' must be preceded with one or more directory names, e.g., 'myProject -TS'")
                else:
                    SCOPE.append(".")
            if len(SCOPE) != 1:  raise ESys(
                "'-TS' only operates on individual directories, as it creates tagspaces usually reserved for the project to level issue; call with one argument only")
            SCOPE = TS(SCOPE)

        elif cmd in ["-info", "-i"]:
            autoscope = False
            if len(SCOPE) == 0:
                if CONF.v("use_cur_dir") != 1:
                    raise ESys("'-info' must be preceded with one or more directory names, e.g., 'myProject -info'")
                else:
                    SCOPE.append(".")
            SCOPE = info(SCOPE, cmd == "-i")

        elif cmd in ["-tag", "-t"]:
            autoscope = False
            if len(SCOPE) == 0:
                if CONF.v("use_cur_dir") != 1:
                    raise ESys("'-tag' must be preceded with one or more directory names, e.g., 'myProject -tag'")
                else:
                    SCOPE.append(".")
            ls = get_argls(cmd, argv)
            tag(SCOPE, ls)

        elif cmd == "-ts":
            autoscope = False
            if len(SCOPE) == 0:
                if CONF.v("use_cur_dir") != 1:
                    raise ESys("'-ts' must be preceded with one or more directory names, e.g., 'myProject -ts'")
                else:
                    SCOPE.append(".")
            for s in SCOPE:
                if isiss(s):
                    issue = Issue(s)
                    fname = issue.fname_tagspace
                    if fname == "":
                        print("No tagspace found for issue '%s'" % issue.name)
                        continue

                    print("Issue: '%s'" % issue.name)
                    print("Tagspace: '%s'" % issue.fname_tagspace)

                    issue.tth.p()  # todo print outside issue, just get lls..
                #else:
                #    print("'%s' is a directory")

        elif cmd in ["-l", "-ll"]:
            autoscope = False
            if len(SCOPE) == 0:
                if CONF.v("use_cur_dir") != 1:
                    raise ESys("'-l' must be preceded with one or more directory names, e.g., 'myProject -li'")
                else:
                    SCOPE.append(".")
            ls = get_argls(cmd, argv)

            if ls == []:
                s_cols = CONF.v("l_tags")
                if cmd == "-ll":
                    s_cols = CONF.v("ll_tags")
                ls = s_cols.split(" ")

            SCOPE = li(SCOPE, ls)





        elif cmd == "-set":
            name, s_value = get_args(cmd, argv, ["s", "s"])
            CONF.set(name, s_value)



        elif cmd == "-p":
            what = get_args(cmd, argv, ["s"])
            if what == "conf":
                CONF.p()
            elif what == "tags":
                if not isiss("."):
                    print("Current dir is not a tracked issue")
            else:
                raise ESys("Invalid print option '%s'" % what)

        elif cmd == "-version":
            print(VERSION)

        elif cmd == "-json":
            tmp = json_rec(".")
            print(json.dumps(tmp, indent=4))

        elif cmd == "-INIT":
            raise ESys("Command line option '%s' must be sole argument" % cmd)
        elif cmd == "-RESET":
            raise ESys("Command line option '%s' must be sole argument" % cmd)

        else:
            if autoscope == True:
                SCOPE.append(cmd)
            else:
                raise ESys("Unknown command line option '%s'" % cmd)

    if len(SCOPE) != 0 and autoscope == True:
        info(SCOPE, False)






def main(argv):
    if len(argv) == 0:
        usage()

    if argv[0] == "-RESET":
        RESET()
        return
    if argv[0] == "-INIT":
        INIT()
        return

    useconf = True
    if argv[0] == "-noconf":
        useconf = False
        argv.pop(0)
    if useconf:
        fname = Glob.path_conffile_default
        if isfile(fname):
            CONF.conf(fname)
        fname = Glob.path_conffile_user_override
        if isfile(fname):
            CONF.conf(fname)

    run(argv)


def INIT():
    printu("Setting up configuration..")

    dname = Glob.path_confdir
    if isdir(dname):
        printu("Config dir '%s' already exists" % dname)
    else:
        exe("mkdir %s" % dname)
        printu("Config dir '%s' created" % dname)

    fname = Glob.path_conffile_default
    if isfile(fname):
        printu("Default config file '%s' already exists" % fname)
    else:
        ls2file(fname, Conf.default())
        printu("Default config file '%s' created" % fname)

    fname = Glob.path_conffile_user_override
    if isfile(fname):
        printu("User override config file '%s' already exists" % fname)
    else:
        ls2file(fname, [""])
        printu("User override config file '%s' created; edit config here" % fname)

    printu("Setting up tagspace..")
    fname = Glob.path_tagspace_default
    if isfile(fname):
        printu("Default tagspace file '%s' already exists" % fname)
    else:
        ls2file(fname, TagTypeHandler.default())
        printu("Default tagspace file '%s' created" % fname)

    printh("\n(For a multi-user setup, a shared tagspace should be used; use the '-TS' command to create one)")


def RESET():
    dname = Glob.path_confdir
    if not isdir(dname):
        printu("Config dir does not exist; nothing to reset")
        return
    exe("rm -rf %s" % dname)
    printu("Config dir and default tagspace deleted; use '-INIT' to re-create")


if __name__ == '__main__':
    try:
        main(sys.argv[1:])
    except ESys as e:
        EXIT("%s" % e)
    except ESysInt as e:
        EXIT_INTERNAL("%s" % e)

