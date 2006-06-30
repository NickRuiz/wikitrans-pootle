#!/usr/bin/python

import sys
sys.path.append('../..') # in case this module is run directly
import doctest

def test_db():
    """

    Let's create a database:

        >>> from Pootle.storage.memory import Database
        >>> db = Database()

    Now we add a language:

        >>> lang = db.add('lt', 'LT')
        >>> lang
        <Language lt-LT>

        >>> db.keys()
        [('lt', 'LT')]
        >>> db.values()
        [<Language lt-LT>]

    """


def test_language():
    """Tests for Language.

        >>> from Pootle.storage.memory import Language, LanguageInfo
        >>> info = LanguageInfo('lt', 'LT')
        >>> lang = Language(info, None)

        >>> proj = lang.add('pootle')
        >>> proj
        <Project pootle>

    """


def test_unitcollection():
    """Tests for UnitCollection.

        >>> from Pootle.storage.memory import UnitCollection
        >>> coll = UnitCollection('web_ui', object())

        >>> tr1 = coll.makeunit(['foo', 'faa'])
        >>> tr2 = coll.makeunit(['boo', 'baa'])
        >>> coll.fill([tr1, tr2])

        >>> len(coll)
        2
        >>> coll[0] == tr1
        True

    """


def test_unit():
    """Tests for UnitCollection.

        >>> from Pootle.storage.memory import TranslationUnit
        >>> unit = TranslationUnit(object(), [('boo', 'baa')])

        >>> unit.trans
        [('boo', 'baa')]

    Let's play around with state:

        >>> unit.unitstate()
        'translated'

        >>> unit.state.add('fuzzy')
        >>> unit.unitstate()
        'fuzzy'

        >>> unit.state.remove('fuzzy')
        >>> unit.trans = [('boo', None)]
        >>> unit.unitstate()
        'untranslated'

    """


def test_interface():
    """Test conformance to the API interface.

    This is a bit buggy.

        >>> from Pootle.storage.api import validateModule
        >>> import Pootle.storage.memory
        >>> validateModule(Pootle.storage.memory, complete=True)

    """


if __name__ == '__main__':
    doctest.testmod()
