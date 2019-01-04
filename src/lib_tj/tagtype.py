import shlex

from lib_generic.base import *


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

    @staticmethod
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
        printls(lls2ls(lls, l_align=["<", "^", "<", "<"], delimiter=" | "))

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
