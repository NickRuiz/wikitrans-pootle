#!/usr/bin/env python

from jToolkit.web import server
from jToolkit.web import session
from jToolkit import prefs
from jToolkit import localize
from jToolkit.widgets import widgets
try:
  from jToolkit.web import templateserver
except ImportError:
  # give people a chance to upgrade jToolkit without this falling over
  class templateserver:
    class TemplateCacheServer(object):
      pass
from Pootle import indexpage
from Pootle import adminpages
from Pootle import translatepage
from Pootle import pagelayout
from Pootle import projects
from Pootle import potree
from Pootle import users
import sys
import os
import random

class PootleServer(users.OptionalLoginAppServer, templateserver.TemplateCacheServer):
  """the Server that serves the Pootle Pages"""
  def __init__(self, instance, webserver, sessioncache=None, errorhandler=None, loginpageclass=users.LoginPage):
    if sessioncache is None:
      sessioncache = session.SessionCache(sessionclass=users.PootleSession)
    self.potree = potree.POTree(instance)
    super(PootleServer, self).__init__(instance, webserver, sessioncache, errorhandler, loginpageclass)
    self.templatedir = os.path.join(os.path.dirname(__file__), "templates")
    self.setdefaultoptions()

  def saveprefs(self):
    """saves any changes made to the preferences"""
    # TODO: this is a hack, fix it up nicely :-)
    prefsfile = self.instance.__root__.__dict__["_setvalue"].im_self
    prefsfile.savefile()

  def setdefaultoptions(self):
    """sets the default options in the preferences"""
    changed = False
    if not hasattr(self.instance, "title"):
      setattr(self.instance, "title", "Pootle Demo")
      changed = True
    if not hasattr(self.instance, "description"):
      defaultdescription = "This is a demo installation of pootle. The administrator can customize the description in the preferences."
      setattr(self.instance, "description", defaultdescription)
      changed = True
    if not hasattr(self.instance, "baseurl"):
      setattr(self.instance, "baseurl", "/")
      changed = True
    if changed:
      self.saveprefs()

  def changeoptions(self, argdict):
    """changes options on the instance"""
    for key, value in argdict.iteritems():
      if not key.startswith("option-"):
        continue
      optionname = key.replace("option-", "", 1)
      setattr(self.instance, optionname, value)
    self.saveprefs()

  def inittranslation(self, localedir=None, localedomains=None, defaultlanguage=None):
    """initializes live translations using the Pootle PO files"""
    self.localedomains = ['jToolkit', 'pootle']
    self.localedir = None
    self.languagelist = self.potree.getlanguagecodes('pootle')
    self.languagenames = dict([(code, self.potree.getlanguagename(code)) for code in self.languagelist])
    self.defaultlanguage = defaultlanguage
    if self.defaultlanguage is None:
      self.defaultlanguage = getattr(self.instance, "defaultlanguage", "en")
    if self.potree.hasproject(self.defaultlanguage, 'pootle'):
      try:
        self.translation = self.potree.getproject(self.defaultlanguage, 'pootle')
        return
      except:
        self.errorhandler.logerror("Could not initialize translation")
    # if no translation available, set up a blank translation
    super(PootleServer, self).inittranslation()

  def gettranslation(self, language):
    """returns a translation object for the given language (or default if language is None)"""
    if language is None:
      return self.translation
    else:
      try:
        return self.potree.getproject(language, 'pootle')
      except:
        self.errorhandler.logerror("Could not get translation for language %r" % language)
        return self.translation

  def refreshstats(self, args):
    """refreshes all the available statistics..."""
    if args:
      def filtererrorhandler(functionname, str1, str2, e):
        print "error in filter %s: %r, %r, %s" % (functionname, str1, str2, e)
        return False
      checkerclasses = [projects.checks.StandardChecker, projects.pofilter.StandardPOChecker]
      stdchecker = projects.pofilter.POTeeChecker(checkerclasses=checkerclasses, errorhandler=filtererrorhandler)
      for arg in args:
        if not os.path.exists(arg):
          print "file not found:", arg
        if os.path.isdir(arg):
          def refreshdir(dummy, dirname, fnames):
            class dummyproject:
              checker = stdchecker
              podir = dirname
              def updatequickstats(*args): pass
            for fname in fnames:
              fpath = os.path.join(dirname, fname)
              if fname.endswith(".po") and not os.path.isdir(fpath):
                print "refreshing stats for", fpath
                projects.pootlefile.pootlefile(dummyproject, fname)
          os.path.walk(arg, refreshdir, None)
        elif os.path.isfile(arg):
          class dummyproject:
            checker = stdchecker
            podir = "."
            def updatequickstats(*args): pass
          print "refreshing stats for", arg
          projects.pootlefile.pootlefile(dummyproject, arg)
    else:
      print "refreshing stats for all files in all projects"
      self.potree.refreshstats()

  def generateactivationcode(self):
    """generates a unique activation code"""
    return "".join(["%02x" % int(random.random()*0x100) for i in range(16)])

  def getpage(self, pathwords, session, argdict):
    """return a page that will be sent to the user"""
    # TODO: strip off the initial path properly
    while pathwords and pathwords[0] == "pootle":
      pathwords = pathwords[1:]
    if pathwords:
      top = pathwords[0]
    else:
      top = ""
    if not top or top == "index.html":
      return indexpage.PootleIndex(self.potree, session)
    elif top == 'about.html':
      return indexpage.AboutPage(session)
    elif top == "login.html":
      if session.isopen:
        returnurl = argdict.get('returnurl', None) or getattr(self.instance, 'homepage', 'home/')
        return server.Redirect(returnurl)
      if 'username' in argdict:
        session.username = argdict["username"]
      return users.LoginPage(session, languagenames=self.languagenames)
    elif top == "register.html":
      return self.registerpage(session, argdict)
    elif top == "activate.html":
      return self.activatepage(session, argdict)
    elif top == "projects":
      pathwords = pathwords[1:]
      if pathwords:
        top = pathwords[0]
      else:
        top = ""
      if not top or top == "index.html":
        return indexpage.ProjectsIndex(self.potree, session)
      else:
        projectcode = top
        if not self.potree.hasproject(None, projectcode):
          return None
        pathwords = pathwords[1:]
        if pathwords:
          top = pathwords[0]
        else:
          top = ""
        if not top or top == "index.html":
          return indexpage.ProjectLanguageIndex(self.potree, projectcode, session)
        elif top == "admin.html":
          return adminpages.ProjectAdminPage(self.potree, projectcode, session, argdict)
    elif top == "languages":
      pathwords = pathwords[1:]
      if pathwords:
        top = pathwords[0]
      else:
        top = ""
      if not top or top == "index.html":
        return indexpage.LanguagesIndex(self.potree, session)
    elif top == "home":
      pathwords = pathwords[1:]
      if pathwords:
        top = pathwords[0]
      else:
        top = ""
      if not session.isopen:
        redirecttext = pagelayout.IntroText("Redirecting to login...")
        redirectpage = pagelayout.PootlePage("Redirecting to login...", redirecttext, session)
        return server.Redirect("../login.html", withpage=redirectpage)
      if not top or top == "index.html":
        return indexpage.UserIndex(self.potree, session)
      elif top == "options.html":
        if "changeoptions" in argdict:
          session.setoptions(argdict)
        if "changepersonal" in argdict:
          session.setpersonaloptions(argdict)
        if "changeinterface" in argdict:
          session.setinterfaceoptions(argdict)
        return users.UserOptions(self.potree, session)
    elif top == "admin":
      pathwords = pathwords[1:]
      if pathwords:
        top = pathwords[0]
      else:
        top = ""
      if not session.isopen:
        redirecttext = pagelayout.IntroText("Redirecting to login...")
        redirectpage = pagelayout.PootlePage("Redirecting to login...", redirecttext, session)
        return server.Redirect("../login.html", withpage=redirectpage)
      if not session.issiteadmin():
        redirecttext = pagelayout.IntroText(self.localize("You do not have the rights to administer pootle."))
        redirectpage = pagelayout.PootlePage("Redirecting to home...", redirecttext, session)
        return server.Redirect("../index.html", withpage=redirectpage)
      if not top or top == "index.html":
        if "changegeneral" in argdict:
          self.changeoptions(argdict)
        return adminpages.AdminPage(self.potree, session, self.instance)
      elif top == "users.html":
        if "changeusers" in argdict:
          self.changeusers(session, argdict)
        return adminpages.UsersAdminPage(self, session.loginchecker.users, session, self.instance)
      elif top == "languages.html":
        if "changelanguages" in argdict:
          self.potree.changelanguages(argdict)
        return adminpages.LanguagesAdminPage(self.potree, session, self.instance)
      elif top == "projects.html":
        if "changeprojects" in argdict:
          self.potree.changeprojects(argdict)
        return adminpages.ProjectsAdminPage(self.potree, session, self.instance)
    elif self.potree.haslanguage(top):
      languagecode = top
      pathwords = pathwords[1:]
      if pathwords:
        top = pathwords[0]
	bottom = pathwords[-1]
      else:
        top = ""
	bottom = ""
      if not top or top == "index.html":
        return indexpage.LanguageIndex(self.potree, languagecode, session)
      if self.potree.hasproject(languagecode, top):
        projectcode = top
        project = self.potree.getproject(languagecode, projectcode)
        pathwords = pathwords[1:]
        if pathwords:
          top = pathwords[0]
        else:
          top = ""
        if not top or top == "index.html":
	  return indexpage.ProjectIndex(project, session, argdict)
        elif top == "admin.html":
          return adminpages.TranslationProjectAdminPage(self.potree, project, session, argdict)
	elif bottom == "translate.html":
	  if len(pathwords) > 1:
            dirfilter = os.path.join(*pathwords[:-1])
	  else:
	    dirfilter = ""
          try:
            return translatepage.TranslatePage(project, session, argdict, dirfilter)
          except projects.RightsError, stoppedby:
            argdict["message"] = str(stoppedby)
            return indexpage.ProjectIndex(project, session, argdict, dirfilter)
	elif bottom.endswith(".po"):
	  pofilename = os.path.join(*pathwords)
	  if argdict.get("translate", 0):
            try:
              return translatepage.TranslatePage(project, session, argdict, dirfilter=pofilename)
            except projects.RightsError, stoppedby:
              argdict["message"] = str(stoppedby)
              return indexpage.ProjectIndex(project, session, argdict, dirfilter=pofilename)
	  elif argdict.get("index", 0):
            return indexpage.ProjectIndex(project, session, argdict, dirfilter=pofilename)
	  else:
            pofile = project.getpofile(pofilename)
	    contents = pofile.getsource()
	    page = widgets.PlainContents(contents)
            encoding = pofile.encoding or "UTF-8"
	    page.content_type = "text/plain; charset=%s" % encoding
	    return page
	elif bottom.endswith(".csv"):
	  csvfilename = os.path.join(*pathwords)
	  contents = project.getcsv(csvfilename)
	  page = widgets.PlainContents(contents)
	  page.content_type = "text/plain; charset=UTF-8"
	  return page
	elif bottom.endswith(".xlf"):
	  xlifffilename = os.path.join(*pathwords)
	  contents = project.getxliff(xlifffilename)
	  page = widgets.PlainContents(contents)
	  page.content_type = "text/xml; charset=UTF-8"
	  return page
	elif bottom.endswith(".mo"):
          if not "pocompile" in project.getrights(session):
            return None
	  mofilename = os.path.join(*pathwords)
	  contents = project.getmo(mofilename)
	  page = widgets.PlainContents(contents)
	  page.content_type = "application/octet-stream"
	  return page
        elif bottom.endswith(".zip"):
          if not "archive" in project.getrights(session):
            return None
	  if len(pathwords) > 1:
            dirfilter = os.path.join(*pathwords[:-1])
	  else:
	    dirfilter = None
          goal = argdict.get("goal", None)
          if goal:
            goalfiles = project.getgoalfiles(goal)
            pofilenames = []
            for goalfile in goalfiles:
              pofilenames.extend(project.browsefiles(goalfile))
          else:
            pofilenames = project.browsefiles(dirfilter)
          archivecontents = project.getarchive(pofilenames)
          page = widgets.PlainContents(archivecontents)
          page.content_type = "application/zip"
          return page
	elif bottom == "index.html":
          if len(pathwords) > 1:
            dirfilter = os.path.join(*pathwords[:-1])
          else:
            dirfilter = None
	  return indexpage.ProjectIndex(project, session, argdict, dirfilter)
	else:
	  return indexpage.ProjectIndex(project, session, argdict, os.path.join(*pathwords))
    return None

def main_is_frozen():
  import imp
  return (hasattr(sys, "frozen") or # new py2exe
          hasattr(sys, "importers") # old py2exe
          or imp.is_frozen("__main__")) # tools/freeze

def main():
  # run the web server
  from jToolkit.web import simplewebserver
  parser = simplewebserver.WebOptionParser()
  if main_is_frozen():
    pootledir = os.path.dirname(sys.executable)
  else:
    pootledir = os.path.abspath(os.path.dirname(__file__))
  prefsfile = os.path.join(pootledir, "pootle.prefs")
  parser.set_default('prefsfile', prefsfile)
  parser.set_default('instance', 'Pootle')
  htmldir = os.path.join(pootledir, "html")
  parser.set_default('htmldir', htmldir)
  parser.add_option('', "--refreshstats", dest="action", action="store_const", const="refreshstats", default="runwebserver", help="refresh the stats files instead of running the webserver")
  options, args = parser.parse_args()
  server = parser.getserver(options)
  if options.action == "runwebserver":
    simplewebserver.run(server, options)
  elif options.action == "refreshstats":
    server.refreshstats(args)

if __name__ == '__main__':
  main()

