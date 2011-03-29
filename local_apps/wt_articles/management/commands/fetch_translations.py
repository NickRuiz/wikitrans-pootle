from django.core.management.base import NoArgsCommand, CommandError
from django.conf import settings

#from wt_articles.models import ArticleOfInterest, SourceArticle, TranslationRequest
from wt_translation.models import ServerlandHost
from wt_translation.models import UnsupportedLanguagePair, UndefinedTranslator, ServerlandConfigError
#
#from pootle_project.models import Project
#from pootle_translationproject.models import TranslationProject
#from pootle_language.models import Language
#
#import xmlrpclib
#import json

class Command(NoArgsCommand):
    help = "Looks for completed translation requests from all Serverland hosts and updates their corresponding .po files."
    
    def handle_error(self, host, error):
        print "An error occurred with Serverland host '%s' (%s):" % (host.shortname, host.url)
        print error #.exc_info()
        
    def handle_noargs(self, **options):
        # Fetch all of the hosts
        hosts = ServerlandHost.objects.all()
        
        for host in hosts:
            try:
                self.host.fetch_translations()
            except UnsupportedLanguagePair as ex:
                self.handle_error(host, ex)
            except UndefinedTranslator as ex:
                self.handle_error(host, ex)
            except ServerlandConfigError as ex:
                self.handle_error(host, ex)
            except Exception as ex:
                self.handle_error(host, ex)

#        token = settings.SERVERLAND_TOKEN
#        
#        print "Using token " + token
#        print "xmlrpclib.ServerProxy(%s)" % settings.SERVERLAND_XMLRPC
#        proxy = xmlrpclib.ServerProxy(settings.SERVERLAND_XMLRPC)
#        print "Connected!"
#        
#        # Fetch a list of the serverland workers
#        # for worker in proxy.list_workers(token):
#        #    workerName = worker['shortname']
#            
#        # Check serverland for completed translations
#        print "proxy.list_requests('%s')" % token
#        requests = proxy.list_requests(token)
#        
#        print "Call finished"
#        # If only one result is retrieved, the dict is not in a list
#        if not isinstance(requests, list):
#            print "Retrieved only one result"
#            requests = [requests]
#        else:
#            print "Retrieved multiple results"
#        
#        # Display the translation requests that are "ready"
#        completedRequests = [request for request in requests if request['ready']]
#        
#        print "Showing the completed requests"
#        # Process the completed requests
#        for completedRequest in completedRequests:
#            # Get the result
#            result = proxy.list_results(token, completedRequest['request_id'])
#            
#            # TODO: Save the result
#            print result['shortname'], result['request_id']
#            print result['result']
#            
#            # TODO: Delete the request
#            # proxy.delete_translation(completedRequest['request_id'])
        