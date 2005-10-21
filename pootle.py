#!/usr/bin/env python
# -*- coding: utf-8 -*-

from jToolkit.web import server
from jToolkit.web import session
from jToolkit import prefs
from jToolkit import localize
from jToolkit.widgets import widgets
from jToolkit.widgets import spellui
from jToolkit.web import simplewebserver
from Pootle import indexpage
from Pootle import adminpages
from Pootle import translatepage
from Pootle import pagelayout
from Pootle import projects
from Pootle import potree
from Pootle import users
from Pootle import filelocations
import sys
import os
import random

class PootleServer(users.OptionalLoginAppServer):
  """the Server that serves the Pootle Pages"""
  def __init__(self, instance, webserver, sessioncache=None, errorhandler=None, loginpageclass=users.LoginPage):
    if sessioncache is None:
      sessioncache = session.SessionCache(sessionclass=users.PootleSession)
    self.potree = potree.POTree(instance)
    super(PootleServer, self).__init__(instance, webserver, sessioncache, errorhandler, loginpageclass)
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
    self.languagenames = self.potree.getlanguages()
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
          if not arg.endswith(os.sep):
            arg += os.sep
          projectcode, languagecode = self.potree.getcodesfordir(arg)
          dummyproject = projects.DummyStatsProject(arg, stdchecker, projectcode, languagecode)
          def refreshdir(dummy, dirname, fnames):
            reldirname = dirname.replace(dummyproject.podir, "")
            for fname in fnames:
              fpath = os.path.join(reldirname, fname)
              if fname.endswith(".po") and not os.path.isdir(os.path.join(dummyproject.podir, fpath)):
                print "refreshing stats for", fpath
                projects.pootlefile.pootlefile(dummyproject, fpath).updatequickstats()
          os.path.walk(arg, refreshdir, None)
          if projectcode and languagecode:
            dummyproject.savequickstats()
        elif os.path.isfile(arg):
          dummyproject = projects.DummyStatsProject(".", stdchecker)
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
    if top == 'js':
      pathwords = pathwords[1:]
      jsfile = os.path.join(filelocations.htmldir, 'js', *pathwords)
      if not os.path.exists(jsfile):
        jsfile = os.path.join(filelocations.jtoolkitdir, 'js', *pathwords)
        if not os.path.exists(jsfile):
          return None
      jspage = widgets.PlainContents(None)
      jspage.content_type = "application/x-javascript"
      jspage.sendfile_path = jsfile
      return jspage
    elif not top or top == "index.html":
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
    elif top == "templates" or self.potree.haslanguage(top):
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
        elif bottom == "spellcheck.html":
          # the full review page
          argdict["spellchecklang"] = languagecode
          return spellui.SpellingReview(session, argdict, js_url="/js/spellui.js")
        elif bottom == "spellingstandby.html":
          # a simple 'loading' page
          return spellui.SpellingStandby()
        elif bottom.endswith("." + project.fileext):
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
            pofile = project.getpofile(pofilename, freshen=False)
            page = widgets.SendFile(pofile.filename)
            page.etag = str(pofile.pomtime)
            page.allowcaching = True
            encoding = pofile.encoding or "UTF-8"
            page.content_type = "text/plain; charset=%s" % encoding
            return page
        elif bottom.endswith(".csv") or bottom.endswith(".xlf") or bottom.endswith(".ts") or bottom.endswith("mo"):
          destfilename = os.path.join(*pathwords)
          basename, extension = os.path.splitext(destfilename)
          pofilename = basename + os.extsep + project.fileext
          extension = extension[1:]
          if extension == "mo":
            if not "pocompile" in project.getrights(session):
              return None
          etag, filepath_or_contents = project.convert(pofilename, extension)
          if etag:
            page = widgets.SendFile(filepath_or_contents)
            page.etag = str(etag)
          else:
            page = widgets.PlainContents(filepath_or_contents)
          page.allowcaching = True
          if extension == "csv":
            page.content_type = "text/plain; charset=UTF-8"
          elif extension == "xlf" or extension == "ts":
            page.content_type = "text/xml; charset=UTF-8"
          elif extension == "mo":
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

class PootleOptionParser(simplewebserver.WebOptionParser):
  def __init__(self):
    simplewebserver.WebOptionParser.__init__(self)
    self.set_default('prefsfile', filelocations.prefsfile)
    self.set_default('instance', 'Pootle')
    self.set_default('htmldir', filelocations.htmldir)
    self.add_option('', "--refreshstats", dest="action", action="store_const", const="refreshstats",
        default="runwebserver", help="refresh the stats files instead of running the webserver")

def main():
  # run the web server
  parser = PootleOptionParser()
  options, args = parser.parse_args()
  if options.action != "runwebserver":
    options.servertype = "dummy"
  server = parser.getserver(options)
  if options.action == "runwebserver":
    simplewebserver.run(server, options)
  elif options.action == "refreshstats":
    server.refreshstats(args)

if __name__ == '__main__':
  main()

