#!/usr/bin/env python

from jToolkit.widgets import widgets
from jToolkit.widgets import table
from Pootle import pagelayout
from Pootle import projects

class AdminPage(pagelayout.PootlePage):
  """page for administering pootle..."""
  def __init__(self, potree, session, instance):
    self.potree = potree
    self.session = session
    self.instance = instance
    self.localize = session.localize
    if self.session.issiteadmin():
      homelink = pagelayout.IntroText(widgets.Link("../home/", self.localize("Home page")))
      userslink = pagelayout.IntroText(widgets.Link("users.html", self.localize("Users")))
      langlink = pagelayout.IntroText(widgets.Link("languages.html", self.localize("Languages")))
      projlink = pagelayout.IntroText(widgets.Link("projects.html", self.localize("Projects")))
      contents = [homelink, userslink, langlink, projlink, self.getgeneral()]
    else:
      contents = pagelayout.IntroText(self.localize("You do not have the rights to administer pootle."))
    pagelayout.PootlePage.__init__(self, self.localize("Pootle Admin Page"), contents, session)

  def getgeneral(self):
    """gets the general options"""
    generaltitle = pagelayout.Title(self.localize('General Options'))
    general = table.TableLayout()
    general.setcell(0, 0, table.TableCell(pagelayout.Title(self.localize("Option"))))
    general.setcell(0, 1, table.TableCell(pagelayout.Title(self.localize("Current value"))))
    options = {"title": self.localize("Title"), "description": self.localize("Description"), "baseurl": self.localize("Base URL")}
    for option, optionname in options.items():
      optionvalue = getattr(self.instance, option, "")
      valuetextbox = widgets.Input({"name": "option-%s" % option, "value": optionvalue})
      rownum = general.maxrownum()+1
      general.setcell(rownum, 0, table.TableCell(optionname))
      general.setcell(rownum, 1, table.TableCell(valuetextbox))
    rownum = general.maxrownum()+1
    submitbutton = widgets.Input({"type":"submit", "name":"changegeneral", "value":self.localize("Save changes")})
    generalform = widgets.Form([general, submitbutton], {"name": "general", "action":""})
    return pagelayout.Contents([generaltitle, generalform])

class LanguagesAdminPage(pagelayout.PootlePage):
  """page for administering pootle..."""
  def __init__(self, potree, session, instance):
    self.potree = potree
    self.session = session
    self.instance = instance
    self.localize = session.localize
    if self.session.issiteadmin():
      homelink = pagelayout.IntroText(widgets.Link("../home/", self.localize("Home page")))
      indexlink = pagelayout.IntroText(widgets.Link("index.html", self.localize("Main Admin page")))
      contents = [homelink, indexlink, self.getlanguages()]
    else:
      contents = pagelayout.IntroText(self.localize("You do not have the rights to administer pootle."))
    pagelayout.PootlePage.__init__(self, self.localize("Pootle Languages Admin Page"), contents, session)

  def getlanguages(self):
    """gets the links to the languages"""
    languagestitle = pagelayout.Title(self.localize('Languages'))
    languages = table.TableLayout()
    languages.setcell(0, 0, table.TableCell(pagelayout.Title(self.localize("ISO Code"))))
    languages.setcell(0, 1, table.TableCell(pagelayout.Title(self.localize("Full Name"))))
    languages.setcell(0, 2, table.TableCell(pagelayout.Title(self.localize("Special Chars"))))
    languages.setcell(0, 3, table.TableCell(pagelayout.Title(self.localize("Number of Plurals"))))
    languages.setcell(0, 4, table.TableCell(pagelayout.Title(self.localize("Plural Equation"))))
    languages.setcell(0, 5, table.TableCell(pagelayout.Title(self.localize("Remove language"))))
    for languagecode in self.potree.getlanguagecodes():
      languagename = self.potree.getlanguagename(languagecode)
      languagespecialchars = self.potree.getlanguagespecialchars(languagecode)
      languagenplurals = self.potree.getlanguagenplurals(languagecode)
      languagepluralequation = self.potree.getlanguagepluralequation(languagecode)
      nametextbox = widgets.Input({"name": "languagename-%s" % languagecode, "value": languagename})
      specialcharstextbox = widgets.Input({"name": "languagespecialchars-%s" % languagecode, "value": languagespecialchars})
      npluralstextbox = widgets.Input({"name": "languagenplurals-%s" % languagecode, "value": languagenplurals})
      pluralequationtextbox = widgets.Input({"name": "languagepluralequation-%s" % languagecode, "value": languagepluralequation})
      removecheckbox = widgets.Input({"name": "languageremove-%s" % languagecode, "type": "checkbox"})
      rownum = languages.maxrownum()+1
      languages.setcell(rownum, 0, table.TableCell(languagecode))
      languages.setcell(rownum, 1, table.TableCell(nametextbox))
      languages.setcell(rownum, 2, table.TableCell(specialcharstextbox))
      languages.setcell(rownum, 3, table.TableCell(npluralstextbox))
      languages.setcell(rownum, 4, table.TableCell(pluralequationtextbox))
      languages.setcell(rownum, 5, table.TableCell([removecheckbox, self.localize("Remove %s") % languagecode]))
    rownum = languages.maxrownum()+1
    codetextbox = widgets.Input({"name": "newlanguagecode", "value": "", "size": 6})
    nametextbox = widgets.Input({"name": "newlanguagename", "value": self.localize("(add language here)")})
    specialcharstextbox = widgets.Input({"name": "newlanguagespecialchars", "value": self.localize("(special characters)")})
    npluralstextbox = widgets.Input({"name": "newlanguagenplurals", "value": self.localize("(number of plurals)")})
    pluralequationtextbox = widgets.Input({"name": "newlanguagepluralequation", "value": self.localize("(plural equation)")})
    languages.setcell(rownum, 0, table.TableCell(codetextbox))
    languages.setcell(rownum, 1, table.TableCell(nametextbox))
    languages.setcell(rownum, 2, table.TableCell(specialcharstextbox))
    languages.setcell(rownum, 3, table.TableCell(npluralstextbox))
    languages.setcell(rownum, 4, table.TableCell(pluralequationtextbox))
    submitbutton = widgets.Input({"type":"submit", "name":"changelanguages", "value":self.localize("Save changes")})
    languageform = widgets.Form([languages, submitbutton], {"name": "languages", "action":""})
    return pagelayout.Contents([languagestitle, languageform])

class ProjectsAdminPage(pagelayout.PootlePage):
  """page for administering pootle..."""
  def __init__(self, potree, session, instance):
    self.potree = potree
    self.session = session
    self.instance = instance
    self.localize = session.localize
    if self.session.issiteadmin():
      homelink = pagelayout.IntroText(widgets.Link("../home/", self.localize("Home page")))
      indexlink = pagelayout.IntroText(widgets.Link("index.html", self.localize("Main Admin page")))
      contents = [homelink, indexlink, self.getprojects()]
    else:
      contents = pagelayout.IntroText(self.localize("You do not have the rights to administer pootle."))
    pagelayout.PootlePage.__init__(self, self.localize("Pootle Projects Admin Page"), contents, session)

  def getprojects(self):
    """gets the links to the projects"""
    projectstitle = pagelayout.Title(self.localize("Projects"))
    projects = table.TableLayout()
    projects.setcell(0, 0, table.TableCell(pagelayout.Title(self.localize("Project Code"))))
    projects.setcell(0, 1, table.TableCell(pagelayout.Title(self.localize("Full Name"))))
    projects.setcell(0, 2, table.TableCell(pagelayout.Title(self.localize("Project Description"))))
    projects.setcell(0, 3, table.TableCell(pagelayout.Title(self.localize("Checker Style"))))
    projects.setcell(0, 4, table.TableCell(pagelayout.Title(self.localize("Create MO Files"))))
    projects.setcell(0, 5, table.TableCell(pagelayout.Title(self.localize("Remove project"))))
    for projectcode in self.potree.getprojectcodes():
      projectadminlink = "../projects/%s/admin.html" % projectcode
      projectname = self.potree.getprojectname(projectcode)
      projectdescription = self.potree.getprojectdescription(projectcode)
      projectname = self.potree.getprojectname(projectcode)
      projectcheckerstyle = self.potree.getprojectcheckerstyle(projectcode)
      if self.potree.getprojectcreatemofiles(projectcode):
        projectcreatemofiles = "checked"
      else:
        projectcreatemofiles = ""
      nametextbox = widgets.Input({"name": "projectname-%s" % projectcode, "value": projectname})
      descriptiontextbox = widgets.Input({"name": "projectdescription-%s" % projectcode, "value": projectdescription})
      checkerstyletextbox = widgets.Input({"name": "projectcheckerstyle-%s" % projectcode, "value": projectcheckerstyle})
      createmofilescheckbox = widgets.Input({"name": "projectcreatemofiles-%s" % projectcode, "value": projectcreatemofiles, "type": "checkbox", projectcreatemofiles:''})
      removecheckbox = widgets.Input({"name": "projectremove-%s" % projectcode, "type": "checkbox"})
      rownum = projects.maxrownum()+1
      projects.setcell(rownum, 0, table.TableCell(widgets.Link(projectadminlink, projectcode)))
      projects.setcell(rownum, 1, table.TableCell(nametextbox))
      projects.setcell(rownum, 2, table.TableCell(descriptiontextbox))
      projects.setcell(rownum, 3, table.TableCell(checkerstyletextbox))
      projects.setcell(rownum, 4, table.TableCell(createmofilescheckbox))
      projects.setcell(rownum, 5, table.TableCell([removecheckbox, self.localize("Remove %s") % projectcode]))
    rownum = projects.maxrownum()+1
    codetextbox = widgets.Input({"name": "newprojectcode", "value": "", "size": 6})
    nametextbox = widgets.Input({"name": "newprojectname", "value": self.localize("(add project here)")})
    descriptiontextbox = widgets.Input({"name": "newprojectdescription", "value": self.localize("(project description)")})
    checkerstyletextbox = widgets.Input({"name": "newprojectcheckerstyle", "value": self.localize("(checker style)")})
    createmofilescheckbox = widgets.Input({"name": "newprojectcreatemofiles", "type": "checkbox"})
    projects.setcell(rownum, 0, table.TableCell(codetextbox))
    projects.setcell(rownum, 1, table.TableCell(nametextbox))
    projects.setcell(rownum, 2, table.TableCell(descriptiontextbox))
    projects.setcell(rownum, 3, table.TableCell(checkerstyletextbox))
    projects.setcell(rownum, 4, table.TableCell(createmofilescheckbox))
    submitbutton = widgets.Input({"type":"submit", "name":"changeprojects", "value":self.localize("Save changes")})
    projectform = widgets.Form([projects, submitbutton], {"name": "projects", "action":""})
    return pagelayout.Contents([projectstitle, projectform])

class UsersAdminPage(pagelayout.PootlePage):
  """page for administering pootle..."""
  def __init__(self, server, users, session, instance):
    self.server = server
    self.users = users
    self.session = session
    self.instance = instance
    self.localize = session.localize
    if self.session.issiteadmin():
      homelink = pagelayout.IntroText(widgets.Link("../home/", self.localize("Home page")))
      adminlink = pagelayout.IntroText(widgets.Link("index.html", self.localize("Admin page")))
      contents = [homelink, adminlink, self.getusers()]
    else:
      contents = pagelayout.IntroText(self.localize("You do not have the rights to administer Pootle."))
    pagelayout.PootlePage.__init__(self, self.localize("Pootle User Admin Page"), contents, session)

  def getusers(self):
    """user list and adding"""
    userstitle = pagelayout.Title(self.localize("Users"))
    users = table.TableLayout()
    users.setcell(0, 0, table.TableCell(pagelayout.Title(self.localize("Login"))))
    users.setcell(0, 1, table.TableCell(pagelayout.Title(self.localize("Full Name"))))
    users.setcell(0, 2, table.TableCell(pagelayout.Title(self.localize("Email Address"))))
    users.setcell(0, 3, table.TableCell(pagelayout.Title(self.localize("Password"))))
    users.setcell(0, 4, table.TableCell(pagelayout.Title(self.localize("Activated"))))
    # users.setcell(0, 3, table.TableCell(pagelayout.Title(self.localize("Projects"))))
    # users.setcell(0, 4, table.TableCell(pagelayout.Title(self.localize("Languages"))))
    for username, usernode in self.users.iteritems():
      if username == "__dummy__":
        continue
      fullnametextbox = widgets.Input({"name": "userfullname-%s" % username, "value": getattr(usernode, "name", "")})
      emailtextbox = widgets.Input({"name": "useremail-%s" % username, "value": getattr(usernode, "email", "")})
      activatedvalues = {"name": "useractivated-%s" % username, "type": "checkbox"}
      if getattr(usernode, "activated", 0) == 1:
        activatedvalues["checked"] = "true"
      activatedcheckbox = widgets.Input(activatedvalues)
      removecheckbox = widgets.Input({"name": "userremove-%s" % username, "type": "checkbox"})
      rownum = users.maxrownum()+1
      users.setcell(rownum, 0, table.TableCell(username))
      users.setcell(rownum, 1, table.TableCell(fullnametextbox))
      users.setcell(rownum, 2, table.TableCell(emailtextbox))
      users.setcell(rownum, 4, table.TableCell(activatedcheckbox))
      # users.setcell(rownum, 2, table.TableCell(descriptiontextbox))
      # users.setcell(rownum, 3, table.TableCell(checkerstyletextbox))
      users.setcell(rownum, 5, table.TableCell([removecheckbox, self.localize("Remove %s") % username]))
    rownum = users.maxrownum()+1
    codetextbox = widgets.Input({"name": "newusername", "value": "", "size": 6})
    newfullnametextbox = widgets.Input({"name": "newfullname", "value": self.localize("(add full name here)")})
    newemailtextbox = widgets.Input({"name": "newuseremail", "value": self.localize("(add email here)")})
    passwordtextbox = widgets.Input({"name": "newuserpassword", "value": self.localize("(add password here)")})
    # sendemailcheckbox = widgets.Input({"name": "newusersendemail", "type": "checkbox", "checked": "true"})
    activatecheckbox = widgets.Input({"name": "newuseractivate", "type": "checkbox", "checked": "true"})
    users.setcell(rownum, 0, table.TableCell(codetextbox))
    users.setcell(rownum, 1, table.TableCell(newfullnametextbox))
    users.setcell(rownum, 2, table.TableCell(newemailtextbox))
    users.setcell(rownum, 3, table.TableCell(passwordtextbox))
    # users.setcell(rownum, 3, table.TableCell([sendemailcheckbox, self.localize("Email New User")]))
    users.setcell(rownum, 4, table.TableCell([activatecheckbox, self.localize("Activate New User")]))
    submitbutton = widgets.Input({"type":"submit", "name":"changeusers", "value":self.localize("Save changes")})
    userform = widgets.Form([users, submitbutton], {"name": "users", "action":""})
    return pagelayout.Contents([userstitle, userform])

class ProjectAdminPage(pagelayout.PootlePage):
  """list of languages belonging to a project"""
  def __init__(self, potree, projectcode, session, argdict):
    self.potree = potree
    self.projectcode = projectcode
    self.session = session
    self.localize = session.localize
    projectname = self.potree.getprojectname(self.projectcode)
    if self.session.issiteadmin():
      if "doaddlanguage" in argdict:
        newlanguage = argdict.get("newlanguage", None)
        if not newlanguage:
          raise ValueError("You must select a new language")
        self.potree.addtranslationproject(newlanguage, self.projectcode)
      if "doupdatelanguage" in argdict:
        languagecode = argdict.get("updatelanguage", None)
        if not languagecode:
          raise ValueError("No languagecode given in doupdatelanguage")
        translationproject = self.potree.getproject(languagecode, self.projectcode)
        translationproject.converttemplates(self.session)
      languagestitle = pagelayout.Title(self.localize("Existing languages"))
      languagelinks = self.getlanguagelinks()
      existing = pagelayout.ContentsItem([languagestitle, languagelinks])
      newlangform = self.getnewlangform()
      contents = [existing, newlangform]
    else:
      contents = pagelayout.IntroText(self.localize("You do not have the rights to administer this project."))
    pagelayout.PootlePage.__init__(self, "Pootle Admin: "+projectname, contents, session, bannerheight=81)

  def getlanguagelinks(self):
    """gets the links to the languages"""
    languagecodes = self.potree.getlanguagecodes(self.projectcode)
    languageitems = [self.getlanguageitem(languagecode) for languagecode in languagecodes]
    return pagelayout.Item(languageitems)

  def getlanguageitem(self, languagecode):
    languagename = self.potree.getlanguagename(languagecode)
    adminlink = widgets.Link("../../%s/%s/admin.html" % (languagecode, self.projectcode), languagename)
    updatelink = widgets.Link("?doupdatelanguage=1&updatelanguage=%s" % languagecode, self.localize("Update from templates"))
    return pagelayout.ItemDescription([adminlink, updatelink])

  def getnewlangform(self):
    """returns a box that lets the user add new languages"""
    existingcodes = self.potree.getlanguagecodes(self.projectcode)
    allcodes = self.potree.getlanguagecodes()
    newcodes = [code for code in allcodes if not code in existingcodes]
    newcodes.sort()
    newoptions = [(code, self.potree.getlanguagename(code)) for code in newcodes]
    languageselect = widgets.Select({'name':'newlanguage'}, options=newoptions)
    submitbutton = widgets.Input({"type": "submit", "name": "doaddlanguage", "value": self.localize("Add Language")})
    newlangform = widgets.Form([languageselect, submitbutton], {"action": "", "name":"newlangform"})
    return newlangform

class TranslationProjectAdminPage(pagelayout.PootlePage):
  """admin page for a translation project (project+language)"""
  def __init__(self, potree, project, session, argdict):
    self.potree = potree
    self.project = project
    self.session = session
    self.localize = session.localize
    self.rightnames = self.project.getrightnames(session)
    title = self.localize("Pootle Admin: %s %s") % (self.project.languagename, self.project.projectname)
    mainlink = widgets.Link("index.html", self.localize("Project home page"))
    links = [pagelayout.Title(title), pagelayout.IntroText(mainlink)]
    if "admin" in self.project.getrights(self.session):
      if "doupdaterights" in argdict:
        for key, value in argdict.iteritems():
          if key.startswith("rights-"):
            username = key.replace("rights-", "", 1)
            self.project.setrights(username, value)
        username = argdict.get("rightsnew-username", None)
        if username:
          username = username.strip()
          if self.session.loginchecker.userexists(username):
            self.project.setrights(username, argdict.get("rightsnew", ""))
          else:
            raise IndexError(self.localize("Cannot set rights for username %s - user does not exist") % username)
      contents = [self.getoptions()]
    else:
      contents = pagelayout.IntroText(self.localize("You do not have the rights to administer this project."))
    pagelayout.PootlePage.__init__(self, title, [links, contents], session, bannerheight=81)

  def getoptions(self):
    """returns a box that describes the options"""
    if self.project.filestyle == "gnu":
      filestyle = pagelayout.IntroText(self.localize("This is a GNU-style project (one directory, files named per language)."))
    else:
      filestyle = pagelayout.IntroText(self.localize("This is a standard style project (one directory per language)."))
    rightstitle = pagelayout.Title(self.localize("User Permissions"))
    rightstable = table.TableLayout()
    rightstable.setcell(0, 0, table.TableCell(pagelayout.Title(self.localize("Username"))))
    rightstable.setcell(0, 1, table.TableCell(pagelayout.Title(self.localize("Rights"))))
    self.addrightsrow(rightstable, 1, "nobody", self.project.getrights(username=None))
    defaultrights = self.project.getrights(username="default")
    self.addrightsrow(rightstable, 2, "default", defaultrights)
    rownum = 3
    for username, rights in getattr(self.project.prefs, "rights", {}).iteritems():
      if username in ("nobody", "default"): continue
      self.addrightsrow(rightstable, rownum, username, rights)
      rownum += 1
    rightstable.setcell(rownum, 0, table.TableCell(widgets.Input({"name": "rightsnew-username"})))
    selectrights = widgets.MultiSelect({"name": "rightsnew", "value": defaultrights}, self.rightnames)
    rightstable.setcell(rownum, 1, table.TableCell(selectrights))
    submitbutton = widgets.Input({"type": "submit", "name": "doupdaterights", "value": self.localize("Update Rights")})
    rightsform = widgets.Form([rightstitle, rightstable, submitbutton], {"action": "", "name":"rightsform"})
    return [filestyle, rightsform]

  def addrightsrow(self, rightstable, rownum, username, rights):
    """adds a row for the given user's rights"""
    if not isinstance(rights, list):
      rights = [right.strip() for right in rights.split(",")]
    rightstable.setcell(rownum, 0, table.TableCell(username))
    selectrights = widgets.MultiSelect({"name": "rights-%s" % username, "value": rights}, self.rightnames)
    rightstable.setcell(rownum, 1, table.TableCell(selectrights))

