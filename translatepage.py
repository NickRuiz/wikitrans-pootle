#!/usr/bin/env python
# -*- coding: utf-8 -*-
# 
# Copyright 2004-2006 Zuza Software Foundation
# 
# This file is part of translate.
#
# translate is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# translate is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with translate; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sre
from jToolkit import spellcheck
from Pootle import pagelayout
from Pootle import projects
from Pootle import pootlefile
import difflib
import urllib

def oddoreven(polarity):
  if polarity % 2 == 0:
    return "even"
  elif polarity % 2 == 1:
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
    self.lastitem = None
    self.pofilename = self.argdict.pop("pofilename", None)
    if self.pofilename == "":
      self.pofilename = None
    if self.pofilename is None and self.dirfilter is not None and self.dirfilter.endswith(".po"):
      self.pofilename = self.dirfilter
    self.receivetranslations()
    # TODO: clean up modes to be one variable
    self.viewmode = self.argdict.get("view", 0) and "view" in self.rights
    self.reviewmode = self.argdict.get("review", 0)
    notice = {}
    try:
      self.finditem()
    except StopIteration, stoppedby:
      notice = self.getfinishedtext(stoppedby)
      self.item = None
    items = self.maketable()
    # self.pofilename can change in search...
    givenpofilename = self.pofilename
    formaction = self.makelink("")
    title = self.localize("Pootle: translating %s into %s: %s", self.project.projectname, self.project.languagename, self.pofilename)
    mainstats = ""
    if self.pofilename is not None:
      postats = self.project.getpostats(self.pofilename)
      blank, fuzzy = postats["blank"], postats["fuzzy"]
      translated, total = postats["translated"], postats["total"]
      mainstats = self.localize("%d/%d translated\n(%d blank, %d fuzzy)", len(translated), len(total), len(blank), len(fuzzy))
    if self.viewmode:
      rows = self.getdisplayrows("view")
      pagelinks = self.getpagelinks("?translate=1&view=1", rows)
      icon="file"
    else:
      pagelinks = []
      icon="edit"
    navbarpath_dict = self.makenavbarpath_dict(self.project, self.session, self.pofilename)
    # templatising
    templatename = "translatepage"
    instancetitle = getattr(session.instance, "title", session.localize("Pootle Demo"))
    # l10n: The first parameter is the name of the installation (like "Pootle")
    # l10n: The second parameter is the name of the project
    # l10n: The third parameter is the target language
    # l10n: The fourth parameter is the filename
    pagetitle = self.localize("%s: translating %s into %s: %s", instancetitle, self.project.projectname, self.project.languagename, self.pofilename)
    sessionvars = {"status": session.status, "isopen": session.isopen, "issiteadmin": session.issiteadmin()}
    stats = {"summary": mainstats, "checks": [], "tracks": [], "assigns": []}
    templatevars = {"pagetitle": pagetitle,
        "project": {"code": self.project.projectcode, "name": self.project.projectname},
        "language": {"code": self.project.languagecode, "name": self.project.languagename},
        "pofilename": self.pofilename,
        # navigation bar
        "navitems": [{"icon": "edit", "path": navbarpath_dict, "actions": {}, "stats": stats}],
        "pagelinks": pagelinks,
        # translation form
        "actionurl": formaction,
        "notice": notice,
        "original_title": self.localize("Original"),
        "translation_title": self.localize("Translation"),
        "items": items,
        "reviewmode": self.reviewmode,
        "accept_button": self.localize("Accept"),
        "reject_button": self.localize("Reject"),
        # optional sections, will appear if these values are replaced
        "assign": None,
        "search": {"title": self.localize("Search")},
        # hidden widgets
        "searchtext": self.searchtext,
        "pofilename": givenpofilename,
        # general vars
        "session": sessionvars, "instancetitle": instancetitle}
    if self.showassigns and "assign" in self.rights:
      templatevars["assign"] = self.getassignbox()
    pagelayout.PootleNavPage.__init__(self, templatename, templatevars, session, bannerheight=81)
    self.addfilelinks(self.pofilename, self.matchnames)

  def getfinishedtext(self, stoppedby):
    """gets notice to display when the translation is finished"""
    title = self.localize("End of batch")
    finishedlink = "index.html?" + "&".join(["%s=%s" % (arg, value) for arg, value in self.argdict.iteritems() if arg.startswith("show") or arg == "editing"])
    returnlink = self.localize("Click here to return to the index")
    stoppedbytext = stoppedby.args[0]
    return {"title": title, "stoppedby": stoppedbytext, "finishedlink": finishedlink, "returnlink": returnlink}

  def getpagelinks(self, baselink, pagesize):
    """gets links to other pages of items, based on the given baselink"""
    pagelinks = []
    pofilelen = self.project.getpofilelen(self.pofilename)
    if pofilelen <= pagesize or self.firstitem is None:
      return pagelinks
    lastitem = min(pofilelen-1, self.firstitem + pagesize - 1)
    if pofilelen > pagesize and not self.firstitem == 0:
      pagelinks.append({"href": baselink + "&item=0", "text": self.localize("Start")})
    else:
      pagelinks.append({"text": self.localize("Start")})
    if self.firstitem > 0:
      linkitem = max(self.firstitem - pagesize, 0)
      pagelinks.append({"href": baselink + "&item=%d" % linkitem, "text": self.localize("Previous %d", (self.firstitem - linkitem))})
    else:
      pagelinks.append({"text": self.localize("Previous %d", pagesize)})
    pagelinks.append({"text": self.localize("Items %d to %d of %d", self.firstitem+1, lastitem+1, pofilelen)})
    if self.firstitem + len(self.translations) < self.project.getpofilelen(self.pofilename):
      linkitem = self.firstitem + pagesize
      itemcount = min(pofilelen - linkitem, pagesize)
      pagelinks.append({"href": baselink + "&item=%d" % linkitem, "text": self.localize("Next %d", itemcount)})
    else:
      pagelinks.append({"text": self.localize("Next %d", pagesize)})
    if pofilelen > pagesize and (self.item + pagesize) < pofilelen:
      pagelinks.append({"href": baselink + "&item=%d" % max(pofilelen - pagesize, 0), "text": self.localize("End")})
    else:
      pagelinks.append({"text": self.localize("End")})
    for n, pagelink in enumerate(pagelinks):
      if n < len(pagelinks)-1:
        pagelink["sep"] = " | "
      else:
        pagelink["sep"] = ""
    return pagelinks

  def addfilelinks(self, pofilename, matchnames):
    """adds a section on the current file, including any checks happening"""
    if self.showassigns and "assign" in self.rights:
      self.templatevars["assigns"] = self.getassignbox()
    if self.pofilename is not None:
      if matchnames:
        checknames = [matchname.replace("check-", "", 1) for matchname in matchnames]
        self.templatevars["checking_text"] = self.localize("checking %s", ", ".join(checknames))

  def getassignbox(self):
    """gets strings if the user can assign strings"""
    users = [username for username, userprefs in self.session.loginchecker.users.iteritems() if username != "__dummy__"]
    users.sort()
    return {
      "title": self.localize("Assign Strings"),
      "user_title": self.localize("Assign to User"),
      "action_title": self.localize("Assign Action"),
      "submit_text": self.localize("Assign Strings"),
      "users": users,
    }

  def receivetranslations(self):
    """receive any translations submitted by the user"""
    if self.pofilename is None:
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
      dotcount = item.count(".")
      if dotcount == 2:
        item, pointitem, subpointitem = item.split(".", 2)
        return int(item), int(pointitem), int(subpointitem)
      elif dotcount == 1:
        item, pointitem = item.split(".", 1)
        return int(item), int(pointitem), None
      else:
        return int(item), None, None
    delkeys = []
    for key, value in self.argdict.iteritems():
      keytype, item = parsekey(key)
      if keytype is None:
        continue
      item, pointitem, subpointitem = pointsplit(item)
      if keytype == "skip":
        skips.append(item)
      elif keytype == "submitsuggest":
        submitsuggests.append(item)
      elif keytype == "submit":
        submits.append(item)
      elif keytype == "accept":
        accepts.append((item, pointitem))
      elif keytype == "reject":
        rejects.append((item, pointitem))
      elif keytype == "trans":
        value = self.unescapesubmition(value)
        if pointitem is not None:
          translations.setdefault(item, {})[pointitem] = value
        else:
          translations[item] = value
      elif keytype == "suggest":
        suggestions.setdefault((item, pointitem), {})[subpointitem] = value
      elif keytype == "orig-pure":
        # this is just to remove the hidden fields from the argdict
        pass
      else:
        continue
      delkeys.append(key)
    for key in delkeys:
      del self.argdict[key]
    for item in skips:
      self.lastitem = item
    for item in submitsuggests:
      if item in skips or item not in translations:
        continue
      value = translations[item]
      self.project.suggesttranslation(self.pofilename, item, value, self.session)
      self.lastitem = item
    for item in submits:
      if item in skips or item not in translations:
        continue
      value = translations[item]
      if isinstance(value, dict) and len(value) == 1 and 0 in value:
        value = value[0]
      self.project.updatetranslation(self.pofilename, item, value, self.session)
      self.lastitem = item
    for item, suggid in rejects:
      value = suggestions[item, suggid]
      if isinstance(value, dict) and len(value) == 1 and 0 in value:
        value = value[0]
      self.project.rejectsuggestion(self.pofilename, item, suggid, value, self.session)
      self.lastitem = item
    for item, suggid in accepts:
      if (item, suggid) in rejects or (item, suggid) not in suggestions:
        continue
      value = suggestions[item, suggid]
      if isinstance(value, dict) and len(value) == 1 and 0 in value:
        value = value[0]
      self.project.acceptsuggestion(self.pofilename, item, suggid, value, self.session)
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

  def getusernode(self):
    """gets the user's prefs node"""
    if self.session.isopen:
      return getattr(self.session.loginchecker.users, self.session.username, None)
    else:
      return None

  def finditem(self):
    """finds the focussed item for this page, searching as neccessary"""
    item = self.argdict.pop("item", None)
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
          raise StopIteration(self.localize("There are no items matching that search ('%s')", self.searchtext))
        else:
          raise StopIteration(self.localize("You have finished going through the items you selected"))
    else:
      if not item.isdigit():
        raise ValueError("Invalid item given")
      self.item = int(item)
      if self.pofilename is None:
        raise ValueError("Received item argument but no pofilename argument")
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
    usernode = self.getusernode()
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
    items = []
    for row, thepo in enumerate(self.translations):
      orig = thepo.unquotedmsgid
      trans = thepo.unquotedmsgstr
      item = self.firstitem + row
      origdict = self.getorigdict(item, orig, item in self.editable)
      transmerge = {}
      if item in self.editable:
        comments = thepo.getnotes().replace("\n", "\n<br />")
        locations = " ".join(thepo.getlocations())
        
        if self.reviewmode:
          itemsuggestions = [suggestion.unquotedmsgstr for suggestion in suggestions[item]]
          transmerge = self.gettransreview(item, trans, itemsuggestions)
        else:
          transmerge = self.gettransedit(item, trans)
      else:
        comments = ""
        locations = ""
        transmerge = self.gettransview(item, trans)
      transdict = {"itemid": "trans%d" % item,
                   "focus_class": origdict["focus_class"],
                   "isplural": len(trans) > 1,
                  }
      transdict.update(transmerge)
      polarity = oddoreven(item)
      origcell_class = "translate-original translate-original-%s" % polarity
      transcell_class = "translate-translation translate-translation-%s" % polarity
      if item in self.editable:
        focus_class = "translate-focus"
      else:
        focus_class = ""
      
      state_class = ""
      if thepo.isfuzzy():
        state_class += "translate-translation-fuzzy"

      itemdict = {
                 "itemid": item,
                 "orig": origdict,
                 "trans": transdict,
                 "polarity": polarity,
                 "focus_class": focus_class,
                 "editable": item in self.editable,
                 "state_class": state_class,
                 "comments": comments,
                 "locations": locations,
                 }
      items.append(itemdict)
    return items

  def escapetext(self, text):
    """Replace special characters &, <, >, add and handle quotes if asked"""
    text = text.replace("&", "&amp;") # Must be done first!
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    #TODO:Show fancy spaces
    text = text.replace("\r\n", '\\r\\n<br />\n')
    text = text.replace("\n", '\\n<br />\n')
    text = text.replace("\r", '\\r<br />\n')
    text = text.replace("\t", '\\t')
    return text

  def escapefortextarea(self, text):
    text = text.replace("&", "&amp;") # Must be done first!
    text = text.replace("<", "&lt;").replace(">", "&gt;")
    text = text.replace("\r\n", '\\r\\n\n')
    text = text.replace("\n", '\\n\n')
    text = text.replace("\t", '\\t')
    return text

  def unescapesubmition(self, text):
    text = text.replace("\t", "")
    text = text.replace("\n", "")
    text = text.replace("\r", "")
    text = text.replace("\\t", "\t")
    text = text.replace("\\n", "\n")
    text = text.replace("\\r", "\r")
    return text

  def getorigdict(self, item, orig, editable):
    if editable:
      focus_class = "translate-original-focus"
    else:
      focus_class = "autoexpand"
    purefields = []
    for pluralid, pluraltext in enumerate(orig):
      pureid = "orig-pure%d.%d" % (item, pluralid)
      purefields.append({"pureid": pureid, "name": pureid, "value": pluraltext})
    origdict = {
           "focus_class": focus_class,
           "itemid": "orig%d" % item,
           "pure": purefields,
           "isplural": len(orig) > 1 or None,
           "singular_title": self.localize("Singular"),
           "plural_title": self.localize("Plural"),
           }
    if len(orig) > 1:
      origdict["singular_text"] = self.escapetext(orig[0])
      origdict["plural_text"] = self.escapetext(orig[1])
    else:
      origdict["text"] = self.escapetext(orig[0])
    return origdict

  def geteditlink(self, item):
    """gets a link to edit the given item, if the user has permission"""
    if "translate" in self.rights or "suggest" in self.rights:
      translateurl = "?translate=1&item=%d&pofilename=%s" % (item, urllib.quote(self.pofilename, '/'))
      return {"href": translateurl, "text": self.localize("Edit"), "linkid": "editlink%d" % item}
    else:
      return None

  def gettransbuttons(self, item, desiredbuttons):
    """gets buttons for actions on translation"""
    if "suggest" in desiredbuttons and "suggest" not in self.rights:
      desiredbuttons.remove("suggest")
    if "translate" in desiredbuttons and "translate" not in self.rights:
      desiredbuttons.remove("translate")
    specialchars = getattr(getattr(self.session.instance.languages, self.project.languagecode, None), "specialchars", "")
    if isinstance(specialchars, str):
      specialchars = specialchars.decode("utf-8")
    usernode = self.getusernode()
    return {"desired": desiredbuttons,
            "item": item,
            "copy_text": self.localize("Copy"),
            "skip": self.localize("Skip"),
            "suggest": self.localize("Suggest"),
            "submit": self.localize("Submit"),
            "specialchars": specialchars,
            "rows": getattr(usernode, "inputheight", 5),
            "cols": getattr(usernode, "inputwidth", 40),
            "grow": self.localize("Grow"),
            "shrink": self.localize("Shrink"),
            "broaden": self.localize("Broaden"),
            "narrow": self.localize("Narrow"),
            "reset": self.localize("Reset")
           }

  def gettransedit(self, item, trans):
    """returns a widget for editing the given item and translation"""
    if "translate" in self.rights or "suggest" in self.rights:
      usernode = self.getusernode()
      transdict = {
                  "isplural": len(trans) > 1 or None,
                  "rows": getattr(usernode, "inputheight", 5),
                  "cols": getattr(usernode, "inputwidth", 40),
                  }
      focusbox = ""
      spellargs = {"standby_url": "spellingstandby.html", "js_url": "/js/spellui.js", "target_url": "spellcheck.html"}
      if len(trans) > 1:
        buttons = self.gettransbuttons(item, ["skip", "suggest", "translate"])
        forms = []
        for pluralitem, pluraltext in enumerate(trans):
          pluralform = self.localize("Plural Form %d", pluralitem)
          pluraltext = self.escapefortextarea(pluraltext)
          textid = "trans%d.%d" % (item, pluralitem)
          forms.append({"title": pluralform, "name": textid, "text": pluraltext, "n": pluralitem})
          if not focusbox:
            focusbox = textid
        transdict["forms"] = forms
      else:
        buttons = self.gettransbuttons(item, ["skip", "copy", "suggest", "translate", "resize"])
        transdict["text"] = self.escapefortextarea(trans[0])
        textid = "trans%d" % item
        focusbox = textid
      transdict["can_spell"] = spellcheck.can_check_lang(self.project.languagecode)
      transdict["spell_args"] = spellargs
      transdict["buttons"] = buttons
      transdict["focusbox"] = focusbox
    else:
      # TODO: work out how to handle this (move it up?)
      transdict = self.gettransview(item, trans, textarea=True)
      buttons = self.gettransbuttons(item, ["skip"])
    transdict["buttons"] = buttons
    return transdict

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
    spanempty = False
    for i, switch, tag in diffswitches:
      textsection = self.escapetext(text[textpos:i])
      textdiff += textsection
      if textsection:
        spanempty = False
      if switch == 'start':
        textnest += 1
      elif switch == 'stop':
        textnest -= 1
      if switch == 'start' and textnest == 1:
        # start of a textition
        textdiff += "<span class='translate-diff-%s'>" % tag
        spanempty = True
      elif switch == 'stop' and textnest == 0:
        # start of an equals block
        if spanempty:
          # FIXME: work out why kid swallows empty spans, and browsers display them horribly, then remove this
          textdiff += "()"
        textdiff += "</span>"
      textpos = i
    textdiff += self.escapetext(text[textpos:])
    return textdiff

  def getdiffcodes(self, cmp1, cmp2):
    """compares the two strings and returns opcodes"""
    return difflib.SequenceMatcher(None, cmp1, cmp2).get_opcodes()

  def gettransreview(self, item, trans, suggestions):
    """returns a widget for reviewing the given item's suggestions"""
    hasplurals = len(trans) > 1
    diffcodes = {}
    for pluralitem, pluraltrans in enumerate(trans):
      if isinstance(pluraltrans, str):
        trans[pluralitem] = pluraltrans.decode("utf-8")
    for suggestion in suggestions:
      for pluralitem, pluralsugg in enumerate(suggestion):
        if isinstance(pluralsugg, str):
          suggestion[pluralitem] = pluralsugg.decode("utf-8")
    forms = []
    for pluralitem, pluraltrans in enumerate(trans):
      pluraldiffcodes = [self.getdiffcodes(pluraltrans, suggestion[pluralitem]) for suggestion in suggestions]
      diffcodes[pluralitem] = pluraldiffcodes
      combineddiffs = reduce(list.__add__, pluraldiffcodes, [])
      transdiff = self.highlightdiffs(pluraltrans, combineddiffs, issrc=True)
      form = {"n": pluralitem, "diff": transdiff, "title": None}
      if hasplurals:
        pluralform = self.localize("Plural Form %d", pluralitem)
        form["title"] = pluralform
      forms.append(form)
    transdict = {
                "current_title": self.localize("Current Translation:"),
                "editlink": self.geteditlink(item),
                "forms": forms,
                "isplural": hasplurals or None,
                "itemid": "trans%d" % item,
                }
    suggitems = []
    for suggid, msgstr in enumerate(suggestions):
      suggestedby = self.project.getsuggester(self.pofilename, item, suggid)
      if len(suggestions) > 1:
        if suggestedby:
          suggtitle = self.localize("Suggestion %d by %s:", suggid+1, suggestedby)
        else:
          suggtitle = self.localize("Suggestion %d:", suggid+1)
      else:
        if suggestedby:
          suggtitle = self.localize("Suggestion by %s:", suggestedby)
        else:
          suggtitle = self.localize("Suggestion:")
      forms = []
      for pluralitem, pluraltrans in enumerate(trans):
        pluralsuggestion = msgstr[pluralitem]
        suggdiffcodes = diffcodes[pluralitem][suggid]
        suggdiff = self.highlightdiffs(pluralsuggestion, suggdiffcodes, issrc=False)
        if isinstance(pluralsuggestion, str):
          pluralsuggestion = pluralsuggestion.decode("utf8")
        form = {"diff": suggdiff}
        form["suggid"] = "suggest%d.%d.%d" % (item, suggid, pluralitem)
        form["value"] = pluralsuggestion
        if hasplurals:
          form["title"] = self.localize("Plural Form %d", pluralitem)
        forms.append(form)
      suggdict = {"title": suggtitle,
                  "forms": forms,
                  "suggid": "%d.%d" % (item, suggid),
                  "canreview": "review" in self.rights,
                  "skip": None,
                 }
      suggitems.append(suggdict)
    skipbutton = {"item": item, "text": self.localize("Skip")}
    if suggitems:
      suggitems[-1]["skip"] = skipbutton
    else:
      transdict["skip"] = skipbutton
    transdict["suggestions"] = suggitems
    return transdict

  def gettransview(self, item, trans, textarea=False):
    """returns a widget for viewing the given item's translation"""
    if textarea:
      escapefunction = self.escapefortextarea
    else:
      escapefunction = self.escapetext
    editlink = self.geteditlink(item)
    transdict = {"editlink": editlink}
    if len(trans) > 1:
      forms = []
      for pluralitem, pluraltext in enumerate(trans):
        form = {"title": self.localize("Plural Form %d", pluralitem), "n": pluralitem, "text": escapefunction(pluraltext)}
        forms.append(form)
      transdict["forms"] = forms
    else:
      transdict["text"] = escapefunction(trans[0])
    return transdict

