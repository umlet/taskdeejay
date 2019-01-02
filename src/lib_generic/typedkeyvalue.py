import json

from lib_generic.base import *


class TypedKeyValue:
    def __init__(self, d_T, d_V):
        self.d_T = d_T
        self.d_V = d_V

    def dumps(self):
        return json.dumps(self.d_V, indent=4, sort_keys=True)

    def get(self, key):
        if key not in self.d_V:  raise ESys("Unknown global variable '%s'" % key)
        return self.d_V[key]

    def set(self, key, value):
        pass