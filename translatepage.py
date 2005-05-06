#!/usr/bin/env python

from jToolkit.widgets import widgets
from jToolkit.widgets import table
from Pootle import pagelayout
from Pootle import projects
from Pootle import pootlefile
import difflib

def oddoreven(polarity):
  if polarity % 2 == 0:
    return "even"
  elif polarity % 2== 1:
    return "odd"

class TranslatePage(pagelayout.PootlePage):
  """the page which lets people edit translations"""
  def __init__(self, project, session, argdict, dirfilter=None):
    self.argdict = argdict
    self.dirfilter = dirfilter
    self.project = project
    self.matchnames = self.getmatchnames(self.project.checker)
    self.searchtext = self.argdict.get("searchtext", "")
    # TODO: fix this in jToolkit
    if isinstance(self.searchtext, str):
      self.searchtext = self.searchtext.decode("utf8")
    self.showassigns = self.argdict.get("showassigns", 0)
    if isinstance(self.showassigns, (str, unicode)) and self.showassigns.isdigit():
      self.showassigns = int(self.showassigns)
    self.session = session
    self.localize = session.localize
    self.rights = self.project.getrights(self.session)
    self.instance = session.instance
    if dirfilter and dirfilter.endswith(".po"):
      self.pofilename = dirfilter
    else:
      self.pofilename = None
    self.lastitem = None
    self.receivetranslations()
    # TODO: clean up modes to be one variable
    self.viewmode = self.argdict.get("view", 0) and "view" in self.rights
    self.reviewmode = self.argdict.get("review", 0)
    notice = ""
    try:
      self.finditem()
    except StopIteration, stoppedby:
      notice = self.getfinishedtext(stoppedby)
      self.item = None
    self.maketable()
    searchcontextinfo = widgets.HiddenFieldList({"searchtext": self.searchtext})
    contextinfo = widgets.HiddenFieldList({"pofilename": self.pofilename})
    translateform = widgets.Form([self.transtable, searchcontextinfo, contextinfo], {"name": "translate", "action":""})
    title = self.localize("Pootle: translating %s into %s: %s") % (self.project.projectname, self.project.languagename, self.pofilename)
    if self.viewmode:
      pagelinks = self.getpagelinks("?translate=1&view=1", 10)
    else:
      pagelinks = []
    translatediv = pagelayout.TranslateForm([notice, pagelinks, translateform, pagelinks])
    pagelayout.PootlePage.__init__(self, title, translatediv, session, bannerheight=81, returnurl="%s/%s/%s" % (self.project.languagecode, self.project.projectcode, dirfilter))
    self.addfilelinks(self.pofilename, self.matchnames)
    if dirfilter and dirfilter.endswith(".po"):
      currentfolder = "/".join(dirfilter.split("/")[:-1])
    else:
      currentfolder = dirfilter
    self.addfolderlinks(self.localize("current folder"), currentfolder, "index.html")
    autoexpandscript = widgets.Script('text/javascript', '', newattribs={'src': self.instance.baseurl + 'js/autoexpand.js'})
    self.headerwidgets.append(autoexpandscript)

  def getfinishedtext(self, stoppedby):
    """gets notice to display when the translation is finished"""
    title = pagelayout.Title(self.localize("End of batch"))
    finishedlink = "index.html?" + "&".join(["%s=%s" % (arg, value) for arg, value in self.argdict.iteritems() if arg.startswith("show")])
    returnlink = widgets.Link(finishedlink, self.localize("Click here to return to the index"))
    stoppedbytext = stoppedby.args[0]
    return [title, pagelayout.IntroText(stoppedbytext), returnlink]

  def getpagelinks(self, baselink, pagesize):
    """gets links to other pages of items, based on the given baselink"""
    pagelinks = []
    pofilelen = self.project.getpofilelen(self.pofilename)
    if pofilelen <= pagesize:
      return pagelinks
    lastitem = min(pofilelen-1, self.firstitem + pagesize - 1)
    if pofilelen > pagesize and not self.firstitem == 0:
      pagelinks.append(widgets.Link(baselink + "&item=0", self.localize("Start")))
    else:
      pagelinks.append(self.localize("Start")) 
    if self.firstitem > 0:
      linkitem = max(self.firstitem - pagesize, 0)
      pagelinks.append(widgets.Link(baselink + "&item=%d" % linkitem, self.localize("Previous %d") % (self.firstitem - linkitem)))
    else:
      pagelinks.append(self.localize("Previous %d") % pagesize)
    pagelinks.append(self.localize("Items %d to %d of %d") % (self.firstitem+1, lastitem+1, pofilelen))
    if self.firstitem + len(self.translations) < self.project.getpofilelen(self.pofilename):
      linkitem = self.firstitem + pagesize
      itemcount = min(pofilelen - linkitem, pagesize)
      pagelinks.append(widgets.Link(baselink + "&item=%d" % linkitem, self.localize("Next %d") % itemcount))
    else:
      pagelinks.append(self.localize("Next %d") % pagesize)
    if pofilelen > pagesize and (self.item + pagesize) < pofilelen:
      pagelinks.append(widgets.Link(baselink + "&item=%d" % max(pofilelen - pagesize, 0), self.localize("End")))
    else:
      pagelinks.append(self.localize("End"))
    return pagelayout.ItemStatistics(widgets.SeparatedList(pagelinks, " | "))

  def addfilelinks(self, pofilename, matchnames):
    """adds a section on the current file, including any checks happening"""
    searchcontextinfo = widgets.HiddenFieldList({"pofilename": self.pofilename})
    self.addsearchbox(self.searchtext, searchcontextinfo)
    if self.showassigns and "assign" in self.rights:
      self.addassignbox()
    if self.pofilename is not None:
      self.links.addcontents(pagelayout.SidebarTitle(self.localize("current file")))
      self.links.addcontents(pagelayout.SidebarText(pofilename))
      if matchnames:
        checknames = [matchname.replace("check-", "", 1) for matchname in matchnames]
        self.links.addcontents(pagelayout.SidebarText(self.localize("checking %s") % ", ".join(checknames)))
      postats = self.project.getpostats(self.pofilename)
      blank, fuzzy = postats["blank"], postats["fuzzy"]
      translated, total = postats["translated"], postats["total"]
      self.links.addcontents(pagelayout.SidebarText(self.localize("%d/%d translated\n(%d blank, %d fuzzy)") % (translated, total, blank, fuzzy)))

  def addassignbox(self):
    """adds a box that lets the user assign strings"""
    self.links.addcontents(pagelayout.SidebarTitle(self.localize("Assign Strings")))
    assigntobox = widgets.Input({"name": "assignto", "value": "", "title": self.localize("Assign to User")})
    actionbox = widgets.Input({"name": "action", "value": "translate", "title": self.localize("Assign Action")})
    submitbutton = widgets.Input({"type": "submit", "name": "doassign", "value": self.localize("Assign Strings")})
    assignform = widgets.Form([assigntobox, actionbox, submitbutton], {"action": "?index=1", "name":"assignform"})
    self.links.addcontents(assignform)

  def receivetranslations(self):
    """receive any translations submitted by the user"""
    pofilename = self.argdict.get("pofilename", None)
    if pofilename is None:
      return
    skips = []
    submitsuggests = []
    submits = []
    accepts = []
    rejects = []
    translations = {}
    suggestions = {}
    def getitem(key, prefix):
      if not key.startswith(prefix):
        return None
      try:
        return int(key.replace(prefix, "", 1))
      except:
        return None
    def getpointitem(key, prefix):
      if not key.startswith(prefix):
        return None, None
      try:
        key = key.replace(prefix, "", 1)
        item, suggid = key.split(".", 1)
        return int(item), int(suggid)
      except:
        return None, None
    for key, value in self.argdict.iteritems():
      item = getitem(key, "skip")
      if item is not None:
        skips.append(item)
      item = getitem(key, "submitsuggest")
      if item is not None:
        submitsuggests.append(item)
      item = getitem(key, "submit")
      if item is not None:
        submits.append(item)
      item, suggid = getpointitem(key, "accept")
      if item is not None:
        accepts.append((item, suggid))
      item, suggid = getpointitem(key, "reject")
      if item is not None:
        rejects.append((item, suggid))
      item = getitem(key, "trans")
      if item is not None:
        translations[item] = value
      item, suggid = getpointitem(key, "sugg")
      if item is not None:
        suggestions[item, suggid] = value
    for item in skips:
      self.lastitem = item
    for item in submitsuggests:
      if item in skips or item not in translations:
        continue
      value = translations[item]
      self.project.suggesttranslation(pofilename, item, value, self.session)
      self.lastitem = item
    for item in submits:
      if item in skips or item not in translations:
        continue
      value = translations[item]
      self.project.updatetranslation(pofilename, item, value, self.session)
      self.lastitem = item
    for item, suggid in rejects:
      value = suggestions[item, suggid]
      self.project.rejectsuggestion(pofilename, item, suggid, value, self.session)
      self.lastitem = item
    for item, suggid in accepts:
      if (item, suggid) in rejects or (item, suggid) not in suggestions:
        continue
      value = suggestions[item, suggid]
      self.project.acceptsuggestion(pofilename, item, suggid, value, self.session)
      self.lastitem = item

  def getmatchnames(self, checker): 
    """returns any checker filters the user has asked to match..."""
    matchnames = []
    for checkname in self.argdict:
      if checkname in ["fuzzy", "blank", "translated", "has-suggestion"]:
        matchnames.append(checkname)
      elif checkname in checker.getfilters():
        matchnames.append("check-" + checkname)
    matchnames.sort()
    return matchnames

  def finditem(self):
    """finds the focussed item for this page, searching as neccessary"""
    item = self.argdict.get("item", None)
    if item is None:
      try:
        search = pootlefile.Search(dirfilter=self.dirfilter, matchnames=self.matchnames, searchtext=self.searchtext)
        # TODO: find a nicer way to let people search stuff assigned to them (does it by default now)
        # search.assignedto = self.argdict.get("assignedto", self.session.username)
        search.assignedto = self.argdict.get("assignedto", None)
        search.assignedaction = self.argdict.get("assignedaction", None)
        self.pofilename, self.item = self.project.searchpoitems(self.pofilename, self.lastitem, search).next()
      except StopIteration:
        if self.lastitem is None:
          raise StopIteration(self.localize("There are no items matching that search ('%s')") % self.searchtext)
        else:
          raise StopIteration(self.localize("You have finished going through the items you selected"))
    else:
      if not item.isdigit():
        raise ValueError("Invalid item given")
      self.item = int(item)
      self.pofilename = self.argdict.get("pofilename", self.dirfilter)
    self.project.track(self.pofilename, self.item, "being edited by %s" % self.session.username)

  def gettranslations(self):
    """gets the list of translations desired for the view, and sets editable and firstitem parameters"""
    if self.item is None:
      self.editable = []
      self.firstitem = self.item
      return []
    elif self.viewmode:
      self.editable = []
      self.firstitem = self.item
      return self.project.getitems(self.pofilename, self.item, self.item+10)
    else:
      self.editable = [self.item]
      fromitem = self.item - 3
      self.firstitem = max(self.item - 3, 0)
      toitem = self.firstitem + 7
      return self.project.getitems(self.pofilename, fromitem, toitem)

  def maketable(self):
    self.translations = self.gettranslations()
    if self.reviewmode and self.item is not None:
      suggestions = {self.item: self.project.getsuggestions(self.pofilename, self.item)}
    self.transtable = table.TableLayout({"class":"translate-table", "cellpadding":10})
    origtitle = table.TableCell(self.localize("original"), {"class":"translate-table-title"})
    transtitle = table.TableCell(self.localize("translation"), {"class":"translate-table-title"})
    self.transtable.setcell(-1, 0, origtitle)
    self.transtable.setcell(-1, 1, transtitle)
    for row, (orig, trans) in enumerate(self.translations):
      item = self.firstitem + row
      itemclasses = self.project.getitemclasses(self.pofilename, item)
      origdiv = self.getorigdiv(item, orig, item in self.editable, itemclasses)
      if item in self.editable:
        if self.reviewmode:
          transdiv = self.gettransreview(item, trans, suggestions[item])
        else:
          transdiv = self.gettransedit(item, orig, trans)
      else:
        transdiv = self.gettransview(item, trans)
      polarity = oddoreven(item)
      origcell = table.TableCell(origdiv, {"class":"translate-original translate-original-%s" % polarity})
      self.transtable.setcell(row, 0, origcell)
      transcell = table.TableCell(transdiv, {"class":"translate-translation translate-translation-%s" % polarity})
      self.transtable.setcell(row, 1, transcell)
      if item in self.editable:
        origcell.attribs["class"] += " translate-focus"
        transcell.attribs["class"] += " translate-focus"
    self.transtable.shrinkrange()
    return self.transtable

  def escapetext(self, text):
    return self.escape(text).replace("\n", "</br>\n")

  def getorigdiv(self, item, orig, editable, itemclasses):
    origclass = "translate-original "
    if editable:
      origclass += "translate-original-focus "
    else:
      origclass += "autoexpand "
    origdiv = widgets.Division(self.escapetext(orig), "orig%d" % item, cls=origclass)
    return origdiv

  def geteditlink(self, item):
    """gets a link to edit the given item, if the user has permission"""
    if "translate" in self.rights or "suggest" in self.rights:
      translateurl = "?translate=1&item=%d&pofilename=%s" % (item, self.quote(self.pofilename))
      return pagelayout.TranslateActionLink(translateurl , "Edit", "editlink%d" % item)
    else:
      return ""

  def gettransbuttons(self, item, desiredbuttons=["skip", "copy", "suggest", "translate", "resize"]):
    """gets buttons for actions on translation"""
    buttons = []
    if "skip" in desiredbuttons:
      skipbutton = widgets.Input({"type":"submit", "name":"skip%d" % item, "value":"skip"}, self.localize("skip"))
      buttons.append(skipbutton)
    if "copy" in desiredbuttons:
      copyscript = "document.forms.translate.trans%d.value = document.getElementById('orig%d').innerHTML" % (item, item)
      copybutton = widgets.Button({"onclick": copyscript}, self.localize("copy"))
      buttons.append(copybutton)
    if "suggest" in desiredbuttons and "suggest" in self.rights:
      suggestbutton = widgets.Input({"type":"submit", "name":"submitsuggest%d" % item, "value":"suggest"}, self.localize("suggest"))
      buttons.append(suggestbutton)
    if "translate" in desiredbuttons and "translate" in self.rights:
      submitbutton = widgets.Input({"type":"submit", "name":"submit%d" % item, "value":"submit"}, self.localize("submit"))
      buttons.append(submitbutton)
    if "translate" in desiredbuttons or "suggest" in desiredbuttons:
      specialchars = getattr(getattr(self.session.instance.languages, self.project.languagecode, None), "specialchars", "")
      buttons.append(specialchars)
    if "resize" in desiredbuttons:
      growlink = widgets.Link('#', self.localize("Grow"), newattribs={"onclick": 'return expandtextarea(this)'})
      shrinklink = widgets.Link('#', self.localize("Shrink"), newattribs={"onclick": 'return contracttextarea(this)'})
      broadenlink = widgets.Link('#', self.localize("Broaden"), newattribs={"onclick": 'return broadentextarea(this)'})
      narrowlink = widgets.Link('#', self.localize("Narrow"), newattribs={"onclick": 'return narrowtextarea(this)'})
      usernode = getattr(self.session.loginchecker.users, self.session.username, None)
      rows = getattr(usernode, "inputheight", 5)
      cols = getattr(usernode, "inputwidth", 40)
      resetlink = widgets.Link('#', self.localize("Reset"), newattribs={"onclick": 'return resettextarea(this, %s, %s)' % (rows, cols)})
      buttons += [growlink, shrinklink, broadenlink, narrowlink, resetlink]
    return buttons

  def gettransedit(self, item, orig, trans):
    """returns a widget for editing the given item and translation"""
    trans = self.escape(trans).decode("utf8")
    if "translate" in self.rights or "suggest" in self.rights:
      min = 3
      max = 10
      cols = 40
      chars_orig = len(orig)
      chars_trans = len(trans)
      if chars_orig > chars_trans:
        ideal_rows = chars_orig/cols
      else:
        ideal_rows = chars_trans/cols
      if ideal_rows < min:
        rows = min
      elif ideal_rows > max:
        rows = max
      else:
        rows = ideal_rows
      text = widgets.TextArea({"name":"trans%d" % item, "rows":rows, "cols":cols}, contents=trans)
    else:
      text = pagelayout.TranslationText(trans)
    buttons = self.gettransbuttons(item)
    transdiv = widgets.Division([text, buttons], "trans%d" % item, cls="translate-translation")
    return transdiv

  def highlightdiffs(self, text, diffs, issrc=True):
    """highlights the differences in diffs in the text.
    diffs should be list of diff opcodes
    issrc specifies whether to use the src or destination positions in reconstructing the text
    this escapes the text on the fly to prevent confusion in escaping the highlighting"""
    if issrc:
      diffstart = [(i1, 'start', tag) for (tag, i1, i2, j1, j2) in diffs if tag != 'equal']
      diffstop = [(i2, 'stop', tag) for (tag, i1, i2, j1, j2) in diffs if tag != 'equal']
    else:
      diffstart = [(j1, 'start', tag) for (tag, i1, i2, j1, j2) in diffs if tag != 'equal']
      diffstop = [(j2, 'stop', tag) for (tag, i1, i2, j1, j2) in diffs if tag != 'equal']
    diffswitches = diffstart + diffstop
    diffswitches.sort()
    textdiff = ""
    textnest = 0
    textpos = 0
    for i, switch, tag in diffswitches:
      textdiff += self.escape(text[textpos:i])
      if switch == 'start':
        textnest += 1
      elif switch == 'stop':
        textnest -= 1
      if switch == 'start' and textnest == 1:
        # start of a textition
        textdiff += "<span class='translate-diff-%s'>" % tag
      elif switch == 'stop' and textnest == 0:
        # start of an equals block
        textdiff += "</span>"
      textpos = i
    textdiff += self.escape(text[textpos:])
    return textdiff

  def gettransreview(self, item, trans, suggestions):
    """returns a widget for reviewing the given item's suggestions"""
    if isinstance(trans, str):
      trans = trans.decode("utf8")
    for suggid in range(len(suggestions)):
      suggestion = suggestions[suggid]
      if isinstance(suggestion, str):
        suggestions[suggid] = suggestion.decode("utf8")
    currenttitle = widgets.Division(self.localize("<b>Current Translation:</b>"))
    diffcodes = [difflib.SequenceMatcher(None, trans, suggestion).get_opcodes() for suggestion in suggestions]
    combineddiffs = reduce(list.__add__, diffcodes, [])
    transdiff = self.highlightdiffs(trans, combineddiffs, issrc=True)
    editlink = self.geteditlink(item)
    currenttext = pagelayout.TranslationText([editlink, transdiff])
    suggdivs = []
    for suggid, suggestion in enumerate(suggestions):
      suggdiffcodes = diffcodes[suggid]
      suggdiff = self.highlightdiffs(suggestion, suggdiffcodes, issrc=False)
      suggestedby = self.project.getsuggester(self.pofilename, item, suggid)
      if isinstance(suggestion, str):
        suggestion = suggestion.decode("utf8")
      if len(suggestions) > 1:
        if suggestedby:
          suggtitle = self.localize("Suggestion %d by %s:") % (suggid+1, suggestedby)
        else:
          suggtitle = self.localize("Suggestion %d:") % (suggid+1)
      else:
        if suggestedby:
          suggtitle = self.localize("Suggestion by %s:") % (suggestedby)
        else:
          suggtitle = self.localize("Suggestion:")
      suggtitle = widgets.Division("<b>%s</b>" % suggtitle)
      suggestiontext = pagelayout.TranslationText(suggdiff)
      suggestionhidden = widgets.Input({'type': 'hidden', "name": "sugg%d.%d" % (item, suggid), 'value': suggestion})
      if "review" in self.rights:
        acceptbutton = widgets.Input({"type":"submit", "name":"accept%d.%d" % (item, suggid), "value":"accept"}, "accept")
        rejectbutton = widgets.Input({"type":"submit", "name":"reject%d.%d" % (item, suggid), "value":"reject"}, "reject")
        buttons = [acceptbutton, rejectbutton]
      else:
        buttons = []
      suggdiv = widgets.Division(["<br/>", suggtitle, suggestiontext, suggestionhidden, "<br/>", buttons], "sugg%d" % item)
      suggdivs.append(suggdiv)
    transbuttons = self.gettransbuttons(item, ["skip"])
    if suggdivs:
      suggdivs[-1].addcontents(transbuttons)
    else:
      suggdivs.append(transbuttons)
    transdiv = widgets.Division([currenttitle, currenttext] + suggdivs, "trans%d" % item, cls="translate-translation")
    return transdiv

  def gettransview(self, item, trans):
    """returns a widget for viewing the given item's translation"""
    editlink = self.geteditlink(item)
    text = pagelayout.TranslationText([editlink, self.escape(trans)])
    transdiv = widgets.Division(text, "trans%d" % item, cls="translate-translation autoexpand")
    return transdiv

