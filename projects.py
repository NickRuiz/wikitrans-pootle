#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""manages projects and files and translations"""

from translate.storage import po
from translate.filters import checks
from translate.filters import pofilter
from translate.convert import po2csv
from translate.convert import po2xliff
from translate.convert import po2ts
from translate.convert import pot2po
from translate.tools import pocompile
from translate.tools import pogrep
from Pootle import pootlefile
from Pootle import versioncontrol
from jToolkit import timecache
from jToolkit import prefs
import time
import os
import cStringIO
import gettext
from jToolkit.data import indexer
from jToolkit import glock

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

class TranslationProject(object):
  """Manages iterating through the translations in a particular project"""
  fileext = "po"
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
      self.quickstats = {}
      self.converttemplates(InternalAdminSession())
    self.podir = potree.getpodir(languagecode, projectcode)
    if self.potree.hasgnufiles(self.podir, self.languagecode):
      self.filestyle = "gnu"
    else:
      self.filestyle = "std"
    self.readprefs()
    self.readquickstats()
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

  def getgoalfiles(self, goalname, dirfilter=None, maxdepth=None, includedirs=True, expanddirs=False, includepartial=False):
    """gets the files for the given goal, with many options!
    dirfilter limits to files in a certain subdirectory
    maxdepth limits to files / directories of a certain depth
    includedirs specifies whether to return directory names
    expanddirs specifies whether to expand directories and return all files in them
    includepartial specifies whether to return directories that are not in the goal, but have files below maxdepth in the goal"""
    goals = getattr(self.prefs, "goals", {})
    poext = os.extsep + self.fileext
    pathsep = os.path.sep
    unique = lambda filelist: dict.fromkeys(filelist).keys()
    for testgoalname, goalnode in goals.iteritems():
      if goalname != testgoalname: continue
      goalmembers = getattr(goalnode, "files", "")
      goalmembers = [goalfile.strip() for goalfile in goalmembers.split(",") if goalfile.strip()]
      goaldirs = [goaldir for goaldir in goalmembers if goaldir.endswith(pathsep)]
      goalfiles = [goalfile for goalfile in goalmembers if not goalfile.endswith(pathsep)]
      if expanddirs:
        expandgoaldirs = []
        expandgoalfiles = []
        for goaldir in goaldirs:
          expandedfiles = self.browsefiles(dirfilter=goaldir, includedirs=includedirs, includefiles=True)
          expandgoalfiles.extend([expandfile for expandfile in expandedfiles if expandfile.endswith(poext)])
          expandgoaldirs.extend([expanddir + pathsep for expanddir in expandedfiles if not expanddir.endswith(poext)])
        goaldirs = unique(goaldirs + expandgoaldirs)
        goalfiles = unique(goalfiles + expandgoalfiles)
      if dirfilter:
        if not dirfilter.endswith(pathsep) and not dirfilter.endswith(poext):
          dirfilter += pathsep
        goalfiles = [goalfile for goalfile in goalfiles if goalfile.startswith(dirfilter)]
        goaldirs = [goaldir for goaldir in goaldirs if goaldir.startswith(dirfilter)]
      if maxdepth is not None:
        if includepartial:
          partialdirs = [goalfile for goalfile in goalfiles if goalfile.count(pathsep) > maxdepth]
          partialdirs += [goalfile for goalfile in goaldirs if goalfile.count(pathsep) > maxdepth]
          makepartial = lambda goalfile: pathsep.join(goalfile.split(pathsep)[:maxdepth+1])+pathsep
          partialdirs = [makepartial(goalfile) for goalfile in partialdirs]
        goalfiles = [goalfile for goalfile in goalfiles if goalfile.count(pathsep) <= maxdepth]
        goaldirs = [goaldir for goaldir in goaldirs if goaldir.count(pathsep) <= maxdepth+1]
        if includepartial:
          goaldirs += partialdirs
      if includedirs:
        return unique(goalfiles + goaldirs)
      else:
        return unique(goalfiles)
    return []

  def getancestry(self, filename):
    """returns parent directories of the file"""
    ancestry = []
    parts = filename.split(os.path.sep)
    for i in range(1, len(parts)):
      ancestor = os.path.join(*parts[:i]) + os.path.sep
      ancestry.append(ancestor)
    return ancestry

  def getfilegoals(self, filename):
    """gets the goals the given file is part of"""
    goals = getattr(self.prefs, "goals", {})
    filegoals = []
    ancestry = self.getancestry(filename)
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
    else:
      unique = lambda filelist: dict.fromkeys(filelist).keys()
      ancestry = self.getancestry(filename)
      for ancestor in ancestry:
        if ancestor in goalfiles:
          filedepth = filename.count(os.path.sep)
          ancestordirs = self.getgoalfiles(goalname, ancestor, maxdepth=filedepth+1, includedirs=True, expanddirs=True)
          ancestordirs = [ancestorfile for ancestorfile in ancestordirs if ancestorfile.endswith(os.path.sep)]
          if filename.endswith(os.path.sep):
            ancestorfiles = self.getgoalfiles(goalname, ancestor, maxdepth=filedepth-1, expanddirs=True)
          else:
            ancestorfiles = self.getgoalfiles(goalname, ancestor, maxdepth=filedepth, expanddirs=True)
          ancestorfiles = unique(ancestordirs + ancestorfiles)
          if not filename in ancestorfiles:
            raise KeyError("expected to find file %s in ancestor %s files %r" % (filename, ancestor, ancestorfiles))
          ancestorfiles.remove(filename)
          ancestorfiles.remove(ancestor)
          goalfiles.remove(ancestor)
          goalfiles.extend(ancestorfiles)
          self.setgoalfiles(session, goalname, goalfiles)
          continue

  def setgoalfiles(self, session, goalname, goalfiles):
    """sets the goalfiles for the given goalname"""
    if "admin" not in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to alter goals here"))
    if isinstance(goalfiles, list):
      goalfiles = [goalfile.strip() for goalfile in goalfiles if goalfile.strip()]
      goalfiles.sort()
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
    self.pofilenames = self.potree.getpofiles(self.languagecode, self.projectcode, poext=self.fileext)
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
      newpofile = po.pofile(elementclass=pootlefile.pootleelement)
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
          msgid = origpo.unquotedmsgid
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
      if not filename.endswith(os.extsep + self.fileext):
        print "error adding %s: not a %s file" % (filename, os.extsep + self.fileext)
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
      if not dirfilter.endswith(os.path.sep) and not dirfilter.endswith(os.extsep + self.fileext):
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
    if not lastpofilename:
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
    if not indexer.HAVE_INDEXER:
      return
    self.indexdir = os.path.join(self.podir, ".poindex-%s-%s" % (self.projectcode, self.languagecode))
    class indexconfig:
      indexdir = self.indexdir
    self.analyzer = indexer.PerFieldAnalyzer([("pofilename", indexer.ExactAnalyzer())])
    self.indexer = indexer.Indexer(indexconfig, analyzer=self.analyzer)
    self.searcher = indexer.Searcher(self.indexdir, analyzer=self.analyzer)
    pofilenames = self.pofiles.keys()
    pofilenames.sort()
    for pofilename in pofilenames:
      self.updateindex(pofilename, optimize=False)
    self.indexer.optimizeIndex()

  def updateindex(self, pofilename, items=None, optimize=True):
    """updates the index with the contents of pofilename (limit to items if given)"""
    if not indexer.HAVE_INDEXER:
      return
    needsupdate = True
    pofile = self.pofiles[pofilename]
    # check if the pomtime in the index == the latest pomtime
    pomtime = pootlefile.getmodtime(pofile.filename)
    pofilenamequery = self.searcher.makeQuery([("pofilename", pofilename)], True)
    pomtimequery = self.searcher.makeQuery([("pomtime", str(pomtime))], True)
    if items is not None:
      itemsquery = self.searcher.makeQuery([("itemno", str(itemno)) for itemno in items], False)
    gooditemsquery = self.searcher.makeQuery([pofilenamequery, pomtimequery], True)
    gooditems = self.searcher.search(gooditemsquery, "itemno")
    allitems = self.searcher.search(pofilenamequery, "itemno")
    if items is None:
      if len(gooditems) == len(allitems) == pofile.getitemslen():
        return
      print "updating", self.projectcode, self.languagecode, "index for", pofilename
      self.searcher.deleteDoc({"pofilename": pofilename})
    else:
      print "updating", self.languagecode, "index for", pofilename, "items", items
      self.searcher.deleteDoc([pofilenamequery, itemsquery])
    pofile.pofreshen()
    addlist = []
    if items is None:
      items = range(len(pofile.transelements))
    for itemno in items:
      thepo = pofile.transelements[itemno]
      doc = {"pofilename": pofilename, "pomtime": str(pomtime), "itemno": str(itemno)}
      if thepo.hasplural():
        orig = self.unquotefrompo(thepo.msgid) + "\n" + self.unquotefrompo(thepo.msgid_plural)
        trans = self.unquotefrompo(thepo.msgstr)
        if isinstance(trans, dict):
          trans = "\n".join(trans.itervalues())
      else:
        orig = self.unquotefrompo(thepo.msgid)
        trans = self.unquotefrompo(thepo.msgstr)
      doc["msgid"] = orig
      doc["msgstr"] = trans
      addlist.append(doc)
    if addlist:
      self.indexer.startIndex()
      try:
        self.indexer.indexFields(addlist)
      finally:
        self.indexer.commitIndex(optimize=optimize)

  def matchessearch(self, pofilename, search):
    """returns whether any items in the pofilename match the search (based on collected stats etc)"""
    if search.dirfilter is not None and not pofilename.startswith(search.dirfilter):
      return False
    # search.assignedto == [None] means assigned to nobody
    if search.assignedto or search.assignedaction:
      if search.assignedto == [None]:
        assigns = self.pofiles[pofilename].getunassigned(search.assignedaction)
      else:
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
    return True

  def indexsearch(self, search, returnfields):
    """returns the results from searching the index with the given search"""
    if not indexer.HAVE_INDEXER:
      return False
    searchparts = []
    if search.searchtext:
      textquery = self.searcher.makeQuery([("msgid", search.searchtext), ("msgstr", search.searchtext)], False)
      searchparts.append(textquery)
    if search.dirfilter:
      pofilenames = self.browsefiles(dirfilter=search.dirfilter)
      filequery = self.searcher.makeQuery([("pofilename", pofilename) for pofilename in pofilenames], False)
      searchparts.append(filequery)
    # TODO: add other search items
    limitedquery = self.searcher.makeQuery(searchparts, True)
    return self.searcher.search(limitedquery, returnfields)

  def searchpofilenames(self, lastpofilename, search, includelast=False):
    """find the next pofilename that has items matching the given search"""
    if lastpofilename and not lastpofilename in self.pofiles:
      # accessing will autoload this file...
      self.pofiles[lastpofilename]
    if indexer.HAVE_INDEXER and search.searchtext:
      # TODO: move this up a level, use index to manage whole search, so we don't do this twice
      hits = self.indexsearch(search, "pofilename")
      print "ran search %s, got %d hits" % (search.searchtext, len(hits))
      searchpofilenames = dict.fromkeys([hit["pofilename"] for hit in hits])
    else:
      searchpofilenames = None
    for pofilename in self.iterpofilenames(lastpofilename, includelast):
      if searchpofilenames is not None:
        if pofilename not in searchpofilenames:
          continue
      if self.matchessearch(pofilename, search):
        yield pofilename

  def searchpoitems(self, pofilename, item, search):
    """finds the next item matching the given search"""
    if search.searchtext:
      pogrepfilter = pogrep.pogrepfilter(search.searchtext, None, ignorecase=True)
    for pofilename in self.searchpofilenames(pofilename, search, includelast=True):
      pofile = self.getpofile(pofilename)
      if indexer.HAVE_INDEXER:
        filesearch = search.copy()
        filesearch.dirfilter = pofilename
        hits = self.indexsearch(filesearch, "itemno")
        items = [int(doc["itemno"]) for doc in hits]
        items = [searchitem for searchitem in items if searchitem > item]
        items.sort()
        notextsearch = search.copy()
        notextsearch.searchtext = None
        matchitems = list(pofile.iteritems(notextsearch, item))
      else:
        items = pofile.iteritems(search, item)
        matchitems = items
      for item in items:
        if items != matchitems:
          if item not in matchitems:
            continue
        # TODO: move this to iteritems
        if search.searchtext:
          thepo = pofile.transelements[item]
          if pogrepfilter.filterelement(thepo):
            yield pofilename, item
        else:
          yield pofilename, item
      item = None

  def reassignpoitems(self, session, search, assignto, action):
    """reassign all the items matching the search to the assignto user(s) evenly, with the given action"""
    # remove all assignments for the given action
    self.unassignpoitems(session, search, None, action)
    assigncount = self.assignpoitems(session, search, assignto, action)
    return assigncount

  def assignpoitems(self, session, search, assignto, action):
    """assign all the items matching the search to the assignto user(s) evenly, with the given action"""
    if not "assign" in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to alter assignments here"))
    if search.searchtext:
      pogrepfilter = pogrep.pogrepfilter(search.searchtext, None, ignorecase=True)
    if not isinstance(assignto, list):
      assignto = [assignto]
    usercount = len(assignto)
    assigncount = 0
    if not usercount:
      return assigncount
    docountwords = lambda pofilename: self.countwords([(pofilename, item) for item in range(self.pofiles[pofilename].getitemslen())])
    pofilenames = [pofilename for pofilename in self.searchpofilenames(None, search, includelast=True)]
    wordcounts = [(pofilename, docountwords(pofilename)) for pofilename in pofilenames]
    totalwordcount = sum([wordcount for pofilename, wordcount in wordcounts])

    wordsperuser = totalwordcount / usercount
    print "assigning", totalwordcount, "words to", usercount, "user(s)", wordsperuser, "words per user"
    usernum = 0
    userwords = 0
    for pofilename, wordcount in wordcounts:
      pofile = self.getpofile(pofilename)
      for item in pofile.iteritems(search, None):
        # TODO: move this to iteritems
        if search.searchtext:
          validitem = False
          thepo = pofile.transelements[item]
          if pogrepfilter.filterelement(thepo):
            validitem = True
          if not validitem:
            continue
        itemwordcount = self.countwords([(pofilename, item)])
        if userwords + itemwordcount > wordsperuser:
          usernum = min(usernum+1, len(assignto)-1)
          userwords = 0
        userwords += itemwordcount
        pofile.assignto(item, assignto[usernum], action)
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

  def updatequickstats(self, pofilename, translatedwords, translated, totalwords, total):
    """updates the quick stats on the given file"""
    self.quickstats[pofilename] = (translatedwords, translated, totalwords, total)
    self.savequickstats()

  def savequickstats(self):
    """saves the quickstats"""
    self.quickstatsfilename = os.path.join(self.podir, "pootle-%s-%s.stats" % (self.projectcode, self.languagecode))
    quickstatsfile = open(self.quickstatsfilename, "w")
    sortedquickstats = self.quickstats.items()
    sortedquickstats.sort()
    for pofilename, (translatedwords, translated, totalwords, total) in sortedquickstats:
      quickstatsfile.write("%s, %d, %d, %d, %d\n" % (pofilename, translatedwords, translated, totalwords, total))
    quickstatsfile.close()

  def readquickstats(self):
    """reads the quickstats from disk"""
    self.quickstats = {}
    self.quickstatsfilename = os.path.join(self.podir, "pootle-%s-%s.stats" % (self.projectcode, self.languagecode))
    if os.path.exists(self.quickstatsfilename):
      quickstatsfile = open(self.quickstatsfilename, "r")
      for line in quickstatsfile:
        pofilename, translatedwords, translated, totalwords, total = line.split(",")
        self.quickstats[pofilename] = tuple([int(a.strip()) for a in translatedwords, translated, totalwords, total])

  def getquickstats(self, pofilenames=None):
    """gets translated and total stats and wordcouts without doing calculations returning dictionary"""
    if pofilenames is None:
      pofilenames = self.pofilenames
    alltranslatedwords, alltranslated, alltotalwords, alltotal = 0, 0, 0, 0
    slowfiles = []
    for pofilename in pofilenames:
      if pofilename not in self.quickstats:
        slowfiles.append(pofilename)
        continue
      translatedwords, translated, totalwords, total = self.quickstats[pofilename]
      alltranslatedwords += translatedwords
      alltranslated += translated
      alltotalwords += totalwords
      alltotal += total
    for pofilename in slowfiles:
      self.pofiles[pofilename].updatequickstats()
      translatedwords, translated, totalwords, total = self.quickstats[pofilename]
      alltranslatedwords += translatedwords
      alltranslated += translated
      alltotalwords += totalwords
      alltotal += total
    return {"translatedwords": alltranslatedwords, "translated": alltranslated, "totalwords": alltotalwords, "total": alltotal}

  def combinestats(self, pofilenames=None):
    """combines translation statistics for the given po files (or all if None given)"""
    totalstats = {}
    if pofilenames is None:
      pofilenames = self.pofilenames
    for pofilename in pofilenames:
      if not pofilename or os.path.isdir(pofilename):
        continue
      postats = self.getpostats(pofilename)
      for name, items in postats.iteritems():
        totalstats[name] = totalstats.get(name, []) + [(pofilename, item) for item in items]
    assignstats = self.combineassignstats(pofilenames)
    totalstats.update(assignstats)
    return totalstats

  def combineassignstats(self, pofilenames=None, action=None):
    """combines assign statistics for the given po files (or all if None given)"""
    totalstats = {}
    if pofilenames is None:
      pofilenames = self.pofilenames
    for pofilename in pofilenames:
      assignstats = self.getassignstats(pofilename, action)
      for name, items in assignstats.iteritems():
        totalstats["assign-"+name] = totalstats.get("assign-"+name, []) + [(pofilename, item) for item in items]
    return totalstats

  def countwords(self, stats):
    """counts the number of words in the items represented by the stats list"""
    wordcount = 0
    for pofilename, item in stats:
      pofile = self.pofiles[pofilename]
      if 0 <= item < len(pofile.msgidwordcounts):
        wordcount += sum(pofile.msgidwordcounts[item])
    return wordcount

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

  def getassignstats(self, pofilename, action=None):
    """calculates translation statistics for the given po file (can filter by action if given)"""
    polen = len(self.getpostats(pofilename)["total"])
    assigns = self.pofiles[pofilename].getassigns()
    assignstats = {}
    for username, userassigns in assigns.iteritems():
      allitems = []
      for assignaction, items in userassigns.iteritems():
        if action is None or assignaction == action:
          allitems += [item for item in items if 0 <= item < polen and item not in allitems]
      if allitems:
        assignstats[username] = allitems
    return assignstats

  def getpofile(self, pofilename, freshen=True):
    """parses the file into a pofile object and stores in self.pofiles"""
    pofile = self.pofiles[pofilename]
    if freshen:
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
    if isinstance(postr, dict):
      quotedpo = {}
      for pluralid in postr:
        quotedpo[pluralid] = self.unquotefrompo(postr[pluralid])
      return quotedpo
    else:
      return po.unquotefrompo(postr)

  def getitems(self, pofilename, itemstart, itemstop):
    """returns a set of items from the pofile, converted to original and translation strings"""
    pofile = self.getpofile(pofilename)
    elements = pofile.transelements[max(itemstart,0):itemstop]
    return elements

  def updatetranslation(self, pofilename, item, trans, session):
    """updates a translation with a new value..."""
    if "translate" not in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to change translations here"))
    pofile = self.pofiles[pofilename]
    pofile.track(item, "edited by %s" % session.username)
    languageprefs = getattr(session.instance.languages, self.languagecode, None)
    pofile.setmsgstr(item, trans, session.prefs, languageprefs)
    self.updateindex(pofilename, [item])

  def suggesttranslation(self, pofilename, item, trans, session):
    """stores a new suggestion for a translation..."""
    if "suggest" not in self.getrights(session):
      raise RightsError(session.localize("You do not have rights to suggest changes here"))
    pofile = self.getpofile(pofilename)
    pofile.track(item, "suggestion made by %s" % session.username)
    pofile.addsuggestion(item, trans, session.username)

  def getsuggestions(self, pofile, item):
    """find all the suggestions submitted for the given (pofile or pofilename) and item"""
    if isinstance(pofile, (str, unicode)):
      pofilename = pofile
      pofile = self.getpofile(pofilename)
    suggestpos = pofile.getsuggestions(item)
    return suggestpos

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
        suggestedby = po.unquotefrompo([msgidcomment]).replace("_:", "", 1).replace("suggested by ", "", 1).strip()
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

  def convert(self, pofilename, destformat):
    """converts the pofile to the given format, returning (etag_if_filepath, filepath_or_contents)"""
    destfilename = pofilename[:-len(self.fileext)] + destformat
    pofile = self.getpofile(pofilename, freshen=False)
    destfilename = pofile.filename[:-len(self.fileext)] + destformat
    destmtime = pootlefile.getmodtime(destfilename)
    pomtime = pootlefile.getmodtime(pofile.filename)
    if pomtime and destmtime == pomtime:
      try:
        return pomtime, destfilename
      except Exception, e:
        print "error reading cached converted file %s: %s" % (destfilename, e)
    pofile.pofreshen()
    converters = {"csv": po2csv.po2csv, "xlf": po2xliff.po2xliff, "ts": po2ts.po2ts, "mo": pocompile.POCompile}
    converterclass = converters.get(destformat, None)
    if converterclass is None:
      raise ValueError("No converter available for %s" % destfilename)
    contents = converterclass().convertfile(pofile)
    if not isinstance(contents, basestring):
      contents = str(contents)
    try:
      destfile = open(destfilename, "w")
      destfile.write(contents)
      destfile.close()
      currenttime, modtime = time.time(), pofile.pomtime
      os.utime(destfilename, (currenttime, modtime))
      return modtime, destfilename
    except Exception, e:
      print "error caching converted file %s: %s" % (destfilename, e)
    return False, contents

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
        if not thepo or thepo.isblankmsgstr() or thepo.isfuzzy():
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

  def ungettext(self, singular, plural, n):
    """gets the plural translation of the message by searching through all the pofiles (unicode version)"""
    for pofilename, pofile in self.pofiles.iteritems():
      try:
        if pofile.pomtime != pootlefile.getmodtime(pofile.filename):
          pofile.readpofile()
          pofile.makeindex()
        elif not hasattr(pofile, "msgidindex"):
          pofile.makeindex()
        nplural, pluralequation = pofile.getheaderplural()
        if pluralequation:
          pluralfn = gettext.c2py(pluralequation)
          thepo = pofile.msgidindex.get(singular, None)
          if not thepo or thepo.isblankmsgstr() or thepo.isfuzzy():
            continue
          tmsg = po.unquotefrompo(thepo.msgstr[pluralfn(n)])
          if tmsg is not None:
            if isinstance(tmsg, unicode):
              return tmsg
            else:
              return unicode(tmsg, pofile.encoding)
      except Exception, e:
        print "error reading translation from pofile %s: %s" % (pofilename, e)
    if n == 1:
      return unicode(singular)
    else:
      return unicode(plural)

  def hascreatemofiles(self, projectcode):
    """returns whether the project has createmofile set"""
    return self.potree.getprojectcreatemofiles(projectcode) == 1

class DummyProject(TranslationProject):
  """a project that is just being used for handling pootlefiles"""
  def __init__(self, podir, checker=None, projectcode=None, languagecode=None):
    """initializes the project with the given podir"""
    self.podir = podir
    if checker is None:
      self.checker = pofilter.POTeeChecker()
    else:
      self.checker = checker
    self.projectcode = projectcode
    self.languagecode = languagecode
    self.readquickstats()

  def readquickstats(self):
    """dummy statistics are empty"""
    self.quickstats = {}

  def savequickstats(self):
    """saves quickstats if possible"""
    pass

class DummyStatsProject(DummyProject):
  """a project that is just being used for refresh of statistics"""
  def __init__(self, podir, checker, projectcode=None, languagecode=None):
    """initializes the project with the given podir"""
    DummyProject.__init__(self, podir, checker, projectcode, languagecode)

  def readquickstats(self):
    """reads statistics from whatever files are available"""
    self.quickstats = {}
    if self.projectcode is not None and self.languagecode is not None:
      TranslationProject.readquickstats(self)

  def savequickstats(self):
    """saves quickstats if possible"""
    if self.projectcode is not None and self.languagecode is not None:
      TranslationProject.savequickstats(self)

class TemplatesProject(TranslationProject):
  """Manages Template files (.pot files) for a project"""
  fileext = "pot"
  def __init__(self, projectcode, potree):
    super(TemplatesProject, self).__init__("templates", projectcode, potree, create=False)

  def getrights(self, session=None, username=None):
    """gets the rights for the given user (name or session, or not-logged-in if username is None)"""
    # internal admin sessions have all rights
    rights = super(TemplatesProject, self).getrights(session=session, username=username)
    rights = [right for right in rights if right not in ["translate", "suggest", "pocompile"]]
    return rights

