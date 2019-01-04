import os

from os.path import isdir
from os.path import isfile

from lib_tj.globals import *
from lib_tj.tagtype import *


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

