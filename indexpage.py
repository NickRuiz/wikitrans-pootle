#!/usr/bin/env python

from jToolkit.widgets import widgets
from Pootle import pagelayout
from Pootle import projects
from Pootle import pootlefile
from Pootle import versioncontrol
from Pootle import __version__ as pootleversion
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
    title = pagelayout.Title(pagetitle)
    description = pagelayout.IntroText(getattr(session.instance, "description"))
    abouttitle = pagelayout.Title(self.localize("About Pootle"))
    introtext = pagelayout.IntroText(self.localize("<strong>Pootle</strong> is a simple web portal that should allow you to <strong>translate</strong>! Since Pootle is <strong>Free Software</strong>, you can download it and run your own copy if you like. You can also help participate in the development in many ways (you don't have to be able to program)."))
    hosttext = pagelayout.IntroText(self.localize('The Pootle project itself is hosted at <a href="http://translate.sourceforge.net/">translate.sourceforge.net</a> where you can find the details about source code, mailing lists etc.'))
    nametext = pagelayout.IntroText(self.localize('The name stands for <b>PO</b>-based <b>O</b>nline <b>T</b>ranslation / <b>L</b>ocalization <b>E</b>ngine, but you may need to read <a href="http://www.thechestnut.com/flumps.htm">this</a>.'))
    versiontitle = pagelayout.Title(self.localize("Versions"))
    versiontext = pagelayout.IntroText(self.localize("This site is running:<br/>Pootle %s</br>jToolkit %s</br>Python %s (on %s/%s)") % (pootleversion.ver, jtoolkitversion.ver, sys.version, sys.platform, os.name))
    aboutpootle = [abouttitle, introtext, hosttext, nametext, versiontitle, versiontext]
    contents = pagelayout.Contents([title, description, aboutpootle])
    pagelayout.PootlePage.__init__(self, pagetitle, contents, session)

class PootleIndex(pagelayout.PootlePage):
  """the main page"""
  def __init__(self, potree, session):
    self.potree = potree
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    aboutlink = pagelayout.IntroText(widgets.Link("/about.html", self.localize("About this Pootle server")))
    languagelinks = self.getlanguagelinks()
    projectlinks = self.getprojectlinks()
    contents = [aboutlink, languagelinks, projectlinks]
    pagelayout.PootlePage.__init__(self, self.localize("Pootle"), contents, session)

  def getlanguagelinks(self):
    """gets the links to the languages"""
    languagestitle = pagelayout.Title(widgets.Link("languages/", self.localize('Languages')))
    languagelinks = []
    for languagecode in self.potree.getlanguagecodes():
      languagename = self.potree.getlanguagename(languagecode)
      languagelink = widgets.Link(languagecode+"/", languagename)
      languagelinks.append(languagelink)
    listwidget = widgets.SeparatedList(languagelinks, ", ")
    bodydescription = pagelayout.ItemDescription(listwidget)
    return pagelayout.Contents([languagestitle, bodydescription])

  def getprojectlinks(self):
    """gets the links to the projects"""
    projectstitle = pagelayout.Title(widgets.Link("projects/", self.localize("Projects")))
    projectlinks = []
    for projectcode in self.potree.getprojectcodes():
      projectname = self.potree.getprojectname(projectcode)
      projectdescription = self.potree.getprojectdescription(projectcode)
      projectlink = widgets.Link("projects/%s/" % projectcode, projectname, {"title":projectdescription})
      projectlinks.append(projectlink)
    listwidget = widgets.SeparatedList(projectlinks, ", ")
    bodydescription = pagelayout.ItemDescription(listwidget)
    return pagelayout.Contents([projectstitle, bodydescription])

class UserIndex(pagelayout.PootlePage):
  """home page for a given user"""
  def __init__(self, potree, session):
    self.potree = potree
    self.session = session
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    optionslink = pagelayout.IntroText(widgets.Link("options.html", self.localize("Change options")))
    contents = [self.getquicklinks(), optionslink]
    if session.issiteadmin():
      adminlink = pagelayout.IntroText(widgets.Link("../admin/", self.localize("Admin page")))
      contents.append(adminlink)
    pagelayout.PootlePage.__init__(self, self.localize("User Page for: %s") % session.username, contents, session)

  def getquicklinks(self):
    """gets a set of quick links to user's project-languages"""
    quicklinkstitle = pagelayout.Title(self.localize("Quick Links"))
    quicklinks = []
    for languagecode in self.session.getlanguages():
      if not self.potree.haslanguage(languagecode):
        continue
      languagename = self.potree.getlanguagename(languagecode)
      languagelink = widgets.Link("../%s/" % languagecode, languagename)
      quicklinks.append(pagelayout.Title(languagelink))
      languagelinks = []
      for projectcode in self.session.getprojects():
        if self.potree.hasproject(languagecode, projectcode):
          projectname = self.potree.getprojectname(projectcode)
          projecturl = "../%s/%s/" % (languagecode, projectcode)
          projecttitle = self.localize("%s %s") % (languagename, projectname)
          languagelinks.append([widgets.Link(projecturl, projecttitle), "<br/>"])
      quicklinks.append(pagelayout.ItemDescription(languagelinks))
    if not quicklinks:
      setoptionstext = self.localize("Please click on 'Change options' and select some languages and projects")
      quicklinks.append(pagelayout.ItemDescription(setoptionstext))
    return pagelayout.Contents([quicklinkstitle, quicklinks])

class ProjectsIndex(PootleIndex):
  """the list of projects"""
  def getlanguagelinks(self):
    """we don't need language links on the project page"""
    return ""

  def getprojectlinks(self):
    """gets the links to the projects"""
    projectstitle = pagelayout.Title(self.localize("Projects"))
    projectlinks = []
    for projectcode in self.potree.getprojectcodes():
      projectname = self.potree.getprojectname(projectcode)
      projectdescription = self.potree.getprojectdescription(projectcode)
      projectlink = widgets.Link("%s/" % projectcode, projectname, {"title":projectdescription})
      projectlinks.append(projectlink)
    listwidget = widgets.SeparatedList(projectlinks, ", ")
    bodydescription = pagelayout.ItemDescription(listwidget)
    return pagelayout.Contents([projectstitle, bodydescription])

class LanguagesIndex(PootleIndex):
  """the list of languages"""

  def getlanguagelinks(self):
    """gets the links to the languages"""
    languagestitle = pagelayout.Title(self.localize("Languages"))
    languagelinks = []
    for languagecode in self.potree.getlanguagecodes():
      languagename = self.potree.getlanguagename(languagecode)
      languagelink = widgets.Link("../%s/" % languagecode, languagename)
      languagelinks.append(languagelink)
    listwidget = widgets.SeparatedList(languagelinks, ", ")
    bodydescription = pagelayout.ItemDescription(listwidget)
    return pagelayout.Contents([languagestitle, bodydescription])

  def getprojectlinks(self):
    """we don't need project links on the language page"""
    return ""

class LanguageIndex(pagelayout.PootleNavPage):
  """the main page"""
  def __init__(self, potree, languagecode, session):
    self.potree = potree
    self.languagecode = languagecode
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    languagename = self.potree.getlanguagename(self.languagecode)
    self.initpagestats()
    projectlinks = self.getprojectlinks()
    average = self.getpagestats()
    languagestats = self.nlocalize("%d project, average %d%% translated", "%d projects, average %d%% translated", self.projectcount) % (self.projectcount, average)
    navbar = self.makenavbar(icon="language", path=self.makenavbarpath(language=(self.languagecode, languagename)), stats=languagestats)
    pagelayout.PootleNavPage.__init__(self, self.localize("Pootle: %s") % languagename, [navbar, projectlinks], session, bannerheight=81, returnurl="%s/" % self.languagecode)

  def getprojectlinks(self):
    """gets the links to the projects"""
    projectcodes = self.potree.getprojectcodes(self.languagecode)
    self.projectcount = len(projectcodes)
    projectitems = [self.getprojectitem(projectcode) for projectcode in projectcodes]
    self.polarizeitems(projectitems)
    return projectitems

  def getprojectitem(self, projectcode):
    projectname = self.potree.getprojectname(projectcode)
    projectdescription = self.potree.getprojectdescription(projectcode)
    projecttitle = pagelayout.Title(widgets.Link(projectcode+"/", projectname, {"title": projectdescription}))
    projecticon = self.geticon("project")
    body = pagelayout.ContentsItem([projecticon, projecttitle])
    project = self.potree.getproject(self.languagecode, projectcode)
    numfiles = len(project.pofilenames)
    projectstats = project.combinestats()
    translated = projectstats.get("translated", [])
    total = projectstats.get("total", [])
    translatedwords = project.countwords(translated)
    totalwords = project.countwords(total)
    self.updatepagestats(translatedwords, totalwords)
    stats = pagelayout.ItemStatistics(self.describestats(project, projectstats, numfiles))
    return pagelayout.Item([body, stats])

class ProjectLanguageIndex(pagelayout.PootleNavPage):
  """list of languages belonging to a project"""
  def __init__(self, potree, projectcode, session):
    self.potree = potree
    self.projectcode = projectcode
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    projectname = self.potree.getprojectname(self.projectcode)
    adminlink = []
    if session.issiteadmin():
      adminlink = widgets.Link("admin.html", self.localize("Admin"))
    self.initpagestats()
    languagelinks = self.getlanguagelinks()
    average = self.getpagestats()
    projectstats = self.nlocalize("%d language, average %d%% translated", "%d languages, average %d%% translated", self.languagecount) % (self.languagecount, average)
    navbar = self.makenavbar(icon="project", path=self.makenavbarpath(session=session, project=(self.projectcode, projectname)), actions=adminlink, stats=projectstats)
    pagelayout.PootleNavPage.__init__(self, self.localize("Pootle: %s") % projectname, [navbar, languagelinks], session, bannerheight=81, returnurl="projects/%s/" % self.projectcode)

  def getlanguagelinks(self):
    """gets the links to the languages"""
    languagecodes = self.potree.getlanguagecodes(self.projectcode)
    self.languagecount = len(languagecodes)
    languageitems = [self.getlanguageitem(languagecode) for languagecode in languagecodes]
    self.polarizeitems(languageitems)
    return languageitems

  def getlanguageitem(self, languagecode):
    languagename = self.potree.getlanguagename(languagecode)
    languagetitle = pagelayout.Title(widgets.Link("../../%s/%s/" % (languagecode, self.projectcode), languagename))
    languageicon = self.geticon("language")
    body = pagelayout.ContentsItem([languageicon, languagetitle])
    language = self.potree.getproject(languagecode, self.projectcode)
    numfiles = len(language.pofilenames)
    languagestats = language.combinestats()
    translated = languagestats.get("translated", [])
    total = languagestats.get("total", [])
    translatedwords = language.countwords(translated)
    totalwords = language.countwords(total)
    self.updatepagestats(translatedwords, totalwords)
    percentfinished = (translatedwords*100/max(totalwords, 1))
    filestats = self.nlocalize("%d file", "%d files", numfiles) % numfiles
    wordstats = self.localize("%d/%d words (%d%%) translated") % (translatedwords, totalwords, percentfinished)
    stringstats = widgets.Span(self.localize("[%d/%d strings]") % (len(translated), len(total)), cls="string-statistics")
    stats = pagelayout.ItemStatistics([filestats, ", ", wordstats, " ", stringstats])
    return pagelayout.Item([body, stats])

class ProjectIndex(pagelayout.PootleNavPage):
  """the main page"""
  def __init__(self, project, session, argdict, dirfilter=None):
    self.project = project
    self.session = session
    self.localize = session.localize
    self.nlocalize = session.nlocalize
    self.rights = self.project.getrights(self.session)
    message = argdict.get("message", "")
    if message:
      message = pagelayout.IntroText(message)
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
      mainstats = []
      mainicon = "file"
    else:
      pofilenames = self.project.browsefiles(dirfilter)
      projectstats = self.project.combinestats(pofilenames)
      actionlinks = self.getactionlinks("", projectstats, ["mine", "review", "check", "assign", "goal", "quick", "all", "zip"], dirfilter)
      mainstats = self.getitemstats("", projectstats, len(pofilenames))
      mainicon = "folder"
    navbar = self.makenavbar(icon=mainicon, path=self.makenavbarpath(project=self.project, session=self.session, currentfolder=dirfilter, goal=self.currentgoal), actions=actionlinks, stats=mainstats)
    if self.showgoals:
      childitems = self.getgoalitems(dirfilter)
    else:
      childitems = self.getchilditems(dirfilter)
    pagetitle = self.localize("Pootle: Project %s, Language %s") % (self.project.projectname, self.project.languagename)
    pagelayout.PootleNavPage.__init__(self, pagetitle, [message, navbar, childitems], session, bannerheight=81, returnurl="%s/%s/%s/" % (self.project.languagecode, self.project.projectcode, self.dirname))
    self.addsearchbox(searchtext="", action="translate.html")
    if self.showassigns and "assign" in self.rights:
      self.addassignbox()
    if "admin" in self.rights:
      if self.showgoals:
        self.addgoalbox()
    if "admin" in self.rights or "translate" in self.rights:
      self.adduploadbox()

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

  def addfolderlinks(self, title, foldername, folderlink, tooltip=None, enhancelink=True):
    """adds a folder link to the sidebar"""
    if enhancelink:
      folderlink = self.makelink(folderlink)
    return pagelayout.PootlePage.addfolderlinks(self, title, foldername, folderlink, tooltip)

  def addassignbox(self):
    """adds a box that lets the user assign strings"""
    self.links.addcontents(pagelayout.SidebarTitle(self.localize("Assign Strings")))
    users = [username for username, userprefs in self.session.loginchecker.users.iteritems() if username != "__dummy__"]
    users.sort()
    assigntoselect = widgets.Select({"name": "assignto", "value": "", "title": self.localize("Assign to User")}, options=[(user, user) for user in users])
    actionbox = widgets.Input({"name": "action", "value": "translate", "title": self.localize("Assign Action")})
    submitbutton = widgets.Input({"type": "submit", "name": "doassign", "value": self.localize("Assign Strings")})
    assignform = widgets.Form([assigntoselect, actionbox, submitbutton], {"action": "", "name":"assignform"})
    self.links.addcontents(assignform)

  def addgoalbox(self):
    """adds a box that lets the user add a new goal"""
    self.links.addcontents(pagelayout.SidebarTitle(self.localize("Goals")))
    namebox = widgets.Input({"type": "text", "name": "newgoal", "title": self.localize("Enter goal name")})
    submitbutton = widgets.Input({"type": "submit", "name": "doaddgoal", "value": self.localize("Add Goal")})
    goalform = widgets.Form([namebox, submitbutton], {"action": "", "name":"goalform"})
    self.links.addcontents(goalform)

  def adduploadbox(self):
    """adds a box that lets the user assign strings"""
    self.links.addcontents(pagelayout.SidebarTitle(self.localize("Upload File")))
    filebox = widgets.Input({"type": "file", "name": "uploadfile", "title": self.localize("Select file to upload")})
    submitbutton = widgets.Input({"type": "submit", "name": "doupload", "value": self.localize("Upload File")})
    uploadform = widgets.Form([filebox, submitbutton], {"action": "", "name":"uploadform", "enctype": "multipart/form-data"})
    self.links.addcontents(uploadform)

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
    if goalname:
      bodytitle = pagelayout.Title(goalname)
    else:
      bodytitle = pagelayout.Title(self.localize("No goal"))
    folderimage = pagelayout.Icon("goal.png")
    browseurl = self.makelink("index.html", goal=goalname)
    bodytitle = widgets.Link(browseurl, bodytitle)
    if pofilenames:
      actionlinks = self.getactionlinks("", projectstats, linksrequired=["mine", "review", "translate", "zip"], goal=goalname)
      bodydescription = pagelayout.ActionLinks(actionlinks)
    else:
      bodydescription = []
    usericon = pagelayout.Icon("person.png")
    goaluserslist = []
    if goalusers:
      goalusers.sort()
      goaluserslist = widgets.SeparatedList(goalusers)
    if goalname and self.currentgoal == goalname:
      if "admin" in self.rights:
        unassignedusers = [username for username, userprefs in self.session.loginchecker.users.iteritems() if username != "__dummy__"]
        for user in goalusers:
          if user in unassignedusers:
            unassignedusers.remove(user)
        unassignedusers.sort()
        adduserlist = widgets.Select({"name": "newgoaluser"}, options=[(user, user) for user in unassignedusers])
        editgoalname = widgets.HiddenFieldList({"editgoalname": goalname})
        submitbutton = widgets.Input({"type": "submit", "name": "doeditgoalusers", "value": self.localize("Add User")})
        userwidgets = [usericon, editgoalname, goaluserslist, adduserlist, submitbutton]
        userlist = widgets.Division(widgets.Form(userwidgets, {"action": "", "name": "goaluserform"}))
      else:
        userlist = widgets.Division([usericon, goaluserslist])
    elif goalusers:
      userlist = widgets.Division([usericon, goaluserslist])
    else:
      userlist = []
    body = pagelayout.ContentsItem([folderimage, bodytitle, bodydescription, userlist])
    stats = self.getitemstats("", projectstats, len(pofilenames))
    return pagelayout.GoalItem([body, stats])

  def getdiritem(self, direntry, linksrequired=None, **newargs):
    """returns an item showing a directory entry"""
    pofilenames = self.project.browsefiles(direntry)
    if self.showgoals and "goal" in self.argdict:
      goalfilenames = self.project.getgoalfiles(self.currentgoal, dirfilter=direntry, includedirs=False, expanddirs=True)
      projectstats = self.project.combinestats(goalfilenames)
    else:
      projectstats = self.project.combinestats(pofilenames)
    basename = os.path.basename(direntry)
    bodytitle = pagelayout.Title(basename)
    basename += "/"
    folderimage = pagelayout.Icon("folder.png")
    browseurl = self.getbrowseurl(basename, **newargs)
    bodytitle = widgets.Link(browseurl, bodytitle)
    actionlinks = self.getactionlinks(basename, projectstats, linksrequired=linksrequired)
    bodydescription = pagelayout.ActionLinks(actionlinks)
    body = pagelayout.ContentsItem([folderimage, bodytitle, bodydescription])
    if self.showgoals and "goal" in self.argdict:
      stats = self.getitemstats(basename, projectstats, (len(goalfilenames), len(pofilenames)))
    else:
      stats = self.getitemstats(basename, projectstats, len(pofilenames))
    return pagelayout.Item([body, stats])

  def getfileitem(self, fileentry, linksrequired=None, **newargs):
    """returns an item showing a file entry"""
    if linksrequired is None:
      linksrequired = ["mine", "review", "quick", "all", "po", "xliff", "csv", "mo", "update"]
    basename = os.path.basename(fileentry)
    projectstats = self.project.combinestats([fileentry])
    folderimage = pagelayout.Icon("file.png")
    browseurl = self.getbrowseurl(basename, **newargs)
    bodytitle = pagelayout.Title(widgets.Link(browseurl, basename))
    actionlinks = self.getactionlinks(basename, projectstats, linksrequired=linksrequired)
    if "po" in linksrequired:
      downloadlink = widgets.Link(basename, self.localize('PO file'))
      actionlinks.append(downloadlink)
    if "xliff" in linksrequired and "translate" in self.rights:
      xliffname = basename.replace(".po", ".xlf")
      xlifflink = widgets.Link(xliffname, self.localize('XLIFF file'))
      actionlinks.append(xlifflink)
    if "csv" in linksrequired and "translate" in self.rights:
      csvname = basename.replace(".po", ".csv")
      csvlink = widgets.Link(csvname, self.localize('CSV file'))
      actionlinks.append(csvlink)
    if "mo" in linksrequired:
      if self.project.hascreatemofiles(self.project.projectcode) and "pocompile" in self.rights:
        moname = basename.replace(".po", ".mo")
        molink = widgets.Link(moname, self.localize('MO file'))
        actionlinks.append(molink)
    if "update" in linksrequired and "admin" in self.rights:
      if versioncontrol.hasversioning(os.path.join(self.project.podir, self.dirname)):
        updatelink = widgets.Link("index.html?doupdate=1&updatefile=%s" % basename, self.localize('Update'))
        actionlinks.append(updatelink)
    bodydescription = pagelayout.ActionLinks(actionlinks)
    body = pagelayout.ContentsItem([folderimage, bodytitle, bodydescription])
    stats = self.getitemstats(basename, projectstats, None)
    return pagelayout.Item([body, stats])

  def getactionlinks(self, basename, projectstats, linksrequired=None, filepath=None, goal=None):
    """get links to the actions that can be taken on an item (directory / file)"""
    if linksrequired is None:
      linksrequired = ["mine", "review", "quick", "all"]
    actionlinks = []
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
          link = widgets.Link(self.makelink(baseindexlink, **{attrname:0}), hidetext)
        else:
          link = widgets.Link(self.makelink(baseindexlink, **{attrname:1}), showtext)
        actionlinks.append(link)
    addoptionlink("track", None, "showtracks", self.localize("Show Tracks"), self.localize("Hide Tracks"))
    addoptionlink("check", "translate", "showchecks", self.localize("Show Checks"), self.localize("Hide Checks"))
    addoptionlink("goal", None, "showgoals", self.localize("Show Goals"), self.localize("Hide Goals"))
    addoptionlink("assign", "translate", "showassigns", self.localize("Show Assigns"), self.localize("Hide Assigns"))
    if not goal:
      goalformname = "goal_%s" % (basename.replace("/", "_").replace(".", "_"))
      goalfile = os.path.join(self.dirname, basename)
      filegoals = self.project.getfilegoals(goalfile)
      if self.showgoals:
        if len(filegoals) > 1:
          actionlinks.append(self.localize("All Goals: %s") % (", ".join(filegoals)))
      if "editgoal" in linksrequired and "admin" in self.rights:
        goaloptions = [('', '')] + [(goalname, goalname) for goalname in self.project.getgoalnames()]
        useroptions = ['']
        for goalname in filegoals:
          useroptions += self.project.getgoalusers(goalname)
        if len(filegoals) > 1:
          goalselect = widgets.MultiSelect({"name": "editgoal", "value": filegoals}, goaloptions)
        else:
          goalselect = widgets.Select({"name": "editgoal", "value": ''.join(filegoals)}, goaloptions)
        editgoalfile = widgets.HiddenFieldList({"editgoalfile": basename})
        editfilegoal = widgets.Input({"type": "submit", "name": "doeditgoal", "value": self.localize("Set Goal")})
        if len(useroptions) > 1:
          assignfilenames = self.project.browsefiles(dirfilter=goalfile)
          if self.currentgoal:
            action = "goal-" + self.currentgoal
          else:
            action = None
          assignstats = self.project.combineassignstats(assignfilenames, action)
          assignusers = [username.replace("assign-", "", 1) for username in assignstats.iterkeys()]
          useroptions += [username for username in assignusers if username not in useroptions]
          # need code and description for options list
          useroptions = [(username, username) for username in useroptions]
          if len(assignusers) > 1:
            userselect = widgets.MultiSelect({"name": "editfileuser", "value": assignusers}, useroptions)
          else:
            # use a normal Select, but allow the user to convert it to a Multi at a click
            userselect = widgets.Select({"name": "editfileuser", "value": ''.join(assignusers)}, useroptions)
            multiscript = 'var userselect = document.forms.%s.editfileuser; userselect.multiple = true; return false' % goalformname
            allowmulti = widgets.HiddenFieldList({"allowmultikey": "editfileuser"})
            multilink = widgets.Link("#", self.localize("Select Multiple"), {"onclick": multiscript})
            userselect = [userselect, multilink, allowmulti]
          assignwhichoptions = [('all', self.localize("All Strings")), ('untranslated', self.localize("Untranslated")), ('unassigned', self.localize('Unassigned')), ('unassigneduntranslated', self.localize("Unassigned and Untranslated"))]
          assignwhich = widgets.Select({"name": "edituserwhich", "value": "all"}, assignwhichoptions)
          editfileuser = widgets.Input({"type": "submit", "name": "doedituser", "value": self.localize("Assign To")})
          changeuser = [userselect, assignwhich, editfileuser]
        else:
          changeuser = []
        goalform = widgets.Form([editgoalfile, goalselect, editfilegoal, changeuser], {"action": "", "name":goalformname})
        actionlinks.append(goalform)
    if "mine" in linksrequired and self.session.isopen:
      if "translate" in self.rights:
        minelink = self.localize("Translate My Strings")
      else:
        minelink = self.localize("View My Strings")
      mystats = projectstats.get("assign-%s" % self.session.username, [])
      if len(mystats):
        minelink = widgets.Link(self.makelink(baseactionlink, assignedto=self.session.username), minelink)
      else:
        minelink = widgets.Tooltip(self.localize("No strings assigned to you"), minelink)
      actionlinks.append(minelink)
      if "quick" in linksrequired and "translate" in self.rights:
        mytranslatedstats = [statsitem for statsitem in mystats if statsitem in projectstats.get("translated", [])]
        quickminelink = self.localize("Quick Translate My Strings")
        if len(mytranslatedstats) < len(mystats):
          quickminelink = widgets.Link(self.makelink(baseactionlink, assignedto=self.session.username, fuzzy=1, blank=1), quickminelink)
        else:
          quickminelink = widgets.Tooltip(self.localize("No untranslated strings assigned to you"), quickminelink)
        actionlinks.append(quickminelink)
    if "review" in linksrequired and projectstats.get("has-suggestion", []):
      if "review" in self.rights:
        reviewlink = self.localize("Review Suggestions")
      else:
        reviewlink = self.localize("View Suggestions")
      reviewlink = widgets.Link(self.makelink(baseactionlink, review=1, **{"has-suggestion": 1}), reviewlink)
      actionlinks.append(reviewlink)
    if "quick" in linksrequired:
      if "translate" in self.rights:
        quicklink = self.localize("Quick Translate")
      else:
        quicklink = self.localize("View Untranslated")
      if len(projectstats.get("translated", [])) < len(projectstats.get("total", [])):
        quicklink = widgets.Link(self.makelink(baseactionlink, fuzzy=1, blank=1), quicklink)
      else:
        quicklink = widgets.Tooltip(self.localize("No untranslated items"), quicklink)
      actionlinks.append(quicklink)
    if "all" in linksrequired and "translate" in self.rights:
      translatelink = widgets.Link(self.makelink(baseactionlink), self.localize('Translate All'))
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
      ziplink = widgets.Link(archivename, linktext, {'title': archivename})
      actionlinks.append(ziplink)
    return actionlinks

  def getitemstats(self, basename, projectstats, numfiles):
    """returns a widget summarizing item statistics"""
    statssummary = self.describestats(self.project, projectstats, numfiles)
    statsdetails = [statssummary]
    if not basename or basename.endswith("/"):
      linkbase = basename + "translate.html?"
    else:
      linkbase = basename + "?translate=1"
    if projectstats:
      if self.showchecks:
        statsdetails = statsdetails + self.getcheckdetails(projectstats, linkbase)
      if self.showtracks:
        trackfilter = (self.dirfilter or "") + basename
        trackpofilenames = self.project.browsefiles(trackfilter)
        projecttracks = self.project.gettracks(trackpofilenames)
        statsdetails += self.gettrackdetails(projecttracks, linkbase)
      if self.showassigns:
        if not basename or basename.endswith("/"):
          removelinkbase = "?showassigns=1&removeassigns=1"
        else:
          removelinkbase = "?showassigns=1&removeassigns=1&removefilter=%s" % basename
        statsdetails = statsdetails + self.getassigndetails(projectstats, linkbase, removelinkbase)
    statsdetails = widgets.SeparatedList(statsdetails, "<br/>\n")
    return pagelayout.ItemStatistics(statsdetails)

  def gettrackdetails(self, projecttracks, linkbase):
    """return a list of strings describing the results of tracks"""
    for trackmessage in projecttracks:
      yield widgets.Span(trackmessage, cls='trackerdetails')

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
        checklink = widgets.Link(self.makelink(linkbase, **{checkname:1}), checkname)
        stats = self.nlocalize("%d string (%d%%) failed", "%d strings (%d%%) failed", checkcount) % (checkcount, (checkcount * 100 / total))
        checklinks += [[checklink, stats]]
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
        assignlink = widgets.Link(self.makelink(linkbase, assignedto=assignname), assignname)
        percentassigned = assignwords * 100 / max(totalwords, 1)
        percentcomplete = completewords * 100 / max(assignwords, 1)
        stats = self.localize("%d/%d words (%d%%) assigned") % (assignwords, totalwords, percentassigned)
        stringstats = widgets.Span(self.localize("[%d/%d strings]") % (assigncount, totalcount), cls="string-statistics")
        completestats = self.localize("%d/%d words (%d%%) translated") % (completewords, assignwords, percentcomplete)
        completestringstats = widgets.Span(self.localize("[%d/%d strings]") % (completecount, assigncount), cls="string-statistics")
        if "assign" in self.rights:
          removetext = self.localize("Remove")
          removelink = widgets.Link(self.makelink(removelinkbase, assignedto=assignname), removetext)
        else:
          removelink = []
        assignlinks += [[assignlink, ": ", stats, " ", stringstats, " - ", completestats, " ", completestringstats, " ", removelink]]
    return assignlinks

