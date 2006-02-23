#!/usr/bin/env python

from Pootle import pootlefile
from translate.storage import po
from translate.storage import test_po
from translate.filters import pofilter
from translate.misc import wStringIO

class TestPootleUnit(test_po.TestPOUnit):
    UnitClass = pootlefile.pootleelement
    def poparse(self, posource):
        """helper that parses po source without requiring files"""
        dummyfile = wStringIO.StringIO(posource)
        pofile = po.pofile(dummyfile, elementclass=self.UnitClass)
        return pofile

    def test_unquoting(self):
        "Test quoting and unquoting of msgid and msgstr."
        minipo = '''msgid "Tree"
msgstr "Boom"'''
        pofile = self.poparse(minipo)
        unit = pofile.units[0]
        unit.unquotedmsgstr = "setlhare"
        assert unit.getunquotedmsgstr() == ["setlhare"]
        
        minipo = '''msgid "Tree"
msgid_plural "Trees"
msgstr[0] "Boom"
msgstr[1] "Bome"'''
        pofile = self.poparse(minipo)
        unit = pofile.units[0]
        assert unit.getunquotedmsgid() == ["Tree", "Trees"]
        assert unit.getunquotedmsgstr() == ["Boom", "Bome"]
        unit.unquotedmsgstr = ["Umuthi", "Imithi"]
        assert unit.getunquotedmsgstr() == ["Umuthi", "Imithi"]
        unit.unquotedmsgstr = "setlhare"
        assert unit.getunquotedmsgstr() == ["setlhare"]

    def test_classify(self):
        """Test basic classification"""
        dummy_checker = pofilter.POTeeChecker()
        unit = self.UnitClass("Glue")
        classes = unit.classify(dummy_checker)
        assert 'blank' in classes
        unit.target = "Gom"
        classes = unit.classify(dummy_checker)
        assert 'translated' in classes
        unit.markfuzzy()
        classes = unit.classify(dummy_checker)
        assert 'fuzzy' in classes

