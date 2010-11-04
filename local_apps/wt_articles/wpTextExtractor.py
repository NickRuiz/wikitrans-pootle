#! /usr/bin/env python2.6
# -*- coding: utf-8 -*-

__author__ = 'Andreas Eisele <eisele@dfki.de>'
__created__ = "Tue Jan 26 21:41:40 2010"

'''
extract clear text from wikipedia articles
'''


import re
import mwlib
from mwlib.refine.compat import parse_txt
from mwlib.refine import core
from mwlib.parser import nodes


# map all node types to the empty string
nodeTypes = [getattr(nodes,d) for d in dir(nodes)]
nodeTypes = [x for x in nodeTypes if type(x)==type]
node2markup = dict((n,'') for n in nodeTypes)
# except for those
node2markup[nodes.Section]='<s>'
node2markup[nodes.Item]='<i>'

def wiki2sentences(wiki, sent_detector,withTags=True):
    # get rid of (nested) template calls
    oldLen = 1E10
    while len(wiki)<oldLen:
        oldLen = len(wiki)
        wiki = re.sub('{[^{}]*}',' ',wiki)

    tree = parse_txt(wiki)
    text = tree2string(tree)
    lines = cleanup(text).split('\n')
    sentences = []
    tags = []
    for line in lines:
        if line.startswith('<s>'):
            sentences.append(line[3:].strip())
            tags.append('Section')
        elif line.startswith('<i>'):
            sentences.append(line[3:].strip())
            tags.append('Item')
        else:
            newSentences = sent_detector(line.strip())
            sentences += newSentences
            tags += ['Sentence']*(len(newSentences)-1)
            tags.append('LastSentence')
    if withTags:
        return sentences,tags
    else:
        return sentences



def tree2string(tree,trace=False):
    snippets = []
    _tree2string(tree,snippets,trace)
    return ''.join(snippets)

def _tree2string(tree,snippets,trace,level=0):
    snippets.append(node2markup[type(tree)])
    if trace: print ' '*level,type(tree)
    try:
        if type(tree)==nodes.ArticleLink:
            if not tree.children:
                if tree.text:
                    snippets.append(tree.text)
                else:
                    snippets.append(tree.target)
                if trace:
                    print ' '*level,'ArticleLink: children:',len(tree.children)
                    print ' '*level,'target',tree.target.encode('utf-8')
                    print ' '*level,'text:',tree.text.encode('utf-8')
                return
        elif type(tree)==nodes.TagNode:
            return
        elif tree.text:
            if trace: print ' '*level,'text:',tree.text.encode('utf-8')
            snippets.append(tree.text)
    except AttributeError: pass
    try:
        for node in tree.children:
            _tree2string(node,snippets,trace,level+1)
    except AttributeError: pass

def cleanup(text):
    # little hack to change the order of
    text = text.replace('."','".')
    
    #strip empty lines
    text = [x.strip() for x in text.split('\n')]
    text = [x for x in text if x and x not in '<i><s>']
    text = '\n'.join(text)

    return text