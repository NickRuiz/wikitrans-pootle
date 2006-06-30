"""A backend that stores all the data directly in memory."""

from Pootle.storage.api import IStatistics, IDatabase, ITranslationUnit
from Pootle.storage.api import ILanguageInfo, ILanguage, IProject
from Pootle.storage.api import IUnitCollection, ISuggestion


class Database(object):
    _interface = IDatabase

    def __init__(self):
        self._languages = {}

    def keys(self):
        return self._languages.keys()

    def values(self):
        return self._languages.values()

    def __getitem__(self, key):
        return self._languages[key]

    def add(self, code, country):
        langinfo = LanguageInfo(code=code, country=country)
        lang = Language(langinfo, self)
        self._languages[lang.key] = lang
        return lang

    def statistics(self):
        stats = Statistics()
        for lang in self.values():
            langstats = lang.statistics()
            stats.accum(langstats)
        return stats


class Language(object):

    _interface = ILanguage

    db = None
    languageinfo = None

    def __init__(self, langinfo, db):
        self.db = db
        self.languageinfo = langinfo
        self._projects = {}

    @property
    def key(self):
        info = self.languageinfo
        return (info.code, info.country)

    def __repr__(self):
        country = ''
        if self.languageinfo.country:
            country = '-' + self.languageinfo.country
        return '<Language %s%s>' % (self.languageinfo.code, country)

    def keys(self):
        return self._projects.keys()

    def values(self):
        return self._projects.values()

    def __getitem__(self, projectid):
        return self._projects[key]

    def add(self, projectid):
        project = Project(projectid, self)
        self._projects[project.key] = project
        return project

    def statistics(self):
        stats = Statistics()
        for proj in self.values():
            langstats = proj.statistics()
            stats.accum(projstats)
        return stats


class LanguageInfo(object):

    _interface = ILanguageInfo

    code = None
    country = None
    name = None
    name_eng = None
    specialchars = None
    nplurals = None
    pluralequation = None

    def __init__(self, code, country=None, name=None, name_eng=None,
                 specialchars=None, nplurals=None, pluralequation=None):
        self.code = code
        self.country = country
        self.name = name
        self.name_eng = name_eng
        self.specialchars = specialchars
        self.nplurals = nplurals
        self.pluralequation = pluralequation


class Project(object):
    _interface = IProject

    language = None
    key = None
    name = None
    description = None
    checker = None
    template = None

    def __init__(self, projectid, language):
        self.language = language
        self.key = projectid
        self.name = projectid # until something else is set
        self._collections = {}

    def __repr__(self):
        return '<Project %s>' % self.key

    def keys(self):
        return self._collections.keys()

    def values(self):
        return self._collections.values()

    def __getitem__(self, code):
        return self._collections[code]

    def add(self, name):
        coll = UnitCollection(name, self)
        self._collections[name] = coll
        return coll

    def statistics(self):
        stats = Statistics()
        for coll in self.values():
            collstats = coll.statistics()
            stats.accum(collstats)
        return stats


class UnitCollection(object):
    _interface = IUnitCollection

    name = None
    project = None

    def __init__(self, name, project):
        self.name = name
        self.project = project
        self._units = []

    def __iter__(self):
        return iter(self._units)

    def __len__(self):
        return len(self._units)

    def __getitem__(self, number):
        return self._units[number]

    def __getslice__(self, start, end):
        return self._units[start:end]

    def fill(self, units):
        for unit in units:
            self._units.append(unit)

    def clear(self):
        del self._units[:]

    def save(self):
        raise NotImplementedError()

    def statistics(self):
        stats = Statistics()
        for unit in self.values():
            stats.total_strings += len(unit.trans)
            state = unit.unitstate()
            if state == 'translated':
                stats.translated_strings += len(unit.trans)
            elif state == 'fuzzy':
                stats.fuzzy_strings += len(unit.trans)
        return stats

    def makeunit(self, trans):
        """See TranslationUnit.__init__."""
        return TranslationUnit(self, trans)


class Suggestion(object):

    _interface = ISuggestion

    unit = None
    date = None
    author = None

    def __init__(self, unit, date, author):
        self.unit = unit
        self.date = date
        self.author = author


class TranslationUnit(object):

    collection = None
    suggestions = None
    context = None

    translator_comments = None
    automatic_comments = None
    reference = None

    datatype = set()
    state = set()

    trans = None

    def __init__(self, collection, trans):
        """Construct a TranslationUnit.

        trans should be a list of tuples (source, target).
        """
        self.collection = collection
        self.trans = trans
        # TODO: check that len(trans) == language.nplurals?

    def unitstate(self):
        if 'fuzzy' in self.state:
            return 'fuzzy'
        for source, target in self.trans:
            if target is None:
                return 'untranslated'
        return 'translated'


class Statistics(object):
    _interface = IStatistics

    total_strings = None
    translated_strings = None
    fuzzy_strings = None

    def __init__(self, total_strings=0, translated_strings=0, fuzzy_strings=0):
        self.total_strings = total_strings
        self.translated_strings = translated_strings
        self.fuzzy_strings = fuzzy_strings

    def accum(self, otherstats):
        self.total_strings += otherstats.total_strings
        self.translated_strings += otherstats.translated_strings
        self.fuzzy_strings += otherstats.fuzzy_strings
