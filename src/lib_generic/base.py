import os
import subprocess
import sys




EXENAME = os.path.basename(sys.argv[0])

def exename():
    return EXENAME


def EXIT(text):
    print("ERROR_FATAL: " + EXENAME + ": " + text, file=sys.stderr)
    sys.exit(99)

def EXIT_INTERNAL(text):
    print("ERROR_FATAL_INTERNAL: " + EXENAME + ": " + text, file=sys.stderr)
    sys.exit(199)

def printu(s):  # to suppress ok actions, or to suppress completely in pipe
    print(s)

def printh(s, show):  # to suppress hints
    if show == 1:
        print("(" + s + ")")


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
        if arg.startswith("--"):
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
                print("output file '%s' already exists.." % fname) #todo better output function
            else:
                print("output file '%s' not found; enforcing execution" % fname) #todo better output function
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


#def p(ls):
#    for s in ls:
#        print(s)





