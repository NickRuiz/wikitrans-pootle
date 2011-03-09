from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import iri_to_uri
from django.conf import settings
from django.contrib.auth.models import User
from datetime import datetime

from pootle_language.models import Language
from pootle_translationproject.models import TranslationProject
from pootle_store.models import Store, Unit, Suggestion

from wt_translation import TRANSLATOR_TYPES, SERVERLAND
from wt_translation import TRANSLATION_STATUSES, STATUS_PENDING, STATUS_IN_PROGRESS, STATUS_FINISHED, STATUS_ERROR, STATUS_CANCELLED
from wt_translation import SERVERLAND_HOST_STATUSES, OK, INVALID_URL, INVALID_TOKEN, UNAVAILABLE, MISCONFIGURED_HOST
import utils

import re

# Serverland integration
import xmlrpclib
import json
import pycountry
import errno

class LanguagePairManager(models.Manager):
    def get_by_natural_key(self, source_language, target_language):
        return LanguagePair.objects.get(source_language=source_language, target_language=target_language)
    
# TODO: Do I need this?   
class LanguagePair(models.Model):
    source_language = models.ForeignKey(Language, related_name="source_language_ref")
    target_language = models.ForeignKey(Language, related_name="target_language_ref")
    
    objects = LanguagePairManager()
    
    def __unicode__(self):
        return u"%s :: %s" % (self.source_language.code, self.target_language.code)
    
    class Meta:
        unique_together = (("source_language", "target_language"),)

# Get or create a language pair
def get_or_create_language_pair(source_language, target_language):
    try:
        # Try to get the language pair
        language_pair = LanguagePair.objects.get_by_natural_key(source_language, target_language)
#        language_pair = LanguagePair.objects.filter(source_language = source_language, target_language = target_language)[0]
    except (LanguagePair.DoesNotExist, IndexError):
        # The language pair doesn't exist. Create it.
        language_pair = LanguagePair()
        language_pair.source_language = source_language
        language_pair.target_language = target_language
        language_pair.save()
        
    return language_pair

class MachineTranslator(models.Model):
    shortname = models.CharField(_('Name'), max_length=50)
    supported_languages = models.ManyToManyField(LanguagePair)
    description = models.TextField(_('Description'))
    type = models.CharField(_('Type'), max_length=32, choices=TRANSLATOR_TYPES, default='Serverland')
    timestamp = models.DateTimeField(_('Refresh Date'), default=datetime.now())
    
    def __unicode__(self):
        return u"%s :: %s" % (self.shortname, self.timestamp)
    
    def is_language_pair_supported(self, source_language, target_language):
        return self.supported_languages.filter(source_language = source_language, 
                                               target_language = target_language).exists()
                                               
    def create_translation_request(self, translation_project):
        '''
        Creates a translation request
        '''
        request = TranslationRequest()
        request.translator = self
        request.translation_project = translation_project
        request.save()
        
        return request
    
    @staticmethod                                           
    def get_eligible_translators(source_language, target_language):
        """
        Get a list of translators that can be used to translate this language pair.
        """
        return MachineTranslator.objects.filter(
                                supported_languages__source_language = source_language,
                                supported_languages__target_language = target_language                                                   
                            )
                                               
class ServerlandHost(models.Model):
    shortname = models.CharField(_('Short Name'), max_length=100)
    description = models.TextField(_('Description'))
    url = models.URLField(_('URL Location'), verify_exists=True, max_length=255, unique=True)
    token = models.CharField(_('Auth Token'), max_length=8)
    timestamp = models.DateTimeField(_('Refresh Date'), default=datetime.now())
    status = models.CharField(_('Status'), max_length=1, choices=SERVERLAND_HOST_STATUSES, editable=False)
    
    translators = models.ManyToManyField(MachineTranslator)
    
    def __unicode__(self):
        return u"%s" % (self.url)
    
    def save(self):      
        # Perform an initial sync if a new host is created.
        if self.id is None:
            super(ServerlandHost, self).save()
            try:
                self.sync()
            except Exception:
                # TODO: Should the host be deleted if it's invalid, or should it be left in an invalid state?
                # TODO: For now, sync() will put the host in an invalid state.
                # self.delete()
                raise 
        else:
            # Update the timestamp
            self.timestamp = datetime.now()
            super(ServerlandHost, self).save()
    
    def sync(self):
        '''
        Add or synchronize a remote Serverland XML-RPC host and its translators (workers).
        '''                
        try:
            # Query the URL to get the rest of the host information.
            proxy = xmlrpclib.ServerProxy(self.url)
            workers = proxy.list_workers(self.token)
            
            # Force JSON/Dict result to a list.
            if not isinstance(workers, list):
                workers = [workers]
            
            # Fetch each worker and store it.
            for i in range(0, len(workers)):  
                # Check if the worker already exists in the database
                mts = self.translators.filter(shortname = workers[i]['shortname'])
                if len(mts) == 1:
                    # Worker already exists
                    mt = mts[0]
                else:
                    mt = MachineTranslator()
                    mt.shortname = workers[i]['shortname']
                    mt.type = SERVERLAND
                    
                mt.description = workers[i]['description']
                mt.is_alive = workers[i]['is_alive']
                mt.save()
                
                # If alive, then add the language pairs
                if mt.is_alive:
                    for language_pair in workers[i]['language_pairs']:
                        try:
                            # Get the ISO639-1 format
                            language_code1 = pycountry.languages.get(bibliographic=language_pair[0]).alpha2
                            language_code2 = pycountry.languages.get(bibliographic=language_pair[1]).alpha2
                            
                            # Find the corresponding Pootle languages
                            l1 = Language.objects.get_by_natural_key(language_code1)
                            l2 = Language.objects.get_by_natural_key(language_code2)
                            
                            # If the 2 languages exist in Pootle, add the translation pair to the MachineTranslator
                            language_pair = get_or_create_language_pair(l1, l2)
                            
                            # Add the language pair for the current translator, if it doesn't already exist.
                            if len(mt.supported_languages.filter(source_language = l1, target_language = l2)) == 0:
                                mt.supported_languages.add(language_pair)
                            
                            # TODO: What about languages that used to be supported by the translator? Should they be deleted?
                            
                        except (KeyError, AttributeError):
                            # Just continue if the language doesn't exist.
                            continue
                        except Language.DoesNotExist:
                            # Just Continue if the language doesn't exist.
                            # TODO: Should we automatically add languages? 
                            continue
                        
                self.translators.add(mt)
                self.status = OK
                self.save()
        except EnvironmentError as ex:
            raise ServerlandConfigError(self, ex)
        except xmlrpclib.Fault as ex:
            raise ServerlandConfigError(self, ex)
        except xmlrpclib.ProtocolError as ex:
            raise ServerlandConfigError(self, ex)
    
    def fetch_translations(self):
        proxy = xmlrpclib.ServerProxy(self.url)
        
        # Fetch the translation requests (and make sure the result is a list)
        requests = utils.cast_to_list(proxy.list_requests(self.token))
        
        # Retrieve the translation requests that are "ready"
        completedRequests = [request for request in requests if request['ready']]
        
        # Process the completed requests
        for completedRequest in completedRequests:
            # Get the result
            result = proxy.list_results(self.token, completedRequest['request_id'])
            
            # TODO: Save the result
            print result['shortname'], result['request_id']
            print result['result']
            
            # Get the external request id and sentences
            external_request_id = completedRequest['shortname']
            result_sentences = result['result'].split('\n')
            
            # FIXME: Add exception handling when the translation request is not found.
            try:
                # Look up the original translation request
                request = TranslationRequest.objects.get_by_external_id(external_request_id)
                
                # Fetch the Pootle store for the corresponding translation project and fill in the translations.
                store = Store.objects.get(translation_project = request.translation_project)
                
                # Get all of the units
                units = store.unit_set.all()
                
                # Make sure that len(units) matches len(result)
                
                
            except DoesNotExist as ex:
                pass
            
            # Get all of the sentences; store.unit_set.all() returns the sentences in order.
            sentences = [unicode(unit) for unit in store.unit_set.all()]
 
class TranslationRequestManager(models.Manager):
    def get_by_external_id(self, external_id):
        return TranslationRequest.objects.get(external_id = external_id)
       
class TranslationRequest(models.Model):
    translation_project = models.ForeignKey(TranslationProject)
    translator = models.ForeignKey(MachineTranslator, related_name='requested_translator')
    status = models.CharField(_('Request Status'),
                              max_length=32,
                              choices=TRANSLATION_STATUSES,
                              default = STATUS_PENDING)
    external_id = models.CharField(_('External ID'), max_length=32, editable=False, null=True) 
    timestamp = models.DateTimeField(_('Last Updated'), default=datetime.now())
    
    objects = TranslationRequestManager()
    
    class Meta:
        unique_together = ("translation_project", "translator")
        
    def __unicode__(self):
        return u"%s - %s" % (self.translator.shortname, self.translation_project)
    
    def save(self):
        # Last step, call the normal save method
        super(TranslationRequest, self).save()

def send_translation_requests(request_status=STATUS_PENDING):
    '''
    Requests a batch of machine translation requests.
    '''
    pending_requests = TranslationRequest.objects.filter(status = request_status)
    for request in pending_requests:
        # Get the .po store for the file to be translated.
        store = Store.objects.get(translation_project = request.translation_project)
        
        # Get all of the sentences; store.unit_set.all() returns the sentences in order.
        sentences = [unicode(unit) for unit in store.unit_set.all()]
        
        # Request the translation
        external_request_id = request_translation(request.translator, 
                                sentences, 
                                request.translation_project.project.source_language, 
                                request.translation_project.language)
        
        # Update the status of the record
        request.external_id = external_request_id
        request.status = STATUS_IN_PROGRESS
        request.save()
            
class UndefinedTranslator(Exception):
    def __init__(self, value):
        if isinstance(value, MachineTranslator):
            self.value = "Machine Translator %s is not completely defined." % value
        else:
            self.value = "This Machine Translator is undefined. %s" % value
    def __str__(self):
        return repr(self.value)
    
class UnsupportedLanguagePair(Exception):
    def __init__(self, translator, source_language, target_language):
        self.value = "Machine Translator %s does not support the language pair (%s, %s)." % (translator, source_language.code, target_language.code)
    
    def __str__(self):
        return repr(self.value)
    
class TranslatorConfigError(Exception):
    def __init__(self, msg):
        self.msg = msg
        
    def __str__(self):
        return repr(self.msg)
    
class ServerlandConfigError(TranslatorConfigError):
    def __init__(self, host, error):
        
        self.errorCode = UNAVAILABLE
        
        if isinstance(host, ServerlandHost):
            # Inspect the XML-RPC error type. It can either be a Fault or a ProtocolError
            if isinstance(error, xmlrpclib.ProtocolError):
                self.errorCode = INVALID_URL
                self.msg = "Invalid Serverland host URL: '%s'." % host.url 
            elif isinstance(error, xmlrpclib.Fault):
                # Inspect the faultCode and faultString to determine the error
                if re.search("[Errno 111] Connection refused", error.faultString) != None:
                    self.errorCode = INVALID_TOKEN
                    self.msg = "Invalid authentication token for Serverland host '%s'." % host.shortname 
                elif re.search("[Errno 111] Connection refused", error.faultString) != None:
                    self.errorCode = UNAVAILABLE
                elif re.search("takes exactly \d+ arguments", error.faultString) != None:
                    self.errorCode = MISCONFIGURED_HOST
                    self.msg = "Serverland host '%s' is misconfigured." % host.shortname
                else:
                    self.msg = error.faultString
            
#            if self.errorCode == UNAVAILABLE:
#                self.msg = "Serverland host '%s' is unavailable." % host.shortname
            
            # TODO: Should updating the ServerlandHost instance go here? And if the host is unavailable, should we update the status as such? For now, assume yes.
            host.status = self.errorCode
            host.save()
        else:
            super(TranslatorsConfigError, self).__init__(host)
    
def request_translation(translator, sentences, source_language, target_language):
    """
    Request a MachineTranslator to perform a translation. The request process is implemented
    based on the type of MachineTranslator. For example, a SERVERLAND type uses a MT Server Land
    to request a translation.
    Preconditions:
        translator:    A MachineTranslator object.
        sentences:     A list of strings.
    Exceptions:
        UnsupportedLanguagePair:The target translator doesn't support the language pair.
        UndefinedTranslator:    When looking up the ServerlandHost for a MachineTranslator, if none exists (this should not happen).
        ServerlandConfigError:  The ServerlandHost has an error.
    """
    
    # Make sure that the translator supports the language pair
    if not translator.is_language_pair_supported(source_language, target_language):
        raise UnsupportedLanguagePair(translator, source_language, target_language)
    
    # Generate a request id
    request_id = utils.generate_request_id()
    
    # Make sure that sentences is a list.
    sentences = utils.cast_to_list(sentences)
#    if not isinstance(sentences, list):
#        print "Retrieved only one sentence."
#        sentences = [sentences]
    
    # One sentence per line, to make it easier for the translator to do its job.
    text = "\n".join(sentence for sentence in sentences)
        
    # Determine the machine translator type.
    if translator.type == SERVERLAND:
        # Get the ServerlandHost
        try:
            # TODO: Change this host reference. Currently, only one ServerLand host is allowed.
            serverland_host = translator.serverlandhost_set.all()[0]
        except IndexError:
            raise UndefinedTranslator(translator)
        
        source_file_id = "%s-%s-%s" % (request_id, source_language.code, target_language.code)
        
        try:
#            print "Requesting the translation"
#            print serverland_host.token, request_id, translator.shortname
#            print utils.get_iso639_2(source_language.code), utils.get_iso639_2(target_language.code)
#            print source_file_id
#            print text
            
            # Request the translation.
            proxy = xmlrpclib.ServerProxy(serverland_host.url)
            result = proxy.create_translation(serverland_host.token,            # Authentication token
                                     request_id,                                # Custom request ID
                                     translator.shortname,                      # MT ServerLand worker
                                     utils.get_iso639_2(source_language.code),  # Source language (in bibliographic)
                                     utils.get_iso639_2(target_language.code),  # Target language (in bibliographic)
                                     source_file_id,                            # Composite id
                                     text)                                      # Sentence(s) to translate
            
            # TODO: For now, just print the results.
            print result
            
            # TODO: Return the request_id
            return request_id
        except xmlrpclib.Fault as ex:
            raise ServerlandConfigError(serverland_host, ex)