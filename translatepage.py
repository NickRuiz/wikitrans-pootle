#!/usr/bin/env python

import sre
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

class TranslatePage(pagelayout.PootleNavPage):
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
    mainstats = []
    if self.pofilename is not None:
      postats = self.project.getpostats(self.pofilename)
      blank, fuzzy = postats["blank"], postats["fuzzy"]
      translated, total = postats["translated"], postats["total"]
      mainstats = self.localize("%d/%d translated\n(%d blank, %d fuzzy)") % (translated, total, blank, fuzzy)
    if self.viewmode:
      rows = self.getdisplayrows("view")
      pagelinks = self.getpagelinks("?translate=1&view=1", rows)
      icon="file"
    else:
      pagelinks = []
      icon="edit"
    mainitem = self.makenavbar(icon=icon, path=self.makenavbarpath(self.project, self.session, dirfilter), stats=mainstats, pagelinks=pagelinks)
    translatediv = pagelayout.TranslateForm([notice, translateform, pagelinks])
    pagelayout.PootleNavPage.__init__(self, title, [mainitem, translatediv], session, bannerheight=81, returnurl="%s/%s/%s" % (self.project.languagecode, self.project.projectcode, dirfilter))
    self.addfilelinks(self.pofilename, self.matchnames)
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
      if matchnames:
        checknames = [matchname.replace("check-", "", 1) for matchname in matchnames]
        self.links.addcontents(pagelayout.SidebarText(self.localize("checking %s") % ", ".join(checknames)))

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
    pluralitems = {}
    keymatcher = sre.compile("(\D+)([0-9.]+)")
    def parsekey(key):
      match = keymatcher.match(key)
      if match:
        keytype, itemcode = match.groups()
        return keytype, itemcode
      return None, None
    def pointsplit(item):
      if "." in item:
        item, suggid = item.split(".", 1)
        return int(item), int(suggid)
      else:
        return int(item), None
    for key, value in self.argdict.iteritems():
      keytype, item = parsekey(key)
      if keytype is None:
        continue
      item, pointitem = pointsplit(item)
      if keytype == "pluralforms":
        pluralitems[item] = int(value)
      if keytype == "skip":
        skips.append(item)
      if keytype == "submitsuggest":
        submitsuggests.append(item)
      if keytype == "submit":
        submits.append(item)
      if keytype == "accept":
        accepts.append((item, pointitem))
      if keytype == "reject":
        rejects.append((item, pointitem))
      if keytype == "trans":
        if pointitem is not None:
          translations.setdefault(item, {})[pointitem] = value
        else:
          translations[item] = value
      if keytype == "suggest":
        suggestions[item, pointitem] = value
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

  def getdisplayrows(self, mode):
    """get the number of rows to display for the given mode"""
    if mode == "view":
      prefsfield = "viewrows"
      default = 10
      maximum = 100
    elif mode == "translate":
      prefsfield = "translaterows"
      default = 7
      maximum = 20
    else:
      raise ValueError("getdisplayrows has no mode '%s'" % mode)
    usernode = getattr(self.session.loginchecker.users, self.session.username, None)
    rowsdesired = getattr(usernode, prefsfield, default)
    if isinstance(rowsdesired, str):
      if rowsdesired == "":
        rowsdesired = default
      else:
        rowsdesired = int(rowsdesired)
    rowsdesired = min(rowsdesired, maximum)
    return rowsdesired

  def gettranslations(self):
    """gets the list of translations desired for the view, and sets editable and firstitem parameters"""
    if self.item is None:
      self.editable = []
      self.firstitem = self.item
      return []
    elif self.viewmode:
      self.editable = []
      self.firstitem = self.item
      rows = self.getdisplayrows("view")
      return self.project.getitems(self.pofilename, self.item, self.item+rows)
    else:
      self.editable = [self.item]
      rows = self.getdisplayrows("translate")
      before = rows / 2
      fromitem = self.item - before
      self.firstitem = max(self.item - before, 0)
      toitem = self.firstitem + rows
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
      origdiv = self.getorigdiv(item, orig, item in self.editable)
      if item in self.editable:
        if self.reviewmode:
          transdiv = self.gettransreview(item, trans, suggestions[item])
        else:
          transdiv = self.gettransedit(item, trans)
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

  def getorigdiv(self, item, orig, editable):
    origclass = "translate-original "
    if editable:
      origclass += "translate-original-focus "
    else:
      origclass += "autoexpand "
    if len(orig) > 1:
      origpuresingular = widgets.Input({"type": "hidden", "id": "orig-hidden%d.0" % item, "value": orig[0]})
      origpureplural = widgets.Input({"type": "hidden", "id": "orig-hidden%d.1" % item, "value": orig[1]})
      origpure = [origpuresingular, origpureplural]
      htmlbreak = "<br/>\n"
      origpretty = [pagelayout.TranslationHeaders(self.localize("Singular")), htmlbreak, 
                    self.escapetext(orig[0]), htmlbreak,
                    pagelayout.TranslationHeaders(self.localize("Plural")), htmlbreak,
                    self.escapetext(orig[1])]
    else:
      origpure = widgets.Input({"type": "hidden", "id": "orig-hidden%d" % item, "value": orig[0]})
      origpretty = self.escapetext(orig[0])
    origdiv = widgets.Division([origpure, origpretty], "orig%d" % item, cls=origclass)
    return origdiv

  def geteditlink(self, item):
    """gets a link to edit the given item, if the user has permission"""
    if "translate" in self.rights or "suggest" in self.rights:
      translateurl = "?translate=1&item=%d&pofilename=%s" % (item, self.quote(self.pofilename))
      return pagelayout.TranslateActionLink(translateurl , self.localize("Edit"), "editlink%d" % item)
    else:
      return ""

  def gettransbuttons(self, item, desiredbuttons=["skip", "copy", "suggest", "translate", "resize"]):
    """gets buttons for actions on translation"""
    buttons = []
    if "skip" in desiredbuttons:
      skipbutton = widgets.Input({"type":"submit", "name":"skip%d" % item, "value":self.localize("skip")})
      buttons.append(skipbutton)
    if "copy" in desiredbuttons:
      copyscript = "document.forms.translate.trans%d.value = document.getElementById('orig-hidden%d').value" % (item, item)
      copybutton = widgets.Button({"onclick": copyscript}, self.localize("copy"))
      buttons.append(copybutton)
    if "suggest" in desiredbuttons and "suggest" in self.rights:
      suggestbutton = widgets.Input({"type":"submit", "name":"submitsuggest%d" % item, "value":self.localize("suggest")})
      buttons.append(suggestbutton)
    if "translate" in desiredbuttons and "translate" in self.rights:
      submitbutton = widgets.Input({"type":"submit", "name":"submit%d" % item, "value":self.localize("submit")})
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

  def gettransedit(self, item, trans):
    """returns a widget for editing the given item and translation"""
    if "translate" in self.rights or "suggest" in self.rights:
      usernode = getattr(self.session.loginchecker.users, self.session.username, None)
      rows = getattr(usernode, "inputheight", 5)
      cols = getattr(usernode, "inputwidth", 40)
      if len(trans) > 1:
        buttons = self.gettransbuttons(item, ["skip", "suggest", "translate"])
        pluralforms = [widgets.HiddenFieldList([("pluralforms%d" % item, len(trans))])]
        htmlbreak = "<br />"
        for pluralitem, pluraltext in enumerate(trans):
          pluralform = self.localize("Plural Form %d") % pluralitem
          pluraltext = self.escape(pluraltext).decode("utf-8")
          textid = "trans%d.%d" % (item, pluralitem)
          text = widgets.TextArea({"name": textid, "rows":rows, "cols":cols}, contents=pluraltext)
          pluralforms += [pagelayout.TranslationHeaders(pluralform), htmlbreak, text, htmlbreak]
        transdiv = widgets.Division([pluralforms, buttons], "trans%d" % item, cls="translate-translation")
      else:
        buttons = self.gettransbuttons(item, ["skip"])
        trans = self.escape(trans[0]).decode("utf8")
        text = widgets.TextArea({"name":"trans%d" % item, "rows":rows, "cols":cols}, contents=trans)
        transdiv = widgets.Division([text, "<br />", buttons], "trans%d" % item, cls="translate-translation")
    else:
      transdiv = self.gettransview(item, trans)
      buttons = self.gettransbuttons(item, ["skip"])
      transdiv.addcontents(buttons)
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

  def getdiffcodes(self, cmp1, cmp2):
    """compares the two strings and returns opcodes"""
    if isinstance(cmp1, str):
      cmp1 = cmp1.decode("utf-8")
    if isinstance(cmp2, str):
      cmp2 = cmp2.decode("utf-8")
    return difflib.SequenceMatcher(None, cmp1, cmp2).get_opcodes()

  def gettransreview(self, item, trans, suggestions):
    """returns a widget for reviewing the given item's suggestions"""
    currenttitle = widgets.Division(self.localize("<b>Current Translation:</b>"))
    hasplurals = len(trans) > 1
    editlink = self.geteditlink(item)
    currenttext = [editlink]
    diffcodes = {}
    htmlbreak = "<br/>"
    for pluralitem, pluraltrans in enumerate(trans):
      pluraldiffcodes = [self.getdiffcodes(pluraltrans, suggestion.get(pluralitem, "")) for suggestion in suggestions]
      diffcodes[pluralitem] = pluraldiffcodes
      combineddiffs = reduce(list.__add__, pluraldiffcodes, [])
      transdiff = self.highlightdiffs(pluraltrans, combineddiffs, issrc=True)
      if hasplurals:
        pluralform = self.localize("Plural Form %d") % pluralitem
        currenttext.append([pagelayout.TranslationHeaders(pluralform), htmlbreak])
      currenttext.append([transdiff, htmlbreak])
    suggitems = []
    for suggid, suggestion in enumerate(suggestions):
      suggtext = []
      suggestedby = self.project.getsuggester(self.pofilename, item, suggid)
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
      suggtitle = ["<b>%s</b>" % suggtitle, htmlbreak]
      for pluralitem, pluraltrans in enumerate(trans):
        pluralsuggestion = suggestion.get(pluralitem, "")
        suggdiffcodes = diffcodes[pluralitem][suggid]
        suggdiff = self.highlightdiffs(pluralsuggestion, suggdiffcodes, issrc=False)
        if isinstance(pluralsuggestion, str):
          pluralsuggestion = pluralsuggestion.decode("utf8")
        if hasplurals:
          pluralform = self.localize("Plural Form %d") % pluralitem
          suggtext.append([pagelayout.TranslationHeaders(pluralform), htmlbreak])
        suggtext.append([pagelayout.TranslationText(suggdiff), htmlbreak])
      suggestionhidden = widgets.Input({'type': 'hidden', "name": "sugg%d.%d" % (item, suggid), 'value': suggestion})
      if "review" in self.rights:
        acceptbutton = widgets.Input({"type":"submit", "name":"accept%d.%d" % (item, suggid), "value":self.localize("accept")})
        rejectbutton = widgets.Input({"type":"submit", "name":"reject%d.%d" % (item, suggid), "value":self.localize("reject")})
        buttons = [acceptbutton, rejectbutton]
      else:
        buttons = []
      suggdiv = [suggtitle, suggtext, suggestionhidden, "<br/>", buttons]
      suggitems.append(suggdiv)
    transbuttons = self.gettransbuttons(item, ["skip"])
    if suggitems:
      suggitems[-1].append(transbuttons)
    else:
      suggitems.append(transbuttons)
    transdiv = widgets.Division(pagelayout.TranslationText([currenttitle, currenttext] + suggitems), "trans%d" % item, cls="translate-translation")
    return transdiv

  def gettransview(self, item, trans):
    """returns a widget for viewing the given item's translation"""
    editlink = self.geteditlink(item)
    if len(trans) > 1:
      text = [editlink]
      htmlbreak = "<br />"
      for pluralitem, pluraltext in enumerate(trans):
        pluralform = self.localize("Plural Form %d") % pluralitem
        text += [pagelayout.TranslationHeaders(pluralform), htmlbreak, self.escape(pluraltext), htmlbreak]
      text = pagelayout.TranslationText(text)
    else:
      text = pagelayout.TranslationText([editlink, self.escape(trans[0])])
    transdiv = widgets.Division(text, "trans%d" % item, cls="translate-translation autoexpand")
    return transdiv

