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

class LanguageIndex(pagelayout.PootlePage):
  """the main page"""
  def __init__(self, potree, languagecode, session):
    self.potree = potree
    self.languagecode = languagecode
    self.localize = session.localize
    languagename = self.potree.getlanguagename(self.languagecode)
    self.initpagestats()
    projectlinks = self.getprojectlinks()
    self.average = self.getpagestats()
    languagestats = self.localize("%d projects, average %d%% translated" % (self.projectcount, self.average))
    navbar = self.makenavbar(icon="language", path=self.makenavbarpath(language=(self.languagecode, languagename)), stats=languagestats)
    pagelayout.PootlePage.__init__(self, self.localize("Pootle: %s") % languagename, [navbar, projectlinks], session, bannerheight=81, returnurl="%s/" % self.languagecode)

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
    projectstats = project.calculatestats()
    translated = projectstats.get("translated", 0)
    total = projectstats.get("total", 0)
    self.updatepagestats(translated, total)
    percentfinished = (translated*100/max(total, 1))
    stats = pagelayout.ItemStatistics(self.localize("%d files, %d/%d strings (%d%%) translated") % (numfiles, translated, total, percentfinished))
    return pagelayout.Item([body, stats])

class ProjectLanguageIndex(pagelayout.PootlePage):
  """list of languages belonging to a project"""
  def __init__(self, potree, projectcode, session):
    self.potree = potree
    self.projectcode = projectcode
    self.localize = session.localize
    projectname = self.potree.getprojectname(self.projectcode)
    adminlink = []
    if session.issiteadmin():
      adminlink = widgets.Link("admin.html", self.localize("Admin"))
    self.initpagestats()
    languagelinks = self.getlanguagelinks()
    self.average = self.getpagestats()
    projectstats = self.localize("%d languages, average %d%% translated" % (self.languagecount, self.average))
    navbar = self.makenavbar(icon="project", path=self.makenavbarpath(session=session, project=(self.projectcode, projectname)), actions=adminlink, stats=projectstats)
    pagelayout.PootlePage.__init__(self, self.localize("Pootle: %s") % projectname, [navbar, languagelinks], session, bannerheight=81, returnurl="projects/%s/" % self.projectcode)

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
    languagestats = language.calculatestats()
    translated = languagestats.get("translated", 0)
    total = languagestats.get("total", 0)
    self.updatepagestats(translated, total)
    percentfinished = (translated*100/max(total, 1))
    stats = pagelayout.ItemStatistics(self.localize("%d files, %d/%d strings (%d%%) translated") % (numfiles, translated, total, percentfinished))
    return pagelayout.Item([body, stats])

class ProjectIndex(pagelayout.PootlePage):
  """the main page"""
  def __init__(self, project, session, argdict, dirfilter=None):
    self.project = project
    self.session = session
    self.localize = session.localize
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
    if dirfilter and dirfilter.endswith(".po"):
      actionlinks = []
      mainstats = []
      mainicon = "file"
    else:
      pofilenames = self.project.browsefiles(dirfilter)
      projectstats = self.project.calculatestats(pofilenames)
      actionlinks = self.getactionlinks("", projectstats, ["review", "check", "assign", "goal", "quick", "all", "zip"], dirfilter)
      mainstats = self.getitemstats("", projectstats, len(pofilenames))
      mainicon = "folder"
    mainitem = self.makenavbar(icon=mainicon, path=self.makenavbarpath(project=self.project, session=self.session, currentfolder=dirfilter), actions=actionlinks, stats=mainstats)
    if self.showgoals:
      childitems = self.getgoalitems(dirfilter)
    else:
      childitems = self.getchilditems(dirfilter)
    pagetitle = self.localize("Pootle: Project %s, Language %s") % (self.project.projectname, self.project.languagename)
    pagelayout.PootlePage.__init__(self, pagetitle, [message, mainitem, childitems], session, bannerheight=81, returnurl="%s/%s/%s/" % (self.project.languagecode, self.project.projectcode, self.dirname))
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
      goalusers = self.argdict.pop("editfileuser", "").strip()
      goalfile = self.argdict.pop("editgoalfile", None)
      if not goalfile:
        raise ValueError("cannot add goal, no filename given")
      if self.dirname:
        goalfile = os.path.join(self.dirname, goalfile)
      goalusers = [goaluser.strip() for goaluser in goalusers if goaluser.strip()]
      # self.project.setfilegoals(self.session, goalnames, goalfile)
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

  def makelink(self, link, **newargs):
    """constructs a link that keeps sticky arguments e.g. showchecks"""
    combinedargs = self.argdict.copy()
    combinedargs.update(newargs)
    if '?' in link:
      if not (link.endswith("&") or link.endswith("?")):
        link += "&"
    else:
      link += '?'
    # TODO: check escaping
    link += "&".join(["%s=%s" % (arg, value) for arg, value in combinedargs.iteritems()])
    return link

  def addfolderlinks(self, title, foldername, folderlink, tooltip=None, enhancelink=True):
    """adds a folder link to the sidebar"""
    if enhancelink:
      folderlink = self.makelink(folderlink)
    return pagelayout.PootlePage.addfolderlinks(self, title, foldername, folderlink, tooltip)

  def addassignbox(self):
    """adds a box that lets the user assign strings"""
    self.links.addcontents(pagelayout.SidebarTitle(self.localize("Assign Strings")))
    assigntobox = widgets.Input({"name": "assignto", "value": "", "title": self.localize("Assign to User")})
    actionbox = widgets.Input({"name": "action", "value": "translate", "title": self.localize("Assign Action")})
    submitbutton = widgets.Input({"type": "submit", "name": "doassign", "value": self.localize("Assign Strings")})
    assignform = widgets.Form([assigntobox, actionbox, submitbutton], {"action": "", "name":"assignform"})
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

  def getitems(self, itempaths, linksrequired=None):
    """gets the listed dir and fileitems"""
    diritems, fileitems = [], []
    for item in itempaths:
      if item.endswith(os.path.extsep + "po"):
        fileitem = self.getfileitem(item, linksrequired=linksrequired)
        fileitems.append((item, fileitem))
      else:
        if item.endswith(os.path.sep):
          item = item.rstrip(os.path.sep)
        diritem = self.getdiritem(item, linksrequired=linksrequired)
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
    for goalname in self.project.getgoalnames():
      goalfiles = self.project.getgoalfiles(goalname, dirfilter)
      if not goalfiles: continue
      initial = dirfilter
      if initial and not initial.endswith(os.path.extsep + "po"):
        initial += os.path.sep
      # TODO: fix the problem where the current directory in a goal displays as ""
      if initial:
        goalfiles = [goalfile.replace(initial, "", 1) for goalfile in goalfiles]
      goalusers = self.project.getgoalusers(goalname)
      goalitem = self.getgoalitem(goalname, goalfiles, goalusers)
      allitems.append(goalitem)
      if self.argdict.get("goal", None) == goalname:
        goalchilditems = self.getitems(goalfiles, linksrequired=["editgoal"])
        allitems.extend(goalchilditems)
      for goalfile in goalfiles:
        goalchildren[goalfile] = True
    goalless = []
    for item in allchildren:
      itemgoals = self.project.getfilegoals(item)
      if not itemgoals:
        goalless.append(item)
    goallessitems = self.getitems(goalless, linksrequired=["editgoal"])
    if goallessitems:
      goalicon = pagelayout.Icon("goal.png")
      goaltitle = pagelayout.Title(self.localize("No goal"))
      goalstats = []
      goalitem = pagelayout.GoalItem([goalicon, goaltitle, goalstats])
      allitems.append(goalitem)
      allitems.extend(goallessitems)
    return allitems

  def getgoalitem(self, goalname, goalfiles, goalusers):
    """returns an item showing a goal entry"""
    pofilenames = []
    for goalfile in goalfiles:
      recursefiles = self.project.browsefiles(goalfile)
      pofilenames.extend(recursefiles)
    projectstats = self.project.calculatestats(pofilenames)
    bodytitle = pagelayout.Title(goalname)
    folderimage = pagelayout.Icon("goal.png")
    browseurl = self.makelink("index.html", goal=goalname)
    bodytitle = widgets.Link(browseurl, bodytitle)
    actionlinks = self.getactionlinks("index.html", projectstats, linksrequired=["review", "translate", "zip"], goal=goalname)
    bodydescription = pagelayout.ActionLinks(actionlinks)
    usericon = pagelayout.Icon("person.png")
    goaluserslist = []
    if goalusers:
      goalusers.sort()
      goaluserslist = widgets.SeparatedList(goalusers)
    if self.argdict.get("goal", "") == goalname:
      unassignedusers = [username for username, userprefs in self.session.loginchecker.users.iteritems()]
      unassignedusers.remove("__dummy__")
      for user in goalusers:
        if user in unassignedusers:
          unassignedusers.remove(user)
      unassignedusers.sort()
      adduserlist = widgets.Select({"name": "newgoaluser"}, options=[(user, user) for user in unassignedusers])
      editgoalname = widgets.HiddenFieldList({"editgoalname": goalname})
      submitbutton = widgets.Input({"type": "submit", "name": "doeditgoalusers", "value": self.localize("Add User")})
      userwidgets = [usericon, editgoalname, goaluserslist, adduserlist, submitbutton]
      userlist = widgets.Division(widgets.Form(userwidgets, {"action": "", "name": "goaluserform"}))
    elif goalusers:
      userlist = widgets.Division([usericon, goaluserslist])
    else:
      userlist = []
    body = pagelayout.ContentsItem([folderimage, bodytitle, bodydescription, userlist])
    stats = self.getitemstats(goalname, projectstats, len(pofilenames))
    return pagelayout.GoalItem([body, stats])

  def getdiritem(self, direntry, linksrequired=None):
    """returns an item showing a directory entry"""
    pofilenames = self.project.browsefiles(direntry)
    projectstats = self.project.calculatestats(pofilenames)
    basename = os.path.basename(direntry)
    bodytitle = pagelayout.Title(basename)
    basename += "/"
    folderimage = pagelayout.Icon("folder.png")
    browseurl = self.getbrowseurl(basename)
    bodytitle = widgets.Link(browseurl, bodytitle)
    actionlinks = self.getactionlinks(basename, projectstats, linksrequired=linksrequired)
    bodydescription = pagelayout.ActionLinks(actionlinks)
    body = pagelayout.ContentsItem([folderimage, bodytitle, bodydescription])
    stats = self.getitemstats(basename, projectstats, len(pofilenames))
    return pagelayout.Item([body, stats])

  def getfileitem(self, fileentry, linksrequired=None):
    """returns an item showing a file entry"""
    if linksrequired is None:
      linksrequired = ["review", "quick", "all", "po", "xliff", "csv", "mo", "update"]
    basename = os.path.basename(fileentry)
    projectstats = self.project.calculatestats([fileentry])
    folderimage = pagelayout.Icon("file.png")
    browseurl = self.getbrowseurl(basename)
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

  def getbrowseurl(self, basename):
    """gets the link to browse the item"""
    if not basename or basename.endswith("/"):
      return self.makelink(basename or "index.html")
    else:
      return self.makelink(basename, translate=1, view=1)

  def getactionlinks(self, basename, projectstats, linksrequired=None, filepath=None, goal=None):
    """get links to the actions that can be taken on an item (directory / file)"""
    if linksrequired is None:
      linksrequired = ["review", "quick", "all"]
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
    addoptionlink("goal", "admin", "showgoals", self.localize("Show Goals"), self.localize("Hide Goals"))
    addoptionlink("assign", "translate", "showassigns", self.localize("Show Assigns"), self.localize("Hide Assigns"))
    if not goal:
      goalfile = os.path.join(self.dirname, basename)
      filegoals = self.project.getfilegoals(goalfile)
      if self.showgoals and "admin" in self.rights:
        if len(filegoals) > 1:
          actionlinks.append(self.localize("All Goals: %s") % (", ".join(filegoals)))
      if "editgoal" in linksrequired and "admin" in self.rights:
        goaloptions = [('', '')] + [(goalname, goalname) for goalname in self.project.getgoalnames()]
        useroptions = [('', '')]
        for goalname in filegoals:
          useroptions += [(username, username) for username in self.project.getgoalusers(goalname)]
        if len(filegoals) > 1:
          goalselect = widgets.MultiSelect({"name": "editgoal", "value": filegoals}, goaloptions)
        else:
          goalselect = widgets.Select({"name": "editgoal", "value": ''.join(filegoals)}, goaloptions)
        goalfile = widgets.HiddenFieldList({"editgoalfile": basename})
        editfilegoal = widgets.Input({"type": "submit", "name": "doeditgoal", "value": self.localize("Set Goal")})
        userselect = widgets.Select({"name": "editfileuser", "value": ""}, useroptions)
        editfileuser = widgets.Input({"type": "submit", "name": "doedituser", "value": self.localize("Set User")})
        goalform = widgets.Form([goalfile, goalselect, editfilegoal, userselect, editfileuser], {"action": "", "name":"goalform-%s" % basename})
        actionlinks.append(goalform)
    if "review" in linksrequired and projectstats.get("has-suggestion", 0):
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
      if projectstats.get("translated", 0) < projectstats.get("total", 0):
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
    translated = projectstats.get("translated", 0)
    total = projectstats.get("total", 0)
    percentfinished = (translated*100/max(total, 1))
    if numfiles is None:
      statssummary = ""
    else:
      statssummary = self.localize("%d files, ") % numfiles
    statssummary += self.localize("%d/%d strings (%d%%) translated") % (translated, total, percentfinished)
    statsdetails = [statssummary]
    if not basename or basename.endswith("/"):
      linkbase = basename + "translate.html?"
    else:
      linkbase = basename + "?translate=1"
    if total and self.showchecks:
      statsdetails = statsdetails + self.getcheckdetails(projectstats, linkbase)
    if total and self.showtracks:
      trackfilter = (self.dirfilter or "") + basename
      trackpofilenames = self.project.browsefiles(trackfilter)
      projecttracks = self.project.gettracks(trackpofilenames)
      statsdetails += self.gettrackdetails(projecttracks, linkbase)
    if total and self.showassigns:
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
    total = max(projectstats.get("total", 0), 1)
    checklinks = []
    keys = projectstats.keys()
    keys.sort()
    for checkname in keys:
      if not checkname.startswith("check-"):
        continue
      checkcount = projectstats[checkname]
      checkname = checkname.replace("check-", "", 1)
      if total and checkcount:
        checklink = widgets.Link(self.makelink(linkbase, **{checkname:1}), checkname)
        stats = self.localize("%d strings (%d%%) failed") % (checkcount, (checkcount * 100 / total))
        checklinks += [[checklink, stats]]
    return checklinks

  def getassigndetails(self, projectstats, linkbase, removelinkbase):
    """return a list of strings describing the assigned strings"""
    total = max(projectstats.get("total", 0), 1)
    assignlinks = []
    keys = projectstats.keys()
    keys.sort()
    for assignname in keys: 
      if not assignname.startswith("assign-"):
        continue
      assigncount = projectstats[assignname]
      assignname = assignname.replace("assign-", "", 1)
      if total and assigncount:
        assignlink = widgets.Link(self.makelink(linkbase, assignedto=assignname), assignname)
        stats = self.localize("%d strings (%d%%) assigned") % (assigncount, (assigncount * 100 / total))
        if "assign" in self.rights:
          removetext = self.localize("Remove")
          removelink = widgets.Link(self.makelink(removelinkbase, assignedto=assignname), removetext)
        else:
          removelink = []
        assignlinks += [[assignlink, ": ", stats, " ", removelink]]
    return assignlinks

