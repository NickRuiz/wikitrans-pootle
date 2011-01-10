from django.core.management.base import NoArgsCommand, CommandError
from django.conf import settings
from django.utils.encoding import smart_str

from wt_articles import TRANSLATORS, TRANSLATION_STATUSES, PENDING, IN_PROGRESS, FINISHED
from wt_articles.models import ArticleOfInterest, SourceArticle, TranslationRequest
from pootle_project.models import Project
from pootle_translationproject.models import TranslationProject
from pootle_language.models import Language

import xmlrpclib
import json
import pycountry

class Command(NoArgsCommand):
    help = "Initiates translation requests for every untranslated article request."
    
    def get_iso639_2(self, language):
        """
        Gets the iso-639-2 language format.
        """
        # TODO: Need to handle the case where a language isn't valid.
        print "Language:", language
        
        language_length = len(language)
        
        if language_length == 2:
            return pycountry.languages.get(alpha2=language).bibliographic
        elif language_length == 3:
            return language
        else:
            # TODO: Add exception handling if the language locale doesn't exist
            return ''
            
    
    def handle_noargs(self, **options):
        # Initiate the XML-RPC connection
        token = settings.SERVERLAND_TOKEN
        
        print "Using token " + token
        print "Establishing connection to %s" % settings.SERVERLAND_XMLRPC
        proxy = xmlrpclib.ServerProxy(settings.SERVERLAND_XMLRPC, encoding='UTF-8', verbose=True)
        print "Connected!"
        
        # Get the pending translations
        print("pendingRequests = TranslationRequest.objects.filter(status=%s)" % PENDING)
        pendingRequests = TranslationRequest.objects.filter(status=PENDING)
        
        # Initiate a serverland request for each pending translation request
        for request in pendingRequests:
            source_language = self.get_iso639_2(request.article.language)
            
            # TODO: Fix target_language
            target_language = '' #self.get_iso639_2(request.target_language)
            request_id = "%s-%s-%s" % (request.article.doc_id, source_language, target_language)
            worker = request.get_translator_display()
            source_file_id = request_id
            # TODO: Use the .po file, not SourceArticle.sentences_to_lines()!
            source_text = request.article.sentences_to_lines()
            
            print source_language, target_language, request_id
            print worker, source_file_id, source_text
            
            # Send the request
            proxy.create_translation(token, 
                                     '1010', # request_id, 
                                     worker,
                                     source_language,
                                     target_language,
                                     source_file_id,
                                     'This is a test.')
                                     # source_text)
                                     #xmlrpclib.Binary(source_text))
            
            # Look at the results
            print 'Finished'
            
            # If the results are good, update the status of the TranslationRequest.
            request.status = IN_PROGRESS
            request.save()
            
            # For now, just try submitting one translation request.
            break