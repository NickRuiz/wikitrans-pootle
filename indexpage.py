#!/usr/bin/env python
# -*- coding: utf-8 -*-

from Pootle import pagelayout
from Pootle import projects
from Pootle import pootlefile
from Pootle import versioncontrol
from Pootle import __version__ as pootleversion
from translate import __version__ as toolkitversion
from jToolkit import __version__ as jtoolkitversion
import os
import sys

def summarizestats(statslist, totalstats=None):
  if totalstats is None:
    totalstats = {}
  for statsdict in statslist:
    for name, count in statsdict.iteritems():
      totalstats[name] = totalstats.get(name, 0) + count
  return totalstats

class AboutPage(pagelayout.PootlePage):
  """the bar at the side describing current login details etc"""
  def __init__(self, session):
    self.localize = session.localize
    pagetitle = getattr(session.instance, "title")
    description = getattr(session.instance, "description")
    abouttitle = self.localize("About Pootle")
    introtext = self.localize("<strong>Pootle</strong> is a simple web portal that should allow you to <strong>translate</strong>! Since Pootle is <strong>Free Software</strong>, you can download it and run your own copy if you like. You can also help participate in the development in many ways (you don't have to be able to program).")
    hosttext = self.localize('The Pootle project itself is hosted at <a href="http://translate.sourceforge.net/">translate.sourceforge.net</a> where you can find the details about source code, mailing lists etc.')
    nametext = self.localize('The name stands for <b>PO</b>-based <b>O</b>nline <b>T</b>ranslation / <b>L</b>ocalization <b>E</b>ngine, but you may need to read <a href="http://www.thechestnut.com/flumps.htm">this</a>.')
    versiontitle = self.localize("Versions")
    versiontext = self.localize("This site is running:<br/>Pootle %s<br/>Translate Toolkit %s<br/>jToolkit %s<br/>Python %s (on %s/%s)", pootleversion.ver, toolkitversion.ver, jtoolkitversion.ver, sys.version, sys.platform, os.name)
    templatename = "about"
    instancetitle = getattr(session.instance, "title", session.localize("Pootle Demo"))
    sessionvars = {"status": session.status, "isopen": session.isopen, "issiteadmin": session.issiteadmin()}
    templatevars = {"pagetitle": pagetitle, "description": description,
        "abouttitle": abouttitle, "introtext": introtext,
        "hosttext": hosttext, "nametext": nametext, "versiontitle": versiontitle, "versiontext": versiontext,
        "session": sessionvars, "instancetitle": pagetitle}
    pagelayout.PootlePage.__init__(self, templatename, templatevars, session)

class PootleIndex(pagelayout.PootlePage):
  """the main page"""
  def __init__(self, potree, session):
    self.potree = potree
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    pagetitle = self.localize("Pootle")
    templatename = "index"
    aboutlink = self.localize("About this Pootle server")
    languagelink = self.localize('Languages')
    projectlink = self.localize('Projects')
    instancetitle = getattr(session.instance, "title", session.localize("Pootle Demo"))
    sessionvars = {"status": session.status, "isopen": session.isopen, "issiteadmin": session.issiteadmin()}
    languages = [{"code": code, "name": name, "sep": ", "} for code, name in self.potree.getlanguages()]
    if languages:
      languages[-1]["sep"] = ""
    templatevars = {"pagetitle": pagetitle, "aboutlink": aboutlink,
        "languagelink": languagelink, "languages": languages,
        "projectlink": projectlink, "projects": self.getprojects(),
        "session": sessionvars, "instancetitle": pagetitle}
    pagelayout.PootlePage.__init__(self, templatename, templatevars, session)

  def getprojects(self):
    """gets the options for the projects"""
    projects = []
    for projectcode in self.potree.getprojectcodes():
      projectname = self.potree.getprojectname(projectcode)
      description = self.potree.getprojectdescription(projectcode)
      projects.append({"code": projectcode, "name": projectname, "description": description, "sep": ", "})
    if projects:
      projects[-1]["sep"] = ""
    return projects

class UserIndex(pagelayout.PootlePage):
  """home page for a given user"""
  def __init__(self, potree, session):
    self.potree = potree
    self.session = session
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    pagetitle = self.localize("User Page for: %s", session.username)
    templatename = "home"
    optionslink = self.localize("Change options")
    adminlink = self.localize("Admin page")
    quicklinkstitle = self.localize("Quick Links")
    instancetitle = getattr(session.instance, "title", session.localize("Pootle Demo"))
    sessionvars = {"status": session.status, "isopen": session.isopen, "issiteadmin": session.issiteadmin()}
    quicklinks = self.getquicklinks()
    setoptionstext = self.localize("Please click on 'Change options' and select some languages and projects")
    templatevars = {"pagetitle": pagetitle, "optionslink": optionslink,
        "adminlink": adminlink, "quicklinkstitle": quicklinkstitle,
        "quicklinks": quicklinks, "setoptionstext": setoptionstext,
        "session": sessionvars, "instancetitle": pagetitle}
    pagelayout.PootlePage.__init__(self, templatename, templatevars, session)

  def getquicklinks(self):
    """gets a set of quick links to user's project-languages"""
    quicklinks = []
    for languagecode in self.session.getlanguages():
      if not self.potree.haslanguage(languagecode):
        continue
      languagename = self.potree.getlanguagename(languagecode)
      langlinks = []
      for projectcode in self.session.getprojects():
        if self.potree.hasproject(languagecode, projectcode):
          projectname = self.potree.getprojectname(projectcode)
          projecttitle = self.localize("%s %s", languagename, projectname)
          langlinks.append({"code": projectcode, "name": projecttitle, "sep": "<br/>"})
      if langlinks:
        langlinks[-1]["sep"] = ""
      quicklinks.append({"code": languagecode, "name": languagename, "projects": langlinks})
    return quicklinks

class ProjectsIndex(PootleIndex):
  """the list of languages"""
  def __init__(self, potree, session):
    PootleIndex.__init__(self, potree, session)
    self.templatename = "projects"

class LanguagesIndex(PootleIndex):
  """the list of languages"""
  def __init__(self, potree, session):
    PootleIndex.__init__(self, potree, session)
    self.templatename = "languages"

class LanguageIndex(pagelayout.PootleNavPage):
  """the main page"""
  def __init__(self, potree, languagecode, session):
    self.potree = potree
    self.languagecode = languagecode
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    self.languagename = self.potree.getlanguagename(self.languagecode)
    self.initpagestats()
    languageprojects = self.getprojects()
    self.projectcount = len(languageprojects)
    average = self.getpagestats()
    languagestats = self.nlocalize("%d project, average %d%% translated", "%d projects, average %d%% translated", self.projectcount, self.projectcount, average)
    languageinfo = self.getlanguageinfo()
    pagetitle =  self.localize("Pootle: %s", self.languagename)
    templatename = "language"
    adminlink = self.localize("Admin")
    instancetitle = getattr(session.instance, "title", session.localize("Pootle Demo"))
    sessionvars = {"status": session.status, "isopen": session.isopen, "issiteadmin": session.issiteadmin()}
    templatevars = {"pagetitle": pagetitle,
        "language": {"code": languagecode, "name": self.languagename, "stats": languagestats, "info": languageinfo},
        "projects": languageprojects,
        "session": sessionvars, "instancetitle": pagetitle}
    pagelayout.PootleNavPage.__init__(self, templatename, templatevars, session, bannerheight=81)

  def getlanguageinfo(self):
    """returns information defined for the language"""
    # specialchars = self.potree.getlanguagespecialchars(self.languagecode)
    nplurals = self.potree.getlanguagenplurals(self.languagecode)
    pluralequation = self.potree.getlanguagepluralequation(self.languagecode)
    infoparts = [(self.localize("Language Code"), self.languagecode),
                 (self.localize("Language Name"), self.languagename),
                 # (self.localize("Special Characters"), specialchars),
                 (self.localize("Number of Plurals"), str(nplurals)),
                 (self.localize("Plural Equation"), pluralequation),
                ]
    return [{"title": title, "value": value} for title, value in infoparts]

  def getprojects(self):
    """gets the info on the projects"""
    projectcodes = self.potree.getprojectcodes(self.languagecode)
    self.projectcount = len(projectcodes)
    projectitems = [self.getprojectitem(projectcode) for projectcode in projectcodes]
    for n, item in enumerate(projectitems):
      item["parity"] = ["even", "odd"][n % 2]
    return projectitems

  def getprojectitem(self, projectcode):
    projectname = self.potree.getprojectname(projectcode)
    projectdescription = self.potree.getprojectdescription(projectcode)
    project = self.potree.getproject(self.languagecode, projectcode)
    numfiles = len(project.pofilenames)
    projectstats = project.getquickstats()
    self.updatepagestats(projectstats["translatedwords"], projectstats["totalwords"])
    projectstats = self.describestats(project, projectstats, numfiles)
    return {"code": projectcode, "name": projectname, "description": projectdescription, "stats": projectstats}

class ProjectLanguageIndex(pagelayout.PootleNavPage):
  """list of languages belonging to a project"""
  def __init__(self, potree, projectcode, session):
    self.potree = potree
    self.projectcode = projectcode
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    self.initpagestats()
    languages = self.getlanguages()
    average = self.getpagestats()
    projectstats = self.nlocalize("%d language, average %d%% translated", "%d languages, average %d%% translated", self.languagecount, self.languagecount, average)
    projectname = self.potree.getprojectname(self.projectcode)
    pagetitle =  self.localize("Pootle: %s", projectname)
    templatename = "project"
    adminlink = self.localize("Admin")
    instancetitle = getattr(session.instance, "title", session.localize("Pootle Demo"))
    sessionvars = {"status": session.status, "isopen": session.isopen, "issiteadmin": session.issiteadmin()}
    setoptionstext = self.localize("Please click on 'Change options' and select some languages and projects")
    templatevars = {"pagetitle": pagetitle,
        "project": {"code": projectcode, "name": projectname, "stats": projectstats},
        "adminlink": adminlink, "languages": languages,
        "session": sessionvars, "instancetitle": pagetitle}
    pagelayout.PootleNavPage.__init__(self, templatename, templatevars, session, bannerheight=81)

  def getlanguages(self):
    """gets the stats etc of the languages"""
    languages = self.potree.getlanguages(self.projectcode)
    self.languagecount = len(languages)
    languageitems = [self.getlanguageitem(languagecode, languagename) for languagecode, languagename in languages]
    for n, item in enumerate(languageitems):
      item["parity"] = ["even", "odd"][n % 2]
    return languageitems

  def getlanguageitem(self, languagecode, languagename):
    language = self.potree.getproject(languagecode, self.projectcode)
    numfiles = len(language.pofilenames)
    languagestats = language.combinestats()
    translated = languagestats.get("translated", [])
    total = languagestats.get("total", [])
    translatedwords = language.countwords(translated)
    totalwords = language.countwords(total)
    self.updatepagestats(translatedwords, totalwords)
    percentfinished = (translatedwords*100/max(totalwords, 1))
    filestats = self.nlocalize("%d file", "%d files", numfiles, numfiles)
    wordstats = self.localize("%d/%d words (%d%%) translated", translatedwords, totalwords, percentfinished)
    stringstats = self.localize("[%d/%d strings]", len(translated), len(total))
    stats = filestats + ", " + wordstats + " " + '<span class="string-statistics">%s</span>' % stringstats
    return {"code": languagecode, "name": languagename, "stats": stats}

class ProjectIndex(pagelayout.PootleNavPage):
  """the main page"""
  def __init__(self, project, session, argdict, dirfilter=None):
    self.project = project
    self.session = session
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    self.rights = self.project.getrights(self.session)
    message = argdict.get("message", "")
    if dirfilter == "":
      dirfilter = None
    self.dirfilter = dirfilter
    if dirfilter and dirfilter.endswith(".po"):
      self.dirname = "/".join(dirfilter.split("/")[:-1])
    else:
      self.dirname = dirfilter or ""
    self.argdict = argdict
    # handle actions before generating URLs, so we strip unneccessary parameters out of argdict
    self.handleactions()
    self.showtracks = self.getboolarg("showtracks")
    self.showchecks = self.getboolarg("showchecks")
    self.showassigns = self.getboolarg("showassigns")
    self.showgoals = self.getboolarg("showgoals")
    self.currentgoal = self.argdict.pop("goal", None)
    if dirfilter and dirfilter.endswith(".po"):
      actionlinks = []
      mainstats = ""
      mainicon = "file"
    else:
      pofilenames = self.project.browsefiles(dirfilter)
      projectstats = self.project.combinestats(pofilenames)
      actionlinks = self.getactionlinks("", projectstats, ["mine", "review", "check", "assign", "goal", "quick", "all", "zip", "sdf"], dirfilter)
      mainstats = self.getitemstats("", projectstats, len(pofilenames))
      mainicon = "folder"
    navbarpath_dict = self.makenavbarpath_dict(project=self.project, session=self.session, currentfolder=dirfilter, goal=self.currentgoal)
    if self.showgoals:
      childitems = self.getgoalitems(dirfilter)
    else:
      childitems = self.getchilditems(dirfilter)
    pagetitle = self.localize("Pootle: Project %s, Language %s", self.project.projectname, self.project.languagename)
    templatename = "fileindex"
    instancetitle = getattr(session.instance, "title", session.localize("Pootle Demo"))
    sessionvars = {"status": session.status, "isopen": session.isopen, "issiteadmin": session.issiteadmin()}
    templatevars = {"pagetitle": pagetitle,
        "project": {"code": self.project.projectcode, "name": self.project.projectname},
        "language": {"code": self.project.languagecode, "name": self.project.languagename},
        # optional sections, will appear if these values are replaced
        "assign": None, "goals": None, "upload": None,
        "search": {"title": self.localize("Search")}, "message": message,
        # navigation bar
        "navitems": [{"icon": "folder", "path": navbarpath_dict, "actions": actionlinks, "stats": mainstats}],
        # children
        "children": childitems,
        # general vars
        "session": sessionvars, "instancetitle": pagetitle}
    pagelayout.PootleNavPage.__init__(self, templatename, templatevars, session, bannerheight=81)
    if self.showassigns and "assign" in self.rights:
      self.templatevars["assign"] = self.getassignbox()
    if "admin" in self.rights:
      if self.showgoals:
        self.templatevars["goals"] = self.getgoalbox()
    if "admin" in self.rights or "translate" in self.rights:
      self.templatevars["upload"] = self.getuploadbox()

  def handleactions(self):
    """handles the given actions that must be taken (changing operations)"""
    if "doassign" in self.argdict:
      assignto = self.argdict.pop("assignto", None)
      action = self.argdict.pop("action", None)
      if not assignto and action:
        raise ValueError("cannot doassign, need assignto and action")
      search = pootlefile.Search(dirfilter=self.dirfilter)
      assigncount = self.project.assignpoitems(self.session, search, assignto, action)
      print "assigned %d strings to %s for %s" % (assigncount, assignto, action)
      del self.argdict["doassign"]
    if self.getboolarg("removeassigns"):
      assignedto = self.argdict.pop("assignedto", None)
      removefilter = self.argdict.pop("removefilter", "")
      if removefilter:
        if self.dirfilter:
          removefilter = self.dirfilter + removefilter
      else:
        removefilter = self.dirfilter
      search = pootlefile.Search(dirfilter=removefilter)
      search.assignedto = assignedto
      assigncount = self.project.unassignpoitems(self.session, search, assignedto)
      print "removed %d assigns from %s" % (assigncount, assignedto)
      del self.argdict["removeassigns"]
    if "doupload" in self.argdict:
      uploadfile = self.argdict.pop("uploadfile", None)
      if not uploadfile.filename:
        raise ValueError(self.localize("Cannot upload file, no file attached"))
      if uploadfile.filename.endswith(".po"):
        self.project.uploadpofile(self.session, self.dirname, uploadfile.filename, uploadfile.contents)
      elif uploadfile.filename.endswith(".zip"):
        self.project.uploadarchive(self.session, self.dirname, uploadfile.contents)
      else:
        raise ValueError(self.localize("Can only upload PO files and zips of PO files"))
      del self.argdict["doupload"]
    if "doupdate" in self.argdict:
      updatefile = self.argdict.pop("updatefile", None)
      if not updatefile:
        raise ValueError("cannot update file, no file specified")
      if updatefile.endswith(".po"):
        self.project.updatepofile(self.session, self.dirname, updatefile)
      else:
        raise ValueError("can only update PO files")
      del self.argdict["doupdate"]
    if "doaddgoal" in self.argdict:
      goalname = self.argdict.pop("newgoal", None)
      if not goalname:
        raise ValueError("cannot add goal, no name given")
      self.project.setgoalfiles(self.session, goalname.strip(), "")
      del self.argdict["doaddgoal"]
    if "doeditgoal" in self.argdict:
      goalnames = self.argdict.pop("editgoal", None)
      goalfile = self.argdict.pop("editgoalfile", None)
      if not goalfile:
        raise ValueError("cannot add goal, no filename given")
      if self.dirname:
        goalfile = os.path.join(self.dirname, goalfile)
      if not isinstance(goalnames, list):
        goalnames = [goalnames]
      goalnames = [goalname.strip() for goalname in goalnames if goalname.strip()]
      self.project.setfilegoals(self.session, goalnames, goalfile)
      del self.argdict["doeditgoal"]
    if "doeditgoalusers" in self.argdict:
      goalname = self.argdict.pop("editgoalname", "").strip()
      if not goalname:
        raise ValueError("cannot edit goal, no name given")
      goalusers = self.project.getgoalusers(goalname)
      addusername = self.argdict.pop("newgoaluser", "").strip()
      if addusername:
        self.project.addusertogoal(self.session, goalname, addusername)
      del self.argdict["doeditgoalusers"]
    if "doedituser" in self.argdict:
      goalnames = self.argdict.pop("editgoal", None)
      goalusers = self.argdict.pop("editfileuser", "")
      goalfile = self.argdict.pop("editgoalfile", None)
      assignwhich = self.argdict.pop("edituserwhich", "all")
      if not goalfile:
        raise ValueError("cannot add user to file for goal, no filename given")
      if self.dirname:
        goalfile = os.path.join(self.dirname, goalfile)
      if not isinstance(goalusers, list):
        goalusers = [goalusers]
      goalusers = [goaluser.strip() for goaluser in goalusers if goaluser.strip()]
      if not isinstance(goalnames, list):
        goalnames = [goalnames]
      goalnames = [goalname.strip() for goalname in goalnames if goalname.strip()]
      search = pootlefile.Search(dirfilter=goalfile)
      if assignwhich == "all":
        pass
      elif assignwhich == "untranslated":
        search.matchnames = ["fuzzy", "blank"]
      elif assignwhich == "unassigned":
        search.assignedto = [None]
      elif assignwhich == "unassigneduntranslated":
        search.matchnames = ["fuzzy", "blank"]
        search.assignedto = [None]
      else:
        raise ValueError("unexpected assignwhich")
      for goalname in goalnames:
        action = "goal-" + goalname
        self.project.reassignpoitems(self.session, search, goalusers, action)
      del self.argdict["doedituser"]
    # pop arguments we don't want to propogate through inadvertently...
    for argname in ("assignto", "action", "assignedto", "removefilter", "uploadfile",
        "updatefile", "newgoal", "editgoal", "editgoalfile", "editgoalname",
        "newgoaluser", "editfileuser", "editgoalfile", "edituserwhich"):
      self.argdict.pop(argname, "")

  def getboolarg(self, argname, default=False):
    """gets a boolean argument from self.argdict"""
    value = self.argdict.get(argname, default)
    if isinstance(value, bool):
      return value
    elif isinstance(value, int):
      return bool(value)
    elif isinstance(value, (str, unicode)):
      value = value.lower() 
      if value.isdigit():
        return bool(int(value))
      if value == "true":
        return True
      if value == "false":
        return False
    raise ValueError("Invalid boolean value for %s: %r" % (argname, value))

  def getassignbox(self):
    """adds a box that lets the user assign strings"""
    users = [username for username, userprefs in self.session.loginchecker.users.iteritems() if username != "__dummy__"]
    users.sort()
    return {
      "users": users,
      "title": self.localize("Assign Strings"),
      "action_text": self.localize("Assign Action"),
      "users_text": self.localize("Assign to User"),
      "button": self.localize("Assign Strings")
    }

  def getgoalbox(self):
    """adds a box that lets the user add a new goal"""
    return {"title": self.localize('goals'), "name-title": self.localize("Enter goal name"), "button": self.localize("Add Goal")}

  def getuploadbox(self):
    """adds a box that lets the user assign strings"""
    return {"title": self.localize("Upload File"),
            "file_title": self.localize("Select file to upload"),
            "button": self.localize("Upload File")}

  def getchilditems(self, dirfilter):
    """get all the items for directories and files viewable at this level"""
    if dirfilter is None:
      depth = 0
    else:
      depth = dirfilter.count(os.path.sep)
      if not dirfilter.endswith(os.path.extsep + "po"):
        depth += 1
    diritems = []
    for childdir in self.project.browsefiles(dirfilter=dirfilter, depth=depth, includedirs=True, includefiles=False):
      diritem = self.getdiritem(childdir)
      diritems.append((childdir, diritem))
    diritems.sort()
    fileitems = []
    for childfile in self.project.browsefiles(dirfilter=dirfilter, depth=depth, includefiles=True, includedirs=False):
      fileitem = self.getfileitem(childfile)
      fileitems.append((childfile, fileitem))
    fileitems.sort()
    childitems = [diritem for childdir, diritem in diritems] + [fileitem for childfile, fileitem in fileitems]
    self.polarizeitems(childitems)
    return childitems

  def getitems(self, itempaths, linksrequired=None, **newargs):
    """gets the listed dir and fileitems"""
    diritems, fileitems = [], []
    for item in itempaths:
      if item.endswith(os.path.extsep + "po"):
        fileitem = self.getfileitem(item, linksrequired=linksrequired, **newargs)
        fileitems.append((item, fileitem))
      else:
        if item.endswith(os.path.sep):
          item = item.rstrip(os.path.sep)
        diritem = self.getdiritem(item, linksrequired=linksrequired, **newargs)
        diritems.append((item, diritem))
      diritems.sort()
      fileitems.sort()
    childitems = [diritem for childdir, diritem in diritems] + [fileitem for childfile, fileitem in fileitems]
    self.polarizeitems(childitems)
    return childitems

  def getgoalitems(self, dirfilter):
    """get all the items for directories and files viewable at this level"""
    if dirfilter is None:
      depth = 0
    else:
      depth = dirfilter.count(os.path.sep)
      if not dirfilter.endswith(os.path.extsep + "po"):
        depth += 1
    allitems = []
    goalchildren = {}
    allchildren = []
    for childname in self.project.browsefiles(dirfilter=dirfilter, depth=depth, includedirs=True, includefiles=False):
      allchildren.append(childname+"/")
    for childname in self.project.browsefiles(dirfilter=dirfilter, depth=depth, includedirs=False, includefiles=True):
      allchildren.append(childname)
    initial = dirfilter
    if initial and not initial.endswith(os.path.extsep + "po"):
      initial += os.path.sep
    if initial:
      maxdepth = initial.count(os.path.sep)
    else:
      maxdepth = 0
    # using a goal of "" means that the file has no goal
    nogoal = ""
    if self.currentgoal is None:
      goalnames = self.project.getgoalnames() + [nogoal]
    else:
      goalnames = [self.currentgoal]
    goalfiledict = {}
    for goalname in goalnames:
      goalfiles = self.project.getgoalfiles(goalname, dirfilter, maxdepth=maxdepth, expanddirs=True, includepartial=True)
      goalfiles = [goalfile for goalfile in goalfiles if goalfile != initial]
      goalfiledict[goalname] = goalfiles
      for goalfile in goalfiles:
        goalchildren[goalfile] = True
    goalless = []
    for item in allchildren:
      itemgoals = self.project.getfilegoals(item)
      if not itemgoals:
        goalless.append(item)
    goalfiledict[nogoal] = goalless
    for goalname in goalnames:
      goalfiles = goalfiledict[goalname]
      goalusers = self.project.getgoalusers(goalname)
      goalitem = self.getgoalitem(goalname, dirfilter, goalusers)
      allitems.append(goalitem)
      if self.currentgoal == goalname:
        goalchilditems = self.getitems(goalfiles, linksrequired=["editgoal"], goal=self.currentgoal)
        allitems.extend(goalchilditems)
    return allitems

  def getgoalitem(self, goalname, dirfilter, goalusers):
    """returns an item showing a goal entry"""
    # TODO: fix stats for goalless
    pofilenames = self.project.getgoalfiles(goalname, dirfilter, expanddirs=True, includedirs=False)
    projectstats = self.project.combinestats(pofilenames)
    goal = {"actions": None, "icon": "goal", "isgoal": True, "goal": {"name": goalname}}
    if goalname:
      goal["title"] = goalname
    else:
      goal["title"] = self.localize("No goal")
    goal["href"] = self.makelink("index.html", goal=goalname)
    if pofilenames:
      actionlinks = self.getactionlinks("", projectstats, linksrequired=["mine", "review", "translate", "zip"], goal=goalname)
      goal["actions"] = actionlinks
    goaluserslist = []
    if goalusers:
      goalusers.sort()
      goaluserslist = [{"name": goaluser, "sep": ", "} for goaluser in goalusers]
      if goaluserslist:
        goaluserslist[-1]["sep"] = ""
    goal["goal"]["users"] = goaluserslist
    if goalname and self.currentgoal == goalname:
      if "admin" in self.rights:
        unassignedusers = [username for username, userprefs in self.session.loginchecker.users.iteritems() if username != "__dummy__"]
        for user in goalusers:
          if user in unassignedusers:
            unassignedusers.remove(user)
        unassignedusers.sort()
        goal["goal"]["show_adduser"] = True
        goal["goal"]["otherusers"] = unassignedusers
        goal["goal"]["adduser_title"] = self.localize("Add User")
    goal["stats"] = self.getitemstats("", projectstats, len(pofilenames))
    return goal

  def getdiritem(self, direntry, linksrequired=None, **newargs):
    """returns an item showing a directory entry"""
    pofilenames = self.project.browsefiles(direntry)
    if self.showgoals and "goal" in self.argdict:
      goalfilenames = self.project.getgoalfiles(self.currentgoal, dirfilter=direntry, includedirs=False, expanddirs=True)
      projectstats = self.project.combinestats(goalfilenames)
    else:
      projectstats = self.project.combinestats(pofilenames)
    basename = os.path.basename(direntry)
    browseurl = self.getbrowseurl("%s/" % basename, **newargs)
    diritem = {"href": browseurl, "title": basename, "icon": "folder", "isdir": True}
    basename += "/"
    actionlinks = self.getactionlinks(basename, projectstats, linksrequired=linksrequired)
    diritem["actions"] = actionlinks
    if self.showgoals and "goal" in self.argdict:
      diritem["stats"] = self.getitemstats(basename, projectstats, (len(goalfilenames), len(pofilenames)))
    else:
      diritem["stats"] = self.getitemstats(basename, projectstats, len(pofilenames))
    return diritem

  def getfileitem(self, fileentry, linksrequired=None, **newargs):
    """returns an item showing a file entry"""
    if linksrequired is None:
      linksrequired = ["mine", "review", "quick", "all", "po", "xliff", "ts", "csv", "mo", "update"]
    basename = os.path.basename(fileentry)
    projectstats = self.project.combinestats([fileentry])
    browseurl = self.getbrowseurl(basename, **newargs)
    fileitem = {"href": browseurl, "title": basename, "icon": "file", "isfile": True}
    actions = self.getactionlinks(basename, projectstats, linksrequired=linksrequired)
    actionlinks = actions["extended"]
    if "po" in linksrequired:
      downloadlink = {"href": basename, "text": self.localize('PO file')}
      actionlinks.append(downloadlink)
    if "xliff" in linksrequired and "translate" in self.rights:
      xliffname = basename.replace(".po", ".xlf")
      xlifflink = {"href": xliffname, "text": self.localize('XLIFF file')}
      actionlinks.append(xlifflink)
    if "ts" in linksrequired and "translate" in self.rights:
      tsname = basename.replace(".po", ".ts")
      tslink = {"href": tsname, "text": self.localize('Qt .ts file')}
      actionlinks.append(tslink)
    if "csv" in linksrequired and "translate" in self.rights:
      csvname = basename.replace(".po", ".csv")
      csvlink = {"href": csvname, "text": self.localize('CSV file')}
      actionlinks.append(csvlink)
    if "mo" in linksrequired:
      if self.project.hascreatemofiles(self.project.projectcode) and "pocompile" in self.rights:
        moname = basename.replace(".po", ".mo")
        molink = {"href": moname, "text": self.localize('MO file')}
        actionlinks.append(molink)
    if "update" in linksrequired and "admin" in self.rights:
      if versioncontrol.hasversioning(os.path.join(self.project.podir, self.dirname)):
        updatelink = {"href": "index.html?doupdate=1&updatefile=%s" % basename, "text": self.localize('Update')}
        actionlinks.append(updatelink)
    # update the separators
    for n, actionlink in enumerate(actionlinks):
      if n < len(actionlinks)-1:
        actionlink["sep"] = " | "
      else:
        actionlink["sep"] = ""
    fileitem["actions"] = actions
    fileitem["stats"] = self.getitemstats(basename, projectstats, None)
    return fileitem

  def getgoalform(self, basename, goalfile, filegoals):
    """Returns a form for adjusting goals"""
    goalformname = "goal_%s" % (basename.replace("/", "_").replace(".", "_"))
    goalnames = self.project.getgoalnames()
    useroptions = []
    for goalname in filegoals:
      useroptions += self.project.getgoalusers(goalname)
    multifiles = None
    if len(filegoals) > 1:
      multifiles = "multiple"
    multiusers = None
    assignusers = []
    assignwhich = []
    if len(useroptions) > 1:
      assignfilenames = self.project.browsefiles(dirfilter=goalfile)
      if self.currentgoal:
        action = "goal-" + self.currentgoal
      else:
        action = None
      assignstats = self.project.combineassignstats(assignfilenames, action)
      assignusers = [username.replace("assign-", "", 1) for username in assignstats.iterkeys()]
      useroptions += [username for username in assignusers if username not in useroptions]
      if len(assignusers) > 1:
        multiusers = "multiple"
      assignwhich = [('all', self.localize("All Strings")), ('untranslated', self.localize("Untranslated")), ('unassigned', self.localize('Unassigned')), ('unassigneduntranslated', self.localize("Unassigned and Untranslated"))]
    return {
     "name": goalformname,
     "filename": basename,
     "goalnames": goalnames,
     "filegoals": dict([(goalname, goalname in filegoals or None) for goalname in goalnames]),
     "multifiles": multifiles,
     "setgoal_text": self.localize("Set Goal"),
     "users": useroptions,
     "assignusers": dict([(username, username in assignusers or None) for username in useroptions]),
     "multiusers": multiusers,
     "assignwhich": [{"value": value, "text": text} for value, text in assignwhich],
     "assignto_text": self.localize("Assign To"),
     }

  def getactionlinks(self, basename, projectstats, linksrequired=None, filepath=None, goal=None):
    """get links to the actions that can be taken on an item (directory / file)"""
    if linksrequired is None:
      linksrequired = ["mine", "review", "quick", "all"]
    actionlinks = []
    actions = {}
    if not basename or basename.endswith("/"):
      baseactionlink = basename + "translate.html?"
      baseindexlink = basename + "index.html?"
    else:
      baseactionlink = "%s?translate=1" % basename
      baseindexlink = "%s?index=1" % basename
    if goal:
      baseactionlink += "&goal=%s" % goal
      baseindexlink += "&goal=%s" % goal
    def addoptionlink(linkname, rightrequired, attrname, showtext, hidetext):
      if linkname in linksrequired:
        if rightrequired and not rightrequired in self.rights:
          return
        if getattr(self, attrname, False):
          link = {"href": self.makelink(baseindexlink, **{attrname:0}), "text": hidetext}
        else:
          link = {"href": self.makelink(baseindexlink, **{attrname:1}), "text": showtext}
        link["sep"] = " | "
        actionlinks.append(link)
    addoptionlink("track", None, "showtracks", self.localize("Show Tracks"), self.localize("Hide Tracks"))
    addoptionlink("check", "translate", "showchecks", self.localize("Show Checks"), self.localize("Hide Checks"))
    addoptionlink("goal", None, "showgoals", self.localize("Show Goals"), self.localize("Hide Goals"))
    addoptionlink("assign", "translate", "showassigns", self.localize("Show Assigns"), self.localize("Hide Assigns"))
    actions["basic"] = actionlinks
    actionlinks = []
    if not goal:
      goalfile = os.path.join(self.dirname, basename)
      filegoals = self.project.getfilegoals(goalfile)
      if self.showgoals:
        if len(filegoals) > 1:
          actionlinks.append(self.localize("All Goals: %s", (", ".join(filegoals))))
      if "editgoal" in linksrequired and "admin" in self.rights:
        actions["goalform"] = self.getgoalform(basename, goalfile, filegoals)
    if "mine" in linksrequired and self.session.isopen:
      if "translate" in self.rights:
        minelink = self.localize("Translate My Strings")
      else:
        minelink = self.localize("View My Strings")
      mystats = projectstats.get("assign-%s" % self.session.username, [])
      if len(mystats):
        minelink = {"href": self.makelink(baseactionlink, assignedto=self.session.username), "text": minelink}
      else:
        minelink = {"title": self.localize("No strings assigned to you"), "text": minelink}
      actionlinks.append(minelink)
      if "quick" in linksrequired and "translate" in self.rights:
        mytranslatedstats = [statsitem for statsitem in mystats if statsitem in projectstats.get("translated", [])]
        quickminelink = self.localize("Quick Translate My Strings")
        if len(mytranslatedstats) < len(mystats):
          quickminelink = {"href": self.makelink(baseactionlink, assignedto=self.session.username, fuzzy=1, blank=1), "text": quickminelink}
        else:
          quickminelink = {"title": self.localize("No untranslated strings assigned to you"), "text": quickminelink}
        actionlinks.append(quickminelink)
    if "review" in linksrequired and projectstats.get("has-suggestion", []):
      if "review" in self.rights:
        reviewlink = self.localize("Review Suggestions")
      else:
        reviewlink = self.localize("View Suggestions")
      reviewlink = {"href": self.makelink(baseactionlink, review=1, **{"has-suggestion": 1}), "text": reviewlink}
      actionlinks.append(reviewlink)
    if "quick" in linksrequired:
      if "translate" in self.rights:
        quicklink = self.localize("Quick Translate")
      else:
        quicklink = self.localize("View Untranslated")
      if len(projectstats.get("translated", [])) < len(projectstats.get("total", [])):
        quicklink = {"href": self.makelink(baseactionlink, fuzzy=1, blank=1), "text": quicklink}
      else:
        quicklink = {"title": self.localize("No untranslated items"), "text": quicklink}
      actionlinks.append(quicklink)
    if "all" in linksrequired and "translate" in self.rights:
      translatelink = {"href": self.makelink(baseactionlink), "text": self.localize('Translate All')}
      actionlinks.append(translatelink)
    if "zip" in linksrequired and "archive" in self.rights:
      if filepath and filepath.endswith(".po"):
        currentfolder = "/".join(filepath.split("/")[:-1])
      else:
        currentfolder = filepath
      archivename = "%s-%s" % (self.project.projectcode, self.project.languagecode)
      if currentfolder:
        archivename += "-%s" % currentfolder.replace("/", "-")
      if goal:
        archivename += "-%s" % goal
      archivename += ".zip"
      if goal:
        archivename += "?goal=%s" % goal
        linktext = self.localize('ZIP of goal')
      else:
        linktext = self.localize('ZIP of folder')
      ziplink = {"href": archivename, "text": linktext, "title": archivename}
      actionlinks.append(ziplink)

    if "sdf" in linksrequired and "pocompile" in self.rights and \
        self.project.ootemplate() and not (basename or filepath):
      archivename = self.project.languagecode + ".sdf"
      linktext = self.localize('Generate SDF')
      oolink = {"href": archivename, "text": linktext, "title": archivename}
      actionlinks.append(oolink)
    for n, actionlink in enumerate(actionlinks):
      if n < len(actionlinks)-1:
        actionlink["sep"] = " | "
      else:
        actionlink["sep"] = ""
    actions["extended"] = actionlinks
    if not actions["extended"] and not actions["goalform"] and actions["basic"]:
      actions["basic"][-1]["sep"] = ""
    return actions

  def getitemstats(self, basename, projectstats, numfiles):
    """returns a widget summarizing item statistics"""
    statssummary = self.describestats(self.project, projectstats, numfiles)
    stats = {"summary": statssummary, "checks": [], "tracks": [], "assigns": []}
    if not basename or basename.endswith("/"):
      linkbase = basename + "translate.html?"
    else:
      linkbase = basename + "?translate=1"
    if projectstats:
      if self.showchecks:
        stats["checks"] = self.getcheckdetails(projectstats, linkbase)
      if self.showtracks:
        trackfilter = (self.dirfilter or "") + basename
        trackpofilenames = self.project.browsefiles(trackfilter)
        projecttracks = self.project.gettracks(trackpofilenames)
        stats["tracks"] = self.gettrackdetails(projecttracks, linkbase)
      if self.showassigns:
        if not basename or basename.endswith("/"):
          removelinkbase = "?showassigns=1&removeassigns=1"
        else:
          removelinkbase = "?showassigns=1&removeassigns=1&removefilter=%s" % basename
        stats["assigns"] = self.getassigndetails(projectstats, linkbase, removelinkbase)
    return stats

  def gettrackdetails(self, projecttracks, linkbase):
    """return a list of strings describing the results of tracks"""
    return [trackmessage for trackmessage in projecttracks]

  def getcheckdetails(self, projectstats, linkbase):
    """return a list of strings describing the results of checks"""
    total = max(len(projectstats.get("total", [])), 1)
    checklinks = []
    keys = projectstats.keys()
    keys.sort()
    for checkname in keys:
      if not checkname.startswith("check-"):
        continue
      checkcount = len(projectstats[checkname])
      checkname = checkname.replace("check-", "", 1)
      if total and checkcount:
        stats = self.nlocalize("%d string (%d%%) failed", "%d strings (%d%%) failed", checkcount, checkcount, (checkcount * 100 / total))
        checklink = {"href": self.makelink(linkbase, **{checkname:1}), "text": checkname, "stats": stats}
        checklinks += [checklink]
    return checklinks

  def getassigndetails(self, projectstats, linkbase, removelinkbase):
    """return a list of strings describing the assigned strings"""
    # TODO: allow setting of action, so goals can only show the appropriate action assigns
    total = projectstats.get("total", [])
    # quick lookup of what has been translated
    translated = dict.fromkeys(projectstats.get("translated", []))
    totalcount = len(total)
    totalwords = self.project.countwords(total)
    assignlinks = []
    keys = projectstats.keys()
    keys.sort()
    for assignname in keys:
      if not assignname.startswith("assign-"):
        continue
      assigned = projectstats[assignname]
      assigncount = len(assigned)
      assignwords = self.project.countwords(assigned)
      complete = [statsitem for statsitem in assigned if statsitem in translated]
      completecount = len(complete)
      completewords = self.project.countwords(complete)
      assignname = assignname.replace("assign-", "", 1)
      if totalcount and assigncount:
        assignlink = {"href": self.makelink(linkbase, assignedto=assignname), "text": assignname}
        percentassigned = assignwords * 100 / max(totalwords, 1)
        percentcomplete = completewords * 100 / max(assignwords, 1)
        stats = self.localize("%d/%d words (%d%%) assigned", assignwords, totalwords, percentassigned)
        stringstats = self.localize("[%d/%d strings]", assigncount, totalcount)
        completestats = self.localize("%d/%d words (%d%%) translated", completewords, assignwords, percentcomplete)
        completestringstats = self.localize("[%d/%d strings]", completecount, assigncount)
        if "assign" in self.rights:
          removetext = self.localize("Remove")
          removelink = {"href": self.makelink(removelinkbase, assignedto=assignname), "text": removetext}
        else:
          removelink = None
        assignlinks.append({"assign": assignlink, "stats": stats, "stringstats": stringstats, "completestats": completestats, "completestringstats": completestringstats, "remove": removelink})
    return assignlinks

