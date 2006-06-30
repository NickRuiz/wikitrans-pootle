"""Abstract classes (interfaces) that define the Pootle backend API.

These classes only describe the available operations.  New backends should
implement operations described here.

Fields marked as optional can have the value None.

You can use the function validateModule to check that a set of backend classes
implements the interfaces described here.


Here is a rough sketch of the class containment hierarchy:

    IDatabase
        ILanguage
            IProject
                IUnitCollection
                    ITranslationUnit

"""

# === Helper objects ===

class Interface(object): pass

# Fields
class String(Interface): pass
class Unicode(Interface): pass
class Username(Unicode): pass
class Id(Unicode): pass
class Integer(Interface): pass
class Date(Interface): pass
class Class(Interface): pass


# === API interfaces ===

class IHaveStatistics(Interface):
    """An object that can provide translation statistics."""

    def statistics(self):
        """Return statistics for this object."""
        return IStatistics


class IStatistics(Interface):
    """Statistics."""

    total_strings = Integer
    translated_strings = Integer
    fuzzy_strings = Integer
    # TODO: untranslated, but suggested? other?

    def accum(self, otherstats):
        """Add up statistics from another IStatistics object."""


class IDatabase(IHaveStatistics):

    def keys(self):
        """Get list of available language codes."""
        return [(String, String)]

    def values(self):
        """Get list of available language objects."""
        return [ILanguage]

    def __getitem__(self, (code, country)):
        """Get language object by language code."""
        return ILanguage

    def add(self, code, country):
        """Add a new language."""
        return ILanguage


class ILanguageInfo(Interface):
   """General information about a language."""

   # TODO: Specify if this object could/should be shared between projects.

   code = String # ISO639 language code
   country = String # optional - ISO3166 two-letter country code
   name = Unicode # complete language name (native)
   name_eng = Unicode # complete language name in English; optional TODO needed?
   specialchars = [Unicode] # list of special chars
   nplurals = Integer
   pluralequation = String # optional


class ILanguage(IHaveStatistics):
    """A set of unit collections of a given project in some language."""

    db = IDatabase
    languageinfo = ILanguageInfo
    key = (String, String) # code, country: should be a property that gets
                           # the data from languageinfo; country may be None.

    def keys(self):
        """Get list of available project keys."""
        return [Unicode]

    def values(self):
        """Get list of available project objects."""
        return [IProject]

    def __getitem__(self, projectid):
        """Get project object by project id."""
        return IProject

    def add(self, projectid):
        """Add a new project.

        Creates and returns a project with the given id after adding it to the
        database.
        """
        return IProject


class IProject(IHaveStatistics):
    """An object corresponding to a project.

    This loosely corresponds to a set of .po files for some project.

    A project may have translations to a number of languages, each translation
    divided into unit collections divided into translation units.
    """

    language = ILanguage
    key = Id # project id
    name = Unicode # project name
    description = Unicode # project description (unwrapped)
    checker = [String] # A list of string identifiers for checkers
    # TODO Maybe checkers should belong to unit collections instead?
    template = Interface # IUnitCollection without the actual translations
    # TODO: Have a link to the project's ViewVC page so that we can produce
    #       direct hyperlinks to unit context in the source code.

    def keys(self):
        """Return list of unit collection ids."""
        return [String]

    def values(self):
        """Return list of unit collection objects."""
        return [IUnitCollection]

    def __getitem__(self, name):
        """Get unit collection by id."""
        return IUnitCollection

    def add(self, name):
        """Add a new module."""
        return IUnitCollection

    def statistics(self):
        return IStatistics


class IUnitCollection(IHaveStatistics):
    """A collection of translation units

    This loosely corresponds to a .po file.

    Note that the internal container of translation units is not exposed
    directly so that the implementation can accurately track all changes.

    For efficiency reasons modifications are not recorded immediately.
    Call save() explicitly when you are done modifying the data.
    TODO: is this really needed?
    """

    name = Unicode # the id for this collection
    project = IProject

    def __iter__(self):
        """Return an iterable of translation units."""
        return iter(ITranslationUnit)

    def __len__(self):
        return Integer

    def __getitem__(self, number):
        """Get translation by index (starting from 0)."""
        return IMessage

    def __getslice__(self, start, end):
        """Return a half-open range (by number) of translations.

        This allows slice-notation: collection[0:5] would get the first 5
        units.
        """

    def fill(self, units):
        """Clear the collection and import units from the given iterable."""

    def clear(self):
        """Clear all units from this collection."""

    def save(self):
        """Save the current state of this collection to persistent storage."""
        # TODO: is this really needed if we have 'fill'?

    def makeunit(self, trans):
        """Construct a new translation unit.

        trans is a list of tuples (source, target).
        """

    def statistics(self):
        """Return module statistics."""
        return IStatistics


class ISuggestion(Interface):
    """A suggestion for a particular message.

    The intention of this class is to store an unapproved string, possibly
    submitted by an irregular or even unregistered translator.  The interface
    should offer a convenient way of "upgrading" suggestions to translations.
    """

    unit = None # =ITranslationUnit
    date = Date # submission date
    author = Username # author's user name -- optional


class ITranslationUnit(Interface):
    """A single translatable string."""

    collection = IUnitCollection
    # TODO: store index number in collection?
    suggestions = [ISuggestion]
    context = String # context information

    # Comments: optional; can be multiline, but should be whitespace-stripped
    translator_comments = Unicode
    automatic_comments = Unicode
    reference = Unicode # TODO Should we be smarter here?

    datatype = set([String]) # c-format, no-c-format, java-format, etc.
    state = set([String]) # fuzzy
    # rather low-tech, but I see little wins in using real objects here.

    # Use the XLIFF model here: plural sources are stored together with targets
    # The list of tuples is ordered.  If a plural is not translated, the target
    # in the tuple should be None.  When copying a translation unit from a
    # template, this list may grow if there are >2 plurals.
    trans = [(Unicode,  # plural msgid (source)
              Unicode)] # plural translation (target)

    def unitstate(self):
        """Return the state: one of 'untranslated', 'fuzzy' or 'translated'."""
        # TODO: rename this (must not conflict with self.state)


# === Validation helpers ===

# TODO: I'm reinventing the wheel here, poorly.  I would like to grab a
# real interface package such as zope.interface, but that would be an
# additional dependency.

class ImplementationError(Exception):
    pass


def validateClass(cls, iface):
    """Validate a given class against an interface."""
    for attrname, attr in iface.__dict__.items():
        if attrname.startswith('__'):
            continue # ignore internal attributes

        # Check for existence of the attribute
        try:
            real_attr = getattr(cls, attrname)
        except AttributeError:
            raise ImplementationError('%r does not have %r' % (cls, attrname))

        if isinstance(attr, type) and issubclass(attr, Interface): # attribute
            pass
        elif callable(attr): # method
            if not callable(real_attr):
                raise ImplementationError('%r of %r is not callable'
                                          % (attrname, cls))
            # TODO check signature of callable?
#        else:
#            raise AssertionError("shouldn't happen")


def validateModule(module, complete=False):
    """Check classes in a module against interfaces.

    The classes to be checked should have the atttribute _interface
    pointing to the implemented interface.
    """
    ifaces = set()
    for name, cls in module.__dict__.items():
        if isinstance(cls, type):
            iface = getattr(cls, '_interface', None)
            if iface is not None:
                validateClass(cls, iface)
                ifaces.add(iface)

    if complete:
        pass # TODO: check if all interfaces were implemented at least once?
