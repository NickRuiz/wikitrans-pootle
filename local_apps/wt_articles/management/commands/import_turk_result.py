from django.db.transaction import commit_on_success
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.utils.encoding import smart_str

from wt_articles.models import SourceSentence, SourceArticle, TranslatedSentence, TranslatedArticle
from wt_articles.management.commands.import_turk_source import unicode_csv_reader

import sys
import os
import csv
import re
from optparse import make_option
from datetime import datetime

try:
    set
except NameError:
    from sets import Set as set   # Python 2.3 fallback

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--source-lang', dest='source_lang',
            help='The two-letter language expression of the source language: e.g. hi'),
        make_option('--target-lang', dest='target_lang',
            help='The two-letter language expression of the target language: e.g. en'),
        make_option('--result-file', dest='result_file',
            help='The result input for Amazon: Hindi-Batch_188107_result.csv'),
    )
    help = 'Installs the named mechanical turk result files in the database.'
    args = "--source-lang <lang> --target-lang <lang> --result-file <file>"

    def handle(self, *labels, **options):
        from django.db.models import get_apps
        from django.core import serializers
        from django.db import connection, transaction
        from django.conf import settings

        self.style = no_style()

        source_lang = options.get('source_lang', None)
        target_lang = options.get('target_lang', None)
        result_file = options.get('result_file', None)
        if not source_lang:
            print 'source-lang is not specified'
            return
        elif len(source_lang) != 2:
            print 'source-lang ' + source_lang + ' is not valid'
            return
        elif not target_lang:
            print 'target-lang is not specified'
            return
        elif len(target_lang) != 2:
            print 'target-lang ' + target_lang + ' is not valid'
            return
        if not os.path.exists(result_file):
            print 'result-file does not exist'
            return

        # Generate dictionary of article id => article title
        return self.parse_result_file(result_file, source_lang, target_lang)

    @commit_on_success
    def parse_result_file(self, result_file, source_lang, target_lang):
        f = open(result_file, 'r')
        csv_reader = unicode_csv_reader(f)
        headers = csv_reader.next()
        header_map = {}
        for i,h in enumerate(headers):
            header_map[h] = i

	# not assuming a specific order for the fields
        sa = None
        cur_aid = -1
	segment_ids = [header_map[x] for x in ['Input.seg_id%d' % i for i in range(1,11)]]
	segments = [header_map[x] for x in ['Input.seg%d' % i for i in range(1,11)]]
	translations = [header_map[x] for x in ['Answer.translation%d' % i for i in range(1,11)]]
	ta = None
	has_title = 'Input.article' in header_map
        for line in csv_reader:
	    if has_title:
		title = line[header_map['Input.article']] + ' (translated)'
	    else:
		title = 'Noname (translated)'
	    approved = (line[header_map['AssignmentStatus']] == 'Approved')
	    for i in range(10):
                try:
                    (aid, seg_id) = line[segment_ids[i]].split('_')
                except ValueError:
                    # treating this basically like an eof
                    break
                
                if cur_aid != int(aid):
                    if sa:
                        # save the previous SourceArticle
                        sa.save(manually_splitting=True)
                    # check if the document is already imported
		    if not has_title:
			title = aid + ' ' + title
                    try:
                        sa = SourceArticle.objects.filter(language = source_lang).get(doc_id = aid)
                        sa.sentences_processed = True
                        cur_aid = int(aid)
                        sa.language = source_lang
                        sa.doc_id = aid 
                        sa.timestamp = datetime.now()
                        sa.title = title
                        sa.save(manually_splitting=True)
                        # get an id for the SourceArticle instance
                    except SourceArticle.DoesNotExist:
                        # make a new sa object
                        sa = SourceArticle()
                        sa.sentences_processed = True
                        cur_aid = int(aid)
                        language = source_lang
                        sa.language = language
                        sa.doc_id = aid 
                        sa.timestamp = datetime.now()
                        sa.title = title
                        sa.save(manually_splitting=True)
                        # get an id for the SourceArticle instance
		    if ta:
			# save the previous target article
			ta.save()
		    # check if the target article has been translated and imported
		    try:
			ta = TranslatedArticle.objects.filter(article = sa).get(language = target_lang)
			# if there is one, do not touch unknown fields.
			ta.title = title
			ta.timestamp = datetime.now()
			ta.language = target_lang
			ta.approved = approved
			ta.save()
		    except TranslatedArticle.DoesNotExist:
			# make a new TranslatedSentence object
			ta = TranslatedArticle()
			ta.article = sa
			ta.title = title
			ta.timestamp = datetime.now()
			ta.language = target_lang
			ta.approved = approved
			ta.save()

		end_of_paragraph = True
		tag_id = 'Input.tag%d' % i
		if tag_id in header_map:
		    tag = line[header_map[tag_id]]
		    end_of_paragraph = re.search("LastSentence", tag) or False

                seg = line[segments[i]]
                try:
		    # do not touch end_of_paragraph because we do not know
                    ss = sa.sourcesentence_set.get(segment_id = seg_id)
                    ss.text = seg
                    ss.segment_id = seg_id
		    ss.end_of_paragraph = end_of_paragraph
                    ss.save()
                except SourceSentence.DoesNotExist:
                    ss = SourceSentence()
                    ss.article = sa
                    ss.text = seg
                    ss.segment_id = seg_id
                    ss.end_of_paragraph = end_of_paragraph
                    ss.save()
                    sa.source_text += seg + u'\n'

		translation = line[translations[i]]
		try:
		    ts = ta.sentences.get(segment_id = seg_id)
		    ts.source_sentence = ss
		    ts.text = translation
		    ts.translated_by = line[header_map['WorkerId']]
		    ts.language = target_lang
		    date_string = line[header_map['SubmitTime']]
		    df = date_string.split(' ')
		    tf = df[3].split(':')
		    ts.translation_date = datetime(int(df[5]), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].index(df[1]) + 1,
						   int(df[2]), int(tf[0]), int(tf[1]), int(tf[2]))
		    ts.approved = approved
		    ts.end_of_paragraph = ss.end_of_paragraph
		    ts.save()
		except TranslatedSentence.DoesNotExist:
		    ts = TranslatedSentence()
		    ts.segment_id = seg_id
		    ts.source_sentence = ss
		    ts.text = translation
		    ts.translated_by = line[header_map['WorkerId']]
		    ts.language = target_lang
		    date_string = line[header_map['SubmitTime']]
		    df = date_string.split(' ')
		    tf = df[3].split(':')
		    ts.translation_date = datetime(int(df[5]), ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'].index(df[1]) + 1,
						   int(df[2]), int(tf[0]), int(tf[1]), int(tf[2]))
		    ts.approved = approved
		    ts.end_of_paragraph = ss.end_of_paragraph
		    ts.save()
		    ta.sentences.add(ts)
        if sa:
            sa.save(manually_splitting=True)
	if ta:
	    ta.save()
