from os.path import expanduser


class Glob():
    token_metadir = ".__tj_meta"
    token_id_tag = "_id"
    token_tagspace = "tagspace.txt"
    path_home = expanduser("~")
    name_confdir = ".tj"
    path_confdir = path_home + "/" + name_confdir
    name_conffile = "config.json"
    path_conffile = path_confdir + "/" + name_conffile
    path_tagspace_default = path_confdir + "/" + token_tagspace

