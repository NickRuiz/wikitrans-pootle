#!/usr/bin/env python
# -*- coding: utf-8 -*-

def layout_banner(maxheight):
  """calculates dimensions, image name for banner"""
  banner_width, banner_height = min((98*maxheight/130, maxheight), (98, 130))
  logo_width, logo_height = min((290*maxheight/160, maxheight), (290, 160))
  if banner_width <= 61:
    banner_image = "pootle-medium.png"
  else:
    banner_image = "pootle.png"
  return {"banner_width": banner_width, "banner_height": banner_height,
    "logo_width": logo_width, "logo_height": logo_height, "banner_image": banner_image}

def completetemplatevars(templatevars, session, bannerheight=135):
  """fill out default values for template variables"""
  if not "instancetitle" in templatevars:
    templatevars["instancetitle"] = getattr(session.instance, "title", session.localize("Pootle Demo"))
  if not "session" in templatevars:
    templatevars["session"] = {"status": session.status, "isopen": session.isopen, "issiteadmin": session.issiteadmin()}
  banner_layout = layout_banner(bannerheight)
  banner_layout["banner_alttext"] = session.localize("WordForge Translation Project")
  banner_layout["logo_alttext"] = session.localize("Pootle Logo")
  templatevars.update(banner_layout)
  if "search" not in templatevars:
    templatevars["search"] = None

class PootlePage:
  """the main page"""
  def __init__(self, templatename, templatevars, session, bannerheight=135):
    if not hasattr(session.instance, "baseurl"):
      session.instance.baseurl = "/"
    self.localize = session.localize
    self.session = session
    self.templatename = templatename
    self.templatevars = templatevars
    self.completevars(bannerheight)

  def completevars(self, bannerheight=135):
    """fill out default values for template variables"""
    if hasattr(self, "templatevars"):
      completetemplatevars(self.templatevars, self.session, bannerheight=bannerheight)

  def polarizeitems(self, itemlist):
    """take an item list and alternate the background colour"""
    polarity = False
    for n, item in enumerate(itemlist):
      if isinstance(item, dict):
        item["parity"] = ["even", "odd"][n % 2]
      else:
        item.setpolarity(polarity)
      polarity = not polarity
    return itemlist

class PootleNavPage(PootlePage):
  def makenavbarpath_dict(self, project=None, session=None, currentfolder=None, language=None, goal=None):
    """create the navbar location line"""
    rootlink = ""
    links = {"admin": None, "project": [], "language": [], "goal": [], "pathlinks": []}
    if currentfolder:
      pathlinks = []
      dirs = currentfolder.split("/")
      depth = len(dirs)
      if currentfolder.endswith(".po"):
        depth = depth - 1
      rootlink = "/".join([".."] * depth)
      if rootlink:
        rootlink += "/"
      for backlinkdir in dirs:
        if backlinkdir.endswith(".po"):
          backlinks = "../" * depth + backlinkdir
        else:
          backlinks = "../" * depth + backlinkdir + "/"
        depth = depth - 1
        pathlinks.append({"href": self.getbrowseurl(backlinks), "text": backlinkdir, "sep": " / "})
      if pathlinks:
        pathlinks[-1]["sep"] = ""
      links["pathlinks"] = pathlinks
    if goal is not None:
      # goallink = {"href": self.getbrowseurl("", goal=goal), "text": goal}
      links["goal"] = {"href": self.getbrowseurl(""), "text": self.localize("All goals")}
    if project:
      if isinstance(project, tuple):
        projectcode, projectname = project
        links["project"] = {"href": "/projects/%s/" % projectcode, "text": projectname}
      else:
        links["language"] = {"href": rootlink + "../index.html", "text": project.languagename}
        # don't getbrowseurl on the project link, so sticky options won't apply here
        links["project"] = {"href": rootlink or "index.html", "text": project.projectname}
        if session:
          if "admin" in project.getrights(session) or session.issiteadmin():
            links["admin"] = {"href": rootlink + "admin.html", "text": self.localize("Admin")}
    elif language:
      languagecode, languagename = language
      links["language"] = {"href": "/%s/" % languagecode, "text": languagename}
    return links

  def getbrowseurl(self, basename, **newargs):
    """gets the link to browse the item"""
    if not basename or basename.endswith("/"):
      return self.makelink(basename or "index.html", **newargs)
    else:
      return self.makelink(basename, translate=1, view=1, **newargs)

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
    link += "&".join(["%s=%s" % (arg, value) for arg, value in combinedargs.iteritems() if arg != "allowmultikey"])
    return link

  def initpagestats(self):
    """initialise the top level (language/project) stats"""
    self.alltranslated = 0
    self.grandtotal = 0
    
  def getpagestats(self):
    """return the top level stats"""
    return (self.alltranslated*100/max(self.grandtotal, 1))

  def updatepagestats(self, translated, total):
    """updates the top level stats"""
    self.alltranslated += translated
    self.grandtotal += total

  def describestats(self, project, projectstats, numfiles):
    """returns a sentence summarizing item statistics"""
    translated = projectstats.get("translated", [])
    total = projectstats.get("total", [])
    if "translatedwords" in projectstats:
      translatedwords = projectstats["translatedwords"]
    else:
      translatedwords = project.countwords(translated)
    if "totalwords" in projectstats:
      totalwords = projectstats["totalwords"]
    else:
      totalwords = project.countwords(total)
    if isinstance(translated, list):
      translated = len(translated)
    if isinstance(total, list):
      total = len(total)
    percentfinished = (translatedwords*100/max(totalwords, 1))
    if numfiles is None:
      filestats = ""
    elif isinstance(numfiles, tuple):
      filestats = self.localize("%d/%d files", numfiles) + ", "
    else:
      filestats = self.nlocalize("%d file", "%d files", numfiles, numfiles) + ", "
    wordstats = self.localize("%d/%d words (%d%%) translated", translatedwords, totalwords, percentfinished)
    stringstats = ' <span cls="string-statistics">[%d/%d strings]</span>' % (translated, total)
    return filestats + wordstats + stringstats

  def getstatsheadings(self):
    """returns a dictionary of localised headings"""
    headings = {"name": self.localize("Name"),
                "translated": self.localize("Translated"),
                "translatedpercentage": self.localize("Translated percentage"),
                "translatedwords": self.localize("Translated words"),
                "fuzzy": self.localize("Fuzzy"),
                "fuzzypercentage": self.localize("Fuzzy percentage"),
                "fuzzywords": self.localize("Fuzzy words"),
                "untranslated": self.localize("Untranslated"),
                "untranslatedpercentage": self.localize("Untranslated percentage"),
                "untranslatedwords": self.localize("Untranslated words"),
                "total": self.localize("Total"),
                "totalwords": self.localize("Total words"),
                "graph": self.localize("Graph")}
    return headings

  def getstats(self, project, projectstats, numfiles):
    """returns a list with the data items to fill a statistics table
    Remember to update getstatsheadings() above as needed"""
    wanted = ["translated", "fuzzy", "check-untranslated", "total"]
    gotten = {}
    for key in wanted:
      gotten[key] = projectstats.get(key, [])
      wordkey = key + "words"
      if wordkey in projectstats:
        gotten[wordkey] = projectstats[wordkey]
      else:
        count = projectstats.get(key, [])
        gotten[wordkey] = project.countwords(count)
      if isinstance(gotten[key], list):
        #TODO: consider carefully:
        gotten[key] = len(gotten[key])

    for key in wanted[:-1]:
      percentkey = key + "percentage"
      wordkey = key + "words"
      gotten[percentkey] = gotten[wordkey]*100/max(gotten["totalwords"], 1)

    for key in gotten:
      if key.find("check-") == 0:
        value = gotten.pop(key)
        gotten[key[len("check-"):]] = value
    return gotten

