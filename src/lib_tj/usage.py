import os
import sys

from lib_generic.base import *




def usage():
    msg = """
TaskDeejay allows to collaboratively track hierarchical tasks or *issues*.

An issue is simply a directory with some special metadata in it.
Each new or existing directory can be made into a tracked issue.
Issues can then be tagged, e.g., with 'status=todo'.
Issue directories can still contain normal files, for example deliverables, as well as other issues.
(They have unique internal IDs, so renaming directories will not break dependencies.)



START TUTORIAL:

1. First-time setup (only run once):
>{EXENAME} --config-init --tagspace-init                        # set up some tag definitions (a 'tagspace') and editable config files

2. Create and tag an issue:
>mkdir myProject
>{EXENAME} myProject --add                                      # make directory into a tracked issue
>{EXENAME} myProject --set type=project status=inpr             # set some tags
>{EXENAME} myProject --get                                      # get info on issue

3. Create and tag three more issues, faster:
>cd myProject
>{EXENAME} myFirstEpic --add --set type=epic s=inpr
>{EXENAME} mySecondEpic myThirdEpic --add --set t=epic s=todo p=hi o+Barbara

4. List issues:
>{EXENAME} --ls                                                 # list issues (and their tags) in current directory
>{EXENAME} --ls name status id    (or: '--ls n s i')            # the same, but show only some tags 
>{EXENAME} --ll                                                 # more info



USAGE:

Creating issues:
>{EXENAME} <dir1> <dir2> .. --add                               # create issues from directories

Tagging:
>{EXENAME} -ts                                                  # show valids tags for current dir
>{EXENAME} <dir1> <dir2> .. --set <tag1>=<v1> <tag2>=<v2> ..    # tag issues

Reports:
>{EXENAME} --ls                                                 # list issues in current dir with default tags
>{EXENAME} --ls <tag1> <tag2> ..                                # list with specific tags
>{EXENAME} --ll                                                 # list with most tags
>{EXENAME} --get
>{EXENAME} <dir1> <dir2> .. --get status                        # info subset on multiple issues

Command combination/pipe:
>{EXENAME} <dir> --add --set <tag1>=<v1> --get                  # creates, tags, and shows info on issue

Configuration:
>{EXENAME} --config-init --tagspace-init                        # create config dir/file and tagspace
>{EXENAME} --reset                                              # remove config dir

>{EXENAME} --config-get                                         # print config settings
>{EXENAME} --config-set <variable> <value1> [<value2> ..]       # temporarily override config variable
                                  ###TODO### same syntax as tags???
"""
    print(msg.replace("{EXENAME}", exename()), file=sys.stderr, end="")
    sys.exit(2)




    
