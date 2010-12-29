from django.db import models
from django.utils.translation import ugettext_lazy as _
from django.utils.encoding import iri_to_uri
from django.conf import settings
from django.contrib.auth.models import User
from datetime import datetime

from pootle_language.models import Language

from wt_translation import TRANSLATOR_TYPES, SERVERLAND

# Serverland integration
import xmlrpclib
import json
import pycountry
import errno

# TODO: Do I need this?   
class LanguagePair(models.Model):
    source_language = models.ForeignKey(Language, related_name="source_language_ref")
    target_language = models.ForeignKey(Language, related_name="target_language_ref")
    
    def __unicode__(self):
        return u"%s :: %s" % (self.source_language.code, self.target_language.code)
    
    class Meta:
        unique_together = (("source_language", "target_language"),)

# Get or create a language pair
def get_or_create_language_pair(l1, l2):
    try:
        # Try to get the language pair
        language_pair = LanguagePair.objects.filter(source_language = l1, target_language = l2)[0]
    except (LanguagePair.DoesNotExist, IndexError):
        # The language pair doesn't exist. Create it.
        language_pair = LanguagePair()
        language_pair.source_language = l1
        language_pair.target_language = l2
        language_pair.save()
        
    return language_pair

class MachineTranslator(models.Model):
    shortname = models.CharField(_('Name'), max_length=50)
    supported_languages = models.ManyToManyField(LanguagePair)
    description = models.TextField(_('Description'))
    type = models.CharField(_('Type'), max_length=32, choices=TRANSLATOR_TYPES, default='Serverland'),
    timestamp = models.DateTimeField(_('Refresh Date'), default=datetime.now())
    is_alive = models.BooleanField()
    
    def __unicode__(self):
        return u"%s :: %s" % (self.shortname, self.timestamp)
    
    def is_language_pair_supported(self, source_language, target_language):
        return self.supported_languages.filter(source_language = source_language, 
                                               target_language = target_language).exists()
    
class ServerlandHost(models.Model):
    shortname = models.CharField(_('Short Name'), max_length=100)
    description = models.TextField(_('Description'))
    url = models.URLField(_('URL Location'), verify_exists=True, max_length=255, unique=True)
    token = models.CharField(_('Auth Token'), max_length=8)
    timestamp = models.DateTimeField(_('Refresh Date'), default=datetime.now())
    
    translators = models.ManyToManyField(MachineTranslator)
    
    def __unicode__(self):
        return u"%s" % (self.url)
    
    def save(self):
        super(ServerlandHost, self).save()
        
        try:
            self.sync()
        except Exception:
            self.delete()
            raise 
    
    def sync(self):
        '''
        Add or synchronize a remote Serverland XML-RPC host and its translators (workers).
        '''      
        from wt_articles import utils
          
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
                    
                mt.description = workers[i]['description']
                mt.is_alive = workers[i]['is_alive']
                mt.save()
                
                # If alive, then add the language pairs
                if mt.is_alive:
                    for language_pair in workers[i]['language_pairs']:
                        try:
                            # Get the ISO639-1 format
                            language_code1 = pycountry.languages.get(terminology=language_pair[0]).alpha2
                            language_code2 = pycountry.languages.get(terminology=language_pair[1]).alpha2
                            
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
        except EnvironmentError as ex:
            if ex.errno == errno.ECONNREFUSED:
                # Connection not available.
                raise RuntimeError("Unable to connect to remote server at %s") % self.url
        except xmlrpclib.Fault as ex:
            if ex.faultCode == 1:
                raise ServerlandConfigError(self)
            
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
    def __init__(self, value):
        self.value = value
        
    def __str__(self):
        return repr(self.value)
    
class ServerlandConfigError(TranslatorConfigError):
    def __init__(self, value):
        if isinstance(value, ServerlandHost):
            self.value = "Invalid authentication token %s for Serverland host at %s." % (value.token, value.url)
        else:
            super(TranslatorsConfigError, self).__init__(value)
    
def request_translation(translator, sentences, source_language, target_language):
    """
    Request a MachineTranslator to perform a translation.
    Preconditions:
        translator:    A MachineTranslator object.
        sentences:     A list of strings.
    Exceptions:
        UnsupportedLanguagePair:The target translator doesn't support the language pair.
        UndefinedTranslator:    When looking up the ServerlandHost for a MachineTranslator, if none exists (this should not happen).
    """
    
    # Make sure that the translator supports the language pair
    if not translator.is_language_pair_supported(source_language, target_language):
        raise UnsupportedLanguagePair(translator, source_language, target_language)
    
    # Create a request id
    request_id = utils.generate_request_id()
    
    # Make sure that there is more than one sentence.
    if not isinstance(sentences, list):
        print "Retrieved only one result"
        sentences = [sentences]
    
    text = "\n".join(sentence for sentence in sentences)
        
    # Determine the machine translator type.
    if translator.type == SERVERLAND:
        # Get the ServerlandHost
        try:
            serverland_host = translator.serverlandhost_set.all()[0]
        except IndexError:
            raise UndefinedTranslator(translator)
        
        source_file_id = "%s-%s-%s" % (request_id, source_language.code, target_language.code)
        
        try:
            # Request the translation.
            proxy = xmlrpclib.ServerProxy(serverland_host.url)
            proxy.create_translation(token, 
                                     request_id, 
                                     translator.shortname,
                                     source_language,
                                     target_language,
                                     source_file_id,
                                     text)
        except xmlrpclib.Fault as ex:
            if ex.faultCode == 1:
                raise ServerlandConfigError(self)