#!/usr/bin/env python
"""module to handle consistent file locations for Pootle"""

import os.path
import sys
import imp

def check_if_frozen():
    return (hasattr(sys, "frozen") or # new py2exe
            hasattr(sys, "importers") # old py2exe
            or imp.is_frozen("__main__")) # tools/freeze

is_frozen = check_if_frozen()
# same directory as this file (or the executable under py2exe)
if is_frozen:
  pootledir = os.path.abspath(os.path.dirname(sys.executable))
  jtoolkitdir = os.path.abspath(os.path.dirname(sys.executable))
else:
  from jToolkit import __version__ as jtoolkitversion
  pootledir = os.path.abspath(os.path.dirname(__file__))
  jtoolkitdir = os.path.dirname(jtoolkitversion.__file__)

# default prefs file is pootle.prefs in the pootledir
prefsfile = os.path.join(pootledir, 'pootle.prefs')

htmldir = os.path.join(pootledir, "html")
templatedir = os.path.join(pootledir, "templates")

