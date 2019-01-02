import json

from lib_generic.base import *


class TypedKeyValue:
    def __init__(self, d_T, d_V):
        self.d_T = d_T
        self.d_V = d_V

    def dumps(self):
        return json.dumps(self.d_V, indent=4, sort_keys=True)

    def get(self, key):
        if key not in self.d_V:  raise ESys("unknown key '%s'" % key)
        return self.d_V[key]

    def set(self, key, ls):
        if key not in self.d_V:  raise ESys("unknown key '%s'" % key)
        if key not in self.d_T:  raise ESysInt("unknown type key '%s'" % key)            
        type = self.d_T[key]
        if type == "ls":
            self.d_V[key] = ls
            return

        if len(ls) != 1:  raise ESys("multiple values not allowed for key '%s'" % key)

        success, v_new = s2x(ls[0], self.d_T[key])
        if not success:  raise ESys(v_new)
        self.d_V[key] = v_new

    def load(self, fname):
        with open(fname) as f:
            tmp = json.load(f)

        for k,v in tmp.items():
            if isinstance(v, list):  ls = [str(x) for x in v]
            else:  ls = [str(v)]
            self.set(k, ls)
