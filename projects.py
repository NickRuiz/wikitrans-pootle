#!/usr/bin/env python

"""manages projects and files and translations"""

from translate.storage import po
from translate.filters import checks
from translate.filters import pofilter
from translate.convert import po2csv
from translate.convert import pot2po
from translate.tools import pogrep
from Pootle import pootlefile
from Pootle import versioncontrol
from jToolkit import timecache
from jToolkit import prefs
import time
import os
import cStringIO
try:
  import PyLucene
except:
  PyLucene = None

class RightsError(ValueError):
  pass

class InternalAdminSession:
  """A fake session used for doing internal admin jobs"""
  def __init__(self):
    self.username = "internal"
    self.isopen = True

  def localize(self, message):
    return message

  def issiteadmin(self):
    return True

class potimecache(timecache.timecache):
  """caches pootlefile objects, remembers time, and reverts back to statistics when neccessary..."""
  def __init__(self, expiryperiod, project):
    """initialises the cache to keep objects for the given expiryperiod, and point back to the project"""
    timecache.timecache.__init__(self, expiryperiod)
    self.project = project

  def __getitem__(self, key):
    """[] access of items"""
    if key and not dict.__contains__(self, key):
      popath = os.path.join(self.project.podir, key)
      if os.path.exists(popath):
        # update the index to pofiles...
        self.project.scanpofiles()
    return timecache.timecache.__getitem__(self, key)

  def expire(self, pofilename):
    """expires the given pofilename by recreating it (holding only stats)"""
    timestamp, currentfile = dict.__getitem__(self, pofilename)
    if currentfile.pomtime is not None:
      # use the currentfile.pomtime as a timestamp as well, so any modifications will extend its life
      if time.time() - currentfile.pomtime > self.expiryperiod.seconds:
        self.__setitem__(pofilename, pootlefile.pootlefile(self.project, pofilename))

class TranslationProject:
  """Manages iterating through the translations in a particular project"""
  def __init__(self, languagecode, projectcode, potree, create=False):
    self.languagecode = languagecode
    self.projectcode = projectcode
    self.potree = potree
    self.languagename = self.potree.getlanguagename(self.languagecode)
    self.projectname = self.potree.getprojectname(self.projectcode)
    self.projectdescription = self.potree.getprojectdescription(self.projectcode)
    self.pofiles = potimecache(15*60, self)
    self.projectcheckerstyle = self.potree.getprojectcheckerstyle(self.projectcode)
    checkerclasses = [checks.projectcheckers.get(self.projectcheckerstyle, checks.StandardChecker), pofilter.StandardPOChecker]
    self.checker = pofilter.POTeeChecker(checkerclasses=checkerclasses, errorhandler=self.filtererrorhandler)
    if create:
      self.converttemplates(InternalAdminSession())
    self.podir = potree.getpodir(languagecode, projectcode)
    if self.potree.hasgnufiles(self.podir, self.languagecode):
      self.filestyle = "gnu"
    else:
      self.filestyle = "std"
    self.readprefs()
    self.scanpofiles()
    self.initindex()

  def readprefs(self):
    """reads the project preferences"""
    self.prefs = prefs.PrefsParser()
    self.prefsfile = os.path.join(self.podir, "pootle-%s-%s.prefs" % (self.projectcode, self.languagecode))
    if not os.path.exists(self.prefsfile):
      prefsfile = open(self.prefsfile, "w")
      prefsfile.write("# Pootle preferences for project %s, language %s\n\n" % (self.projectcode, self.languagecode))
      prefsfile.close()
    self.prefs.parsefile(self.prefsfile)

  def saveprefs(self):
    """saves the project preferences"""
    self.prefs.savefile()

  def getrightnames(self, session):
    """gets the available rights and their localized names"""
    localize = session.localize
    return [("view", localize("View")),
            ("suggest", localize("Suggest")),
            ("translate", localize("Translate")),
            ("review", localize("Review")),
            ("archive", localize("Archive")),
            ("pocompile", localize("Compile PO files")),
            ("assign", localize("Assign")),
            ("admin", localize("Administrate")),
           ]

  def getrights(self, session=None, username=None):
    """gets the rights for the given user (name or session, or not-logged-in if username is None)"""
    # internal admin sessions have all rights
    if isinstance(session, InternalAdminSession):
      return [right for right, localizedright in self.getrightnames(session)]
    if session is not None and session.isopen and username is None:
      username = session.username
    if hasattr(self.prefs, "rights"):
      rights = self.prefs.rights
    else:
      rights = None
    if username is None:
      rights = getattr(rights, "nobody", "view")
    else:
      rights = getattr(rights, username, getattr(rights, "default", None))
      if rights is None:
        if self.languagecode == "en":
          rights = "view, archive, pocompile"
        else:
          rights = "view, review, translate, archive, pocompile"
    rights = [right.strip() for right in rights.split(",")]
    if session is not None and session.issiteadmin():
      if "admin" not in rights:
        rights.append("admin")
    return rights

  def setrights(self, username, rights):
    """sets the rights for the given username... (or not-logged-in if username is None)"""
    if username is None: username = "nobody"
    if isinstance(rights, list):
      rights = ", ".join(rights)
    if not hasattr(self.prefs, "rights"):
      self.prefs.rights = prefs.PrefNode(self.prefs, "rights")
    setattr(self.prefs.rights, username, rights)
    self.saveprefs()

  def delrights(self, username):
    """deletes teh rights for the given username"""
    if username == "nobody" or username == "default":
      raise RightsError(session.localize('You cannot remove the "nobody" or "default" user'))
    delattr(self.prefs.rights, username)
    self.saveprefs()

  def getgoalnames(self):
    """gets the goals and associated files for the project"""
    goals = getattr(self.prefs, "goals", {})
    goallist = []
    for goalname, goalnode in goals.iteritems():
      goallist.append(goalname)
    goallist.sort()
    return goallist

  def getgoalfiles(self, goalname, dirfilter=None):
    """gets the files for the given goal"""
    goals = getattr(self.prefs, "goals", {})
    for testgoalname, goalnode in goals.iteritems():
      if goalname != testgoalname: continue
      goalfiles = getattr(goalnode, "files", "")
      goalfiles = [goalfile.strip() for goalfile in goalfiles.split(",") if goalfile.strip()]
      if dirfilter:
        if not dirfilter.endswith(os.path.sep) and not dirfilter.endswith(os.path.extsep + "po"):
          dirfilter += os.path.sep
        goalfiles = [goalfile for goalfile in goalfiles if goalfile.startswith(dirfilter)]
      return goalfiles
    return []

  def getfilegoals(self, filename):
    """gets the goals the given file is part of"""
    goals = getattr(self.prefs, "goals", {})
    filegoals = []
    ancestry = []
    parts = filename.split(os.path.sep)
    for i in range(1, len(parts)):
      ancestor = os.path.join(*parts[:i]) + os.path.sep
      ancestry.append(ancestor)
    for goalname, goalnode in goals.iteritems():
      goalfiles = getattr(goalnode, "files", "")
      goalfiles = [goalfile.strip() for goalfile in goalfiles.split(",") if goalfile.strip()]
      if filename in goalfiles:
        filegoals.append(goalname)
        continue
      for ancestor in ancestry:
        if ancestor in goalfiles:
          filegoals.append(goalname)
          continue
    return filegoals

  def setfilegoals(self, session, goalnames, filename):
    """sets the given file to belong to the given goals exactly"""
    filegoals = self.getfilegoals(filename)
    for othergoalname in filegoals:
      if othergoalname not in goalnames:
        self.removefilefromgoal(session, othergoalname, filename)
    for goalname in goalnames:
      goalfiles = self.getgoalfiles(goalname)
      if filename not in goalfiles:
        goalfiles.append(filename)
        self.setgoalfiles(session, goalname, goalfiles)

  def removefilefromgoal(self, session, goalname, filename):
    """removes the given file from the goal"""
    goalfiles = self.getgoalfiles(goalname)
    if filename in goalfiles:
      goalfiles.remove(filename)
      self.setgoalfiles(session, goalname, goalfiles)

  def setgoalfiles(self, session, goalname, goalfiles):
    """sets the goalfiles for the given goalname"""
    if "admin" not in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to alter goals here"))
    if isinstance(goalfiles, list):
      goalfiles = [goalfile.strip() for goalfile in goalfiles if goalfile.strip()]
      goalfiles = ", ".join(goalfiles)
    if not hasattr(self.prefs, "goals"):
      self.prefs.goals = prefs.PrefNode(self.prefs, "goals")
    if not hasattr(self.prefs.goals, goalname):
      # TODO: check that its a valid goalname (alphanumeric etc)
      setattr(self.prefs.goals, goalname, prefs.PrefNode(self.prefs.goals, goalname))
    goalnode = getattr(self.prefs.goals, goalname)
    goalnode.files = goalfiles
    self.saveprefs()

  def getgoalusers(self, goalname):
    """gets the users for the given goal"""
    goals = getattr(self.prefs, "goals", {})
    for testgoalname, goalnode in goals.iteritems():
      if goalname != testgoalname: continue
      goalusers = getattr(goalnode, "users", "")
      goalusers = [goaluser.strip() for goaluser in goalusers.split(",") if goaluser.strip()]
      return goalusers
    return []

  def getusergoals(self, username):
    """gets the goals the given user is part of"""
    goals = getattr(self.prefs, "goals", {})
    usergoals = []
    for goalname, goalnode in goals.iteritems():
      goalusers = getattr(goalnode, "users", "")
      goalusers = [goaluser.strip() for goaluser in goalusers.split(",") if goaluser.strip()]
      if username in goalusers:
        usergoals.append(goalname)
        continue
    return usergoals

  def addusertogoal(self, session, goalname, username, exclusive=False):
    """adds the given user to the goal"""
    if exclusive:
      usergoals = self.getusergoals(username)
      for othergoalname in usergoals:
        if othergoalname != goalname:
          self.removeuserfromgoal(session, othergoalname, username)
    goalusers = self.getgoalusers(goalname)
    if username not in goalusers:
      goalusers.append(username)
      self.setgoalusers(session, goalname, goalusers)

  def removeuserfromgoal(self, session, goalname, username):
    """removes the given user from the goal"""
    goalusers = self.getgoalusers(goalname)
    if username in goalusers:
      goalusers.remove(username)
      self.setgoalusers(session, goalname, goalusers)

  def setgoalusers(self, session, goalname, goalusers):
    """sets the goalusers for the given goalname"""
    if "admin" not in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to alter goals here"))
    if isinstance(goalusers, list):
      goalusers = [goaluser.strip() for goaluser in goalusers if goaluser.strip()]
      goalusers = ", ".join(goalusers)
    if not hasattr(self.prefs, "goals"):
      self.prefs.goals = prefs.PrefNode(self.prefs, "goals")
    if not hasattr(self.prefs.goals, goalname):
      setattr(self.prefs.goals, goalname, prefs.PrefNode(self.prefs.goals, goalname))
    goalnode = getattr(self.prefs.goals, goalname)
    goalnode.users = goalusers
    self.saveprefs()

  def scanpofiles(self):
    """sets the list of pofilenames by scanning the project directory"""
    self.pofilenames = self.potree.getpofiles(self.languagecode, self.projectcode)
    for pofilename in self.pofilenames:
      if not pofilename in self.pofiles:
        self.pofiles[pofilename] = pootlefile.pootlefile(self, pofilename)
    # remove any files that have been deleted since initialization
    for pofilename in self.pofiles.keys():
      if not pofilename in self.pofilenames:
        del self.pofiles[pofilename]

  def getuploadpath(self, dirname, pofilename):
    """gets the path of a po file being uploaded securely, creating directories as neccessary"""
    if os.path.isabs(dirname) or dirname.startswith("."):
      raise ValueError("invalid/insecure file path: %s" % dirname)
    if os.path.basename(pofilename) != pofilename or pofilename.startswith("."):
      raise ValueError("invalid/insecure file name: %s" % pofilename)
    if self.filestyle == "gnu":
      if not self.potree.languagematch(self.languagecode, pofilename[:-len(".po")]):
        raise ValueError("invalid GNU-style file name %s: must match '%s.po' or '%s[_-][A-Z]{2,3}.po'" % (pofilename, self.languagecode, self.languagecode))
    dircheck = self.podir
    for part in dirname.split(os.sep):
      dircheck = os.path.join(dircheck, part)
      if dircheck and not os.path.isdir(dircheck):
        os.mkdir(dircheck)
    return os.path.join(self.podir, dirname, pofilename)  

  def uploadpofile(self, session, dirname, pofilename, contents):
    """uploads an individual PO files"""
    pathname = self.getuploadpath(dirname, pofilename)
    if os.path.exists(pathname):
      origpofile = self.getpofile(os.path.join(dirname, pofilename))
      newpofile = po.pofile()
      infile = cStringIO.StringIO(contents)
      newpofile.parse(infile)
      if "admin" in self.getrights(session):
        origpofile.mergefile(newpofile, session.username)
      elif "translate" in self.getrights(session):
        origpofile.mergefile(newpofile, session.username, allownewstrings=False)
      else:
        raise RightsError(session.localize("You do not have rights to upload files here"))
    else:
      if "admin" not in self.getrights(session):
        raise RightsError(session.localize("You do not have rights to upload new files here"))
      outfile = open(pathname, "wb")
      outfile.write(contents)
      outfile.close()
      self.scanpofiles()

  def updatepofile(self, session, dirname, pofilename):
    """updates an individual PO file from version control"""
    if "admin" not in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to update files here"))
    pathname = self.getuploadpath(dirname, pofilename)
    # read from version control
    if os.path.exists(pathname):
      popath = os.path.join(dirname, pofilename)
      currentpofile = self.getpofile(popath)
      # reading BASE version of file
      origcontents = versioncontrol.getcleanfile(pathname, "BASE")
      origpofile = pootlefile.pootlefile(self, popath)
      originfile = cStringIO.StringIO(origcontents)
      origpofile.parse(originfile)
      # matching current file with BASE version
      matches = origpofile.matchitems(currentpofile, usesources=False)
      # TODO: add some locking here...
      # reading new version of file
      versioncontrol.updatefile(pathname)
      newpofile = pootlefile.pootlefile(self, popath)
      newpofile.pofreshen()
      if not hasattr(newpofile, "msgidindex"):
        newpofile.makeindex()
      newmatches = []
      # sorting through old matches
      for origpo, localpo in matches:
        # we need to find the corresponding newpo to see what to merge
        if localpo is None:
          continue
        if origpo is None:
          # if it wasn't in the original, then use the addition for searching
          origpo = localpo
        else:
          origmsgstr = po.unquotefrompo(origpo.msgstr, False)
          localmsgstr = po.unquotefrompo(localpo.msgstr, False)
          if origmsgstr == localmsgstr:
            continue
        foundsource = False
        if usesources:
          for source in origpo.getsources():
            if source in newpofile.sourceindex:
              newpo = newpofile.sourceindex[source]
              if newpo is not None:
                foundsource = True
                newmatches.append((newpo, localpo))
                continue
        if not foundsource:
          msgid = po.getunquotedstr(origpo.msgid)
          if msgid in newpofile.msgidindex:
            newpo = newpofile.msgidindex[msgid]
            newmatches.append((newpo, localpo))
          else:
            newmatches.append((None, localpo))
      # finding new matches
      for newpo, localpo in newmatches:
        if newpo is None:
          # TODO: include localpo as obsolete
          continue
        if localpo is None:
          continue
        newpofile.mergeitem(newpo, localpo, "versionmerge")
      # saving
      newpofile.savepofile()
      self.pofiles[pofilename] = newpofile
      # recalculate everything
      newpofile.readpofile()
    else:
      versioncontrol.updatefile(pathname)
      self.scanpofiles()

  def converttemplates(self, session):
    """creates PO files from the templates"""
    projectdir = os.path.join(self.potree.podirectory, self.projectcode)
    templatesdir = os.path.join(projectdir, "templates")
    if not os.path.exists(templatesdir):
      templatesdir = os.path.join(projectdir, "pot")
      if not os.path.exists(templatesdir):
        templatesdir = projectdir
    if self.potree.isgnustyle(self.projectcode):
      self.filestyle = "gnu"
    else:
      self.filestyle = "std"
    templates = self.potree.gettemplates(self.projectcode)
    if self.filestyle == "gnu":
      self.podir = projectdir
      if not templates:
        raise NotImplementedError("Cannot create GNU-style translation project without templates")
    else:
      self.podir = os.path.join(projectdir, self.languagecode)
      if not os.path.exists(self.podir):
        os.mkdir(self.podir)
    for potfilename in templates:
      inputfile = open(os.path.join(templatesdir, potfilename), "rb")
      outputfile = cStringIO.StringIO()
      pot2po.convertpot(inputfile, outputfile, None)
      dirname, potfilename = os.path.dirname(potfilename), os.path.basename(potfilename)
      if self.filestyle == "gnu":
        pofilename = self.languagecode + os.extsep + "po"
      else:
        pofilename = potfilename[:-len(os.extsep+"pot")] + os.extsep + "po"
      self.uploadpofile(session, dirname, pofilename, outputfile.getvalue())

  def filtererrorhandler(self, functionname, str1, str2, e):
    print "error in filter %s: %r, %r, %s" % (functionname, str1, str2, e)
    return False

  def getarchive(self, pofilenames):
    """returns an archive of the given filenames"""
    tempzipfile = os.tmpnam()
    try:
      # using zip command line is fast
      os.system("cd %s ; zip -r - %s > %s" % (self.podir, " ".join(pofilenames), tempzipfile))
      return open(tempzipfile, "r").read()
    finally:
      if os.path.exists(tempzipfile):
        os.remove(tempzipfile)
    # but if it doesn't work, we can do it from python
    import zipfile
    archivecontents = cStringIO.StringIO()
    archive = zipfile.ZipFile(archivecontents, 'w', zipfile.ZIP_DEFLATED)
    for pofilename in pofilenames:
      pofile = self.getpofile(pofilename)
      archive.write(pofile.filename, pofilename)
    archive.close()
    return archivecontents.getvalue()

  def uploadarchive(self, session, dirname, archivecontents):
    """uploads the files inside the archive"""
    try:
      tempzipfile = os.tmpnam()
      # using zip command line is fast
      # os.system("cd %s ; zip -r - %s > %s" % (self.podir, " ".join(pofilenames), tempzipfile))
      # return open(tempzipfile, "r").read()
      pass
    finally:
      if os.path.exists(tempzipfile):
        os.remove(tempzipfile)
    # but if it doesn't work, we can do it from python
    import zipfile
    archivefile = cStringIO.StringIO(archivecontents)
    archive = zipfile.ZipFile(archivefile, 'r')
    # TODO: find a better way to return errors...
    for filename in archive.namelist():
      if not filename.endswith(os.extsep + "po"):
        print "error adding %s: not a .po file" % filename
        continue
      contents = archive.read(filename)
      subdirname, pofilename = os.path.dirname(filename), os.path.basename(filename)
      try:
        # TODO: use zipfile info to set the time and date of the file
        self.uploadpofile(session, os.path.join(dirname, subdirname), pofilename, contents)
      except ValueError, e:
        print "error adding %s" % filename, e
        continue
    archive.close()

  def browsefiles(self, dirfilter=None, depth=None, maxdepth=None, includedirs=False, includefiles=True):
    """gets a list of pofilenames, optionally filtering with the parent directory"""
    if dirfilter is None:
      pofilenames = self.pofilenames
    else:
      if not dirfilter.endswith(os.path.sep) and not dirfilter.endswith(os.path.extsep + "po"):
        dirfilter += os.path.sep
      pofilenames = [pofilename for pofilename in self.pofilenames if pofilename.startswith(dirfilter)]
    if includedirs:
      podirs = {}
      for pofilename in pofilenames:
        dirname = os.path.dirname(pofilename)
	if not dirname:
	  continue
        podirs[dirname] = True
	while dirname:
	  dirname = os.path.dirname(dirname)
	  if dirname:
	    podirs[dirname] = True
      podirs = podirs.keys()
    else:
      podirs = []
    if not includefiles:
      pofilenames = []
    if maxdepth is not None:
      pofilenames = [pofilename for pofilename in pofilenames if pofilename.count(os.path.sep) <= maxdepth]
      podirs = [podir for podir in podirs if podir.count(os.path.sep) <= maxdepth]
    if depth is not None:
      pofilenames = [pofilename for pofilename in pofilenames if pofilename.count(os.path.sep) == depth]
      podirs = [podir for podir in podirs if podir.count(os.path.sep) == depth]
    return pofilenames + podirs

  def iterpofilenames(self, lastpofilename=None, includelast=False):
    """iterates through the pofilenames starting after the given pofilename"""
    if lastpofilename is None:
      index = 0
    else:
      index = self.pofilenames.index(lastpofilename)
      if not includelast:
        index += 1
    while index < len(self.pofilenames):
      yield self.pofilenames[index]
      index += 1

  def initindex(self):
    """initializes the search index"""
    if PyLucene is None:
      return
    self.indexdir = os.path.join(self.podir, ".poindex-%s-%s" % (self.projectcode, self.languagecode))
    self.analyzer = PyLucene.StandardAnalyzer()
    if not os.path.exists(self.indexdir):
      os.mkdir(self.indexdir)
      self.indexstore = PyLucene.FSDirectory.getDirectory(self.indexdir, True)
      writer = PyLucene.IndexWriter(self.indexstore, self.analyzer, True)
      writer.close()
    else:
      self.indexstore = PyLucene.FSDirectory.getDirectory(self.indexdir, False)
    self.indexreader = PyLucene.IndexReader.open(self.indexstore)
    self.searcher = PyLucene.IndexSearcher(self.indexreader)
    addlist, deletelist = [], []
    for pofilename in self.pofiles:
      self.updateindex(pofilename, addlist, deletelist)
    # TODO: this is all unneccessarily complicated, there must be a simpler way.
    if deletelist:
      for docid in deletelist:
        self.indexreader.deleteDocument(docid)
      self.searcher.close()
      self.indexreader.close()
    if addlist:
      self.indexwriter = PyLucene.IndexWriter(self.indexstore, self.analyzer, False)
      for doc in addlist:
        self.indexwriter.addDocument(doc)
      self.indexwriter.optimize(True)
      self.indexwriter.close()
    if deletelist:
      self.indexreader = PyLucene.IndexReader.open(self.indexstore)
      self.searcher = PyLucene.IndexSearcher(self.indexreader)

  def updateindex(self, pofilename, addlist, deletelist):
    """updates the index with the contents of pofilename"""
    if PyLucene is None:
      return
    needsupdate = True
    pofile = self.pofiles[pofilename]
    presencecheck = PyLucene.QueryParser.parse(pofilename, "filename", self.analyzer)
    hits = self.searcher.search(presencecheck)
    pomtime = pootlefile.getmodtime(pofile.filename)
    for hit in xrange(hits.length()):
      doc = hits.doc(hit)
      if doc.get("pomtime") == str(pomtime):
        needsupdate = False
    if needsupdate:
      # TODO: update this to index items individually rather than the whole file
      for hit in xrange(hits.length()):
        docid = hits.id(hit)
        deletelist.append(docid)
      pofile.pofreshen()
      doc = PyLucene.Document()
      doc.add(PyLucene.Field("filename", pofilename, True, True, True))
      doc.add(PyLucene.Field("pomtime", str(pomtime), True, True, True))
      allorig, alltrans = [], []
      for thepo in pofile.transelements:
        orig, trans = self.unquotefrompo(thepo.msgid), self.unquotefrompo(thepo.msgstr)
        allorig.append(orig)
        alltrans.append(trans)
      allorig = "\n".join(allorig)
      alltrans = "\n".join(alltrans)
      doc.add(PyLucene.Field("orig", allorig, False, True, True))
      doc.add(PyLucene.Field("trans", alltrans, False, True, True))
      addlist.append(doc)

  def matchessearch(self, pofilename, search):
    """returns whether any items in the pofilename match the search (based on collected stats etc)"""
    if search.dirfilter is not None and not pofilename.startswith(search.dirfilter):
      return False
    if search.assignedto or search.assignedaction:
      assigns = self.pofiles[pofilename].getassigns()
      if search.assignedto is not None:
        if search.assignedto not in assigns:
          return False
        assigns = assigns[search.assignedto]
      else:
        assigns = reduce(lambda x, y: x+y, [userassigns.keys() for userassigns in assigns.values()], [])
      if search.assignedaction is not None:
        if search.assignedaction not in assigns:
          return False
    if search.matchnames:
      postats = self.getpostats(pofilename)
      matches = False
      for name in search.matchnames:
        if postats[name]:
          matches = True
      if not matches:
        return False
    if PyLucene and search.searchtext:
      # TODO: move this up a level, use index to manage whole search
      origquery = PyLucene.QueryParser.parse(search.searchtext, "orig", self.analyzer)
      transquery = PyLucene.QueryParser.parse(search.searchtext, "trans", self.analyzer)
      textquery = PyLucene.BooleanQuery()
      textquery.add(origquery, False, False)
      textquery.add(transquery, False, False)
      hits = self.searcher.search(textquery)
      for hit in xrange(hits.length()):
        if hits.doc(hit).get("filename") == pofilename:
          return True
      return False
    return True

  def searchpofilenames(self, lastpofilename, search, includelast=False):
    """find the next pofilename that has items matching the given search"""
    if lastpofilename and not lastpofilename in self.pofiles:
      # accessing will autoload this file...
      self.pofiles[lastpofilename]
    for pofilename in self.iterpofilenames(lastpofilename, includelast):
      if self.matchessearch(pofilename, search):
        yield pofilename

  def searchpoitems(self, pofilename, item, search):
    """finds the next item matching the given search"""
    if search.searchtext:
      pogrepfilter = pogrep.pogrepfilter(search.searchtext, None, ignorecase=True)
    for pofilename in self.searchpofilenames(pofilename, search, includelast=True):
      pofile = self.getpofile(pofilename)
      for item in pofile.iteritems(search, item):
        # TODO: move this to iteritems
        if search.searchtext:
          thepo = pofile.transelements[item]
          if pogrepfilter.filterelement(thepo):
            yield pofilename, item
        else:
          yield pofilename, item

  def assignpoitems(self, session, search, assignto, action):
    """assign all the items matching the search to the assignto user with the given action"""
    if not "assign" in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to alter assignments here"))
    if search.searchtext:
      pogrepfilter = pogrep.pogrepfilter(search.searchtext, None, ignorecase=True)
    assigncount = 0
    for pofilename in self.searchpofilenames(None, search, includelast=True):
      pofile = self.getpofile(pofilename)
      for item in pofile.iteritems(search, None):
        # TODO: move this to iteritems
        if search.searchtext:
          thepo = pofile.transelements[item]
          if pogrepfilter.filterelement(thepo):
            pofile.assignto(item, assignto, action)
            assigncount += 1
        else:
          pofile.assignto(item, assignto, action)
          assigncount += 1
    return assigncount

  def unassignpoitems(self, session, search, assignedto, action=None):
    """unassigns all the items matching the search to the assignedto user"""
    if not "assign" in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to alter assignments here"))
    if search.searchtext:
      pogrepfilter = pogrep.pogrepfilter(search.searchtext, None, ignorecase=True)
    assigncount = 0
    for pofilename in self.searchpofilenames(None, search, includelast=True):
      pofile = self.getpofile(pofilename)
      for item in pofile.iteritems(search, None):
        # TODO: move this to iteritems
        if search.searchtext:
          thepo = pofile.transelements[item]
          if pogrepfilter.filterelement(thepo):
            pofile.unassign(item, assignedto, action)
            assigncount += 1
        else:
          pofile.unassign(item, assignedto, action)
          assigncount += 1
    return assigncount

  def calculatestats(self, pofilenames=None):
    """calculates translation statistics for the given po files (or all if None given)"""
    totalstats = {}
    if pofilenames is None:
      pofilenames = self.pofilenames
    for pofilename in pofilenames:
      if not pofilename or os.path.isdir(pofilename):
        continue
      postats = self.getpostats(pofilename)
      for name, count in postats.iteritems():
        totalstats[name] = totalstats.get(name, 0) + count
      assignstats = self.getassignstats(pofilename)
      for name, count in assignstats.iteritems():
        totalstats["assign-"+name] = totalstats.get("assign-"+name, 0) + count
    return totalstats

  def track(self, pofilename, item, message):
    """sends a track message to the pofile"""
    self.pofiles[pofilename].track(item, message)

  def gettracks(self, pofilenames=None):
    """calculates translation statistics for the given po files (or all if None given)"""
    alltracks = []
    if pofilenames is None:
      pofilenames = self.pofilenames
    for pofilename in pofilenames:
      if not pofilename or os.path.isdir(pofilename):
        continue
      tracker = self.pofiles[pofilename].tracker
      items = tracker.keys()
      items.sort()
      for item in items:
        alltracks.append("%s item %d: %s" % (pofilename, item, tracker[item]))
    return alltracks

  def getpostats(self, pofilename):
    """calculates translation statistics for the given po file"""
    return self.pofiles[pofilename].getstats()

  def getassignstats(self, pofilename):
    """calculates translation statistics for the given po file"""
    assigns = self.pofiles[pofilename].getassigns()
    assignstats = {}
    for username, userassigns in assigns.iteritems():
      count = 0
      for action, items in userassigns.iteritems():
        count += len(items)
      assignstats[username] = count
    return assignstats

  def getpofile(self, pofilename):
    """parses the file into a pofile object and stores in self.pofiles"""
    pofile = self.pofiles[pofilename]
    pofile.pofreshen()
    return pofile

  def getpofilelen(self, pofilename):
    """returns number of items in the given pofilename"""
    # TODO: needn't parse the file for this ...
    pofile = self.getpofile(pofilename)
    return len(pofile.transelements)

  def getitem(self, pofilename, item):
    """returns a particular item from a particular po file's orig, trans strings as a tuple"""
    pofile = self.getpofile(pofilename)
    thepo = pofile.transelements[item]
    orig, trans = self.unquotefrompo(thepo.msgid), self.unquotefrompo(thepo.msgstr)
    return orig, trans

  def getitemclasses(self, pofilename, item):
    """returns which classes this item belongs to"""
    # TODO: needn't parse the file for this ...
    pofile = self.getpofile(pofilename)
    return [classname for (classname, classitems) in pofile.classify.iteritems() if item in classitems]

  def unquotefrompo(self, postr):
    """extracts a po-quoted string to normal text"""
    # TODO: handle plurals properly
    if isinstance(postr, dict):
      pokeys = postr.keys()
      pokeys.sort()
      return self.unquotefrompo(postr[pokeys[0]])
    return po.unquotefrompo(postr)

  def quoteforpo(self, text):
    """quotes text in po-style"""
    text = text.replace("\r\n", "\n")
    return po.quoteforpo(text)

  def getitems(self, pofilename, itemstart, itemstop):
    """returns a set of items from the pofile, converted to original and translation strings"""
    pofile = self.getpofile(pofilename)
    elements = pofile.transelements[max(itemstart,0):itemstop]
    return [(self.unquotefrompo(poel.msgid), self.unquotefrompo(poel.msgstr)) for poel in elements]

  def updatetranslation(self, pofilename, item, trans, session):
    """updates a translation with a new value..."""
    if "translate" not in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to change translations here"))
    newmsgstr = self.quoteforpo(trans)
    pofile = self.pofiles[pofilename]
    pofile.track(item, "edited by %s" % session.username)
    pofile.setmsgstr(item, newmsgstr, session.prefs)

  def suggesttranslation(self, pofilename, item, trans, session):
    """stores a new suggestion for a translation..."""
    if "suggest" not in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to suggest changes here"))
    suggmsgstr = self.quoteforpo(trans)
    pofile = self.getpofile(pofilename)
    pofile.track(item, "suggestion made by %s" % session.username)
    pofile.addsuggestion(item, suggmsgstr, session.username)

  def getsuggestions(self, pofile, item):
    """find all the suggestions submitted for the given (pofile or pofilename) and item"""
    if isinstance(pofile, (str, unicode)):
      pofilename = pofile
      pofile = self.getpofile(pofilename)
    suggestpos = pofile.getsuggestions(item)
    suggestions = [self.unquotefrompo(suggestpo.msgstr) for suggestpo in suggestpos]
    return suggestions

  def acceptsuggestion(self, pofile, item, suggitem, newtrans, session):
    """accepts the suggestion into the main pofile"""
    if not "review" in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to review suggestions here"))
    if isinstance(pofile, (str, unicode)):
      pofilename = pofile
      pofile = self.getpofile(pofilename)
    pofile.track(item, "suggestion by %s accepted by %s" % (self.getsuggester(pofile, item, suggitem), session.username))
    pofile.deletesuggestion(item, suggitem)
    self.updatetranslation(pofilename, item, newtrans, session)

  def getsuggester(self, pofile, item, suggitem):
    """returns who suggested the given item's suggitem if recorded, else None"""
    if isinstance(pofile, (str, unicode)):
      pofilename = pofile
      pofile = self.getpofile(pofilename)
    suggestionpo = pofile.getsuggestions(item)[suggitem]
    for msgidcomment in suggestionpo.msgidcomments:
      if msgidcomment.find("suggested by ") != -1:
        suggestedby = po.getunquotedstr([msgidcomment]).replace("_:", "", 1).replace("suggested by ", "", 1).strip()
        return suggestedby
    return None

  def rejectsuggestion(self, pofile, item, suggitem, newtrans, session):
    """rejects the suggestion and removes it from the pending file"""
    if not "review" in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to review suggestions here"))
    if isinstance(pofile, (str, unicode)):
      pofilename = pofile
      pofile = self.getpofile(pofilename)
    pofile.track(item, "suggestion by %s rejected by %s" % (self.getsuggester(pofile, item, suggitem), session.username))
    pofile.deletesuggestion(item, suggitem)

  def savepofile(self, pofilename):
    """saves changes to disk..."""
    pofile = self.getpofile(pofilename)
    pofile.savepofile()

  def getsource(self, pofilename):
    """returns pofile source"""
    pofile = self.getpofile(pofilename)
    return pofile.getsource()

  def getcsv(self, csvfilename):
    """returns pofile as csv"""
    pofilename = csvfilename.replace(".csv", ".po")
    pofile = self.getpofile(pofilename)
    return pofile.getcsv()

  def getmo(self, mofilename):
    """return pofile as compiled mo"""
    pofilename = mofilename.replace(".mo", ".po")
    pofile = self.getpofile(pofilename)
    return pofile.getmo()

  def gettext(self, message):
    """uses the project as a live translator for the given message"""
    for pofilename, pofile in self.pofiles.iteritems():
      if pofile.pomtime != pootlefile.getmodtime(pofile.filename):
        pofile.readpofile()
        pofile.makeindex()
      elif not hasattr(pofile, "msgidindex"):
        pofile.makeindex()
      thepo = pofile.msgidindex.get(message, None)
      if not thepo or thepo.isblankmsgstr():
        continue
      tmsg = po.unquotefrompo(thepo.msgstr)
      if tmsg is not None:
        return tmsg
    return message

  def ugettext(self, message):
    """gets the translation of the message by searching through all the pofiles (unicode version)"""
    for pofilename, pofile in self.pofiles.iteritems():
      try:
        if pofile.pomtime != pootlefile.getmodtime(pofile.filename):
          pofile.readpofile()
          pofile.makeindex()
        elif not hasattr(pofile, "msgidindex"):
          pofile.makeindex()
        thepo = pofile.msgidindex.get(message, None)
        if not thepo or thepo.isblankmsgstr():
          continue
        tmsg = po.unquotefrompo(thepo.msgstr)
        if tmsg is not None:
          if isinstance(tmsg, unicode):
            return tmsg
          else:
            return unicode(tmsg, pofile.encoding)
      except Exception, e:
        print "error reading translation from pofile %s: %s" % (pofilename, e)
    return unicode(message)

  def hascreatemofiles(self, projectcode):
    """returns whether the project has createmofile set"""
    return self.potree.getprojectcreatemofiles(projectcode) == 1

