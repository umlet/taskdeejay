import os
import sys

from lib_generic.base import *




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
    print(msg.replace("{EXENAME}", exename()), file=sys.stderr, end="")
    sys.exit(2)




    
