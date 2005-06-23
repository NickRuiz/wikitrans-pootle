from Pootle import pootle
from Pootle import pootlefile

def setup_module(module):
    """initialize global variables in the module"""
    parser = pootle.PootleOptionParser()
    options, args = parser.parse_args(["--servertype=dummy"])
    module.server = parser.getserver(options)
    # shortcuts to make tests easier
    module.potree = module.server.potree

def test_init():
    """tests that the index can be initialized"""
    for languagecode, languagename in potree.getlanguages("pootle"):
       translationproject = potree.getproject(languagecode, "pootle")
       assert hasattr(translationproject, "indexdir")

def test_search():
    """tests that the index can be initialized"""
    pass_search = pootlefile.Search(searchtext="login")
    fail_search = pootlefile.Search(searchtext="Zrogny")
    for languagecode, languagename in potree.getlanguages("pootle"):
       translationproject = potree.getproject(languagecode, "pootle")
       print translationproject.indexdir
       assert list(translationproject.searchpoitems("pootle.po", -1, pass_search))
       assert not list(translationproject.searchpoitems("pootle.po", -1, fail_search))

