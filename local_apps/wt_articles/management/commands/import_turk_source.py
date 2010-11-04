from django.db.transaction import commit_on_success
from django.core.management.base import BaseCommand
from django.core.management.color import no_style
from django.utils.encoding import smart_str

from wt_articles.models import SourceSentence, SourceArticle

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

def unicode_csv_reader(unicode_csv_data, dialect=csv.excel, **kwargs):
    # Borrowed from Python v.2.6.5 Documentation >> ... >> 13.1 csv
    # csv.py doesn't do Unicode; encode temporarily as UTF-8:
    csv_reader = csv.reader(unicode_csv_data,
                            dialect=dialect, **kwargs)
    for row in csv_reader:
        # decode UTF-8 back to Unicode, cell by cell:
        yield [unicode(cell, 'utf-8') for cell in row]

class Command(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--articles-file', dest='articles_file',
            help='File containing article titles: hi_articles'),
        make_option('--ids-file', dest='ids_file', 
            help='File containing article ids: hi_articles.ids'),
        make_option('--source-file', dest='source_file',
            help='The source input for Amazon: hindi_wikipedia_feature_article_to_translate-2010-02-13T1051.csv'),
    )
    help = 'Installs the named mechanical turk output files in the database.'
    args = "--articles-file <file> --ids-file <file> --source-file <file>"

    def handle(self, *labels, **options):
        from django.db.models import get_apps
        from django.core import serializers
        from django.db import connection, transaction
        from django.conf import settings

        self.style = no_style()

        articles_file = options.get('articles_file', None)
        ids_file = options.get('ids_file', None)
        source_file = options.get('source_file', None)
        if not os.path.exists(articles_file):
            print 'articles-file does not exist'
            return
        if not os.path.exists(ids_file):
            print 'ids-file does not exist'
            return
        if not os.path.exists(source_file):
            print 'source-file does not exist'
            return

        # Generate dictionary of article id => article title
        article_names = self.parse_articles_file(articles_file)
        article_ids = self.parse_ids_file(ids_file)
        article_id_map = {}
        for name, aid in zip(article_names, article_ids):
            article_id_map[aid.strip()] = name.strip()

        return self.parse_source_file(source_file, article_id_map)

    def parse_articles_file(self, articles_file):
        f = open(articles_file, 'r')
        return [unicode(title,'utf-8') for title in f.readlines()]

    def parse_ids_file(self, ids_file):
        f = open(ids_file, 'r')
        return f.readlines()

    @commit_on_success
    def parse_source_file(self, source_file, article_id_map):
        f = open(source_file, 'r')
        csv_reader = unicode_csv_reader(f)
        headers = csv_reader.next()
        header_map = {}
        for i,h in enumerate(headers):
            header_map[h] = i

        # The headers are uniform in this file
        # lang,(seg_id1,tag1,seg1,img_url1,machine_translation1),...,(seg_idn,...)
        sa = None
        cur_aid = -1
        language = None
        segments = ['seg_id%s' % i for i in xrange(1,11)]
        for i,line in enumerate(csv_reader):
            segment_offsets = [(header_map[seg]) for seg in segments]
            for offs in segment_offsets:
                try:
                    (aid, seg_id) = line[offs].split('_')
                except IndexError:
                    # treating this basically like an eof
                    break
                
                if cur_aid != int(aid):
                    if sa:
                        # save the previous SourceArticle
                        sa.save(manually_splitting=True)
                    # check if the document is already imported
                    try:
                        sa = SourceArticle.objects.filter(language = line[0]).get(doc_id = aid)
                        sa.sentences_processed = True
                        cur_aid = int(aid)
                        language = line[0]
                        sa.language = language
                        sa.doc_id = aid 
                        sa.timestamp = datetime.now()
                        sa.title = article_id_map[aid]
                        sa.save(manually_splitting=True)
                        # get an id for the SourceArticle instance
                    except SourceArticle.DoesNotExist:
                        # make a new sa object
                        sa = SourceArticle()
                        sa.sentences_processed = True
                        cur_aid = int(aid)
                        language = line[0]
                        sa.language = language
                        sa.doc_id = aid 
                        sa.timestamp = datetime.now()
                        sa.title = article_id_map[aid]
                        sa.save(manually_splitting=True)
                        # get an id for the SourceArticle instance

                tag = line[(offs + 1)]
                seg = line[(offs + 2)]

                try:
                    ss = sa.sourcesentence_set.get(segment_id = seg_id)
                    ss.text = seg
                    ss.segment_id = seg_id
                    ss.end_of_paragraph = re.search("LastSentence", tag) or False
                    ss.save()
                except SourceSentence.DoesNotExist:
                    ss = SourceSentence()
                    ss.article = sa
                    ss.text = seg
                    ss.segment_id = seg_id
                    ss.end_of_paragraph = re.search("LastSentence", tag) or False
                    ss.save()
                    sa.source_text += seg + u'\n'
                
        if sa:
            sa.save(manually_splitting=True)
