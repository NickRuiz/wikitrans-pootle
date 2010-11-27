from goopytrans import translate as gtranslate
from apyrtium import translate as atranslate
import nltk.data

from django.utils.safestring import SafeUnicode

from wt_languages.models import TARGET_LANGUAGE, SOURCE_LANGUAGE, BOTH
from wt_languages.models import LanguageCompetancy
from wt_articles.models import SourceArticle, SourceSentence, TranslatedArticle, TranslatedSentence

from wt_articles import GOOGLE,APERTIUM
from wt_articles import MECHANICAL_TURK,HUMAN,DEFAULT_TRANNY

from wt_articles.models import ServerlandHost, MachineTranslator, LanguagePair
from pootle_language.models import Language

# Serverland integration
import xmlrpclib
import json
import pycountry

class Translator:
    """
    A container class for various translation methods
    """
    def __init__(self, name, func):
        self.name = name
        self.translate = func

    def translate(self, text, source, target):
        self.translate(text, source=source, target=target)

def google_translator():
    return Translator(GOOGLE, gtranslate)

def apertium_translator():
    return Translator(APERTIUM, atranslate)

def _group_sentences(sentences):
    p_groups = []
    prev_s = None
    for s in sentences:
        if prev_s == None or prev_s.end_of_paragraph:
            cur_list = []
            p_groups.append(cur_list)
        cur_list.append(s)
        prev_s = s
    return p_groups

def _format_sentences(sentences, fun):
    sentence_groups = _group_sentences(sentences)
    formatted = ''
    for s_list in sentence_groups:
        raw_text = [(s.text) for s in s_list]
        formatted = formatted + fun(' '.join(raw_text))
    formatted = SafeUnicode(formatted)
    return formatted

def sentences_as_text(sentences):
    format_p = lambda s: '%s\n\n' % (s)
    text = _format_sentences(sentences, format_p)
    return text

def sentences_as_html(sentences):
    format_p = lambda s: '<p>%s</p>' % (s)
    html = _format_sentences(sentences, format_p)
    return html

def sentences_as_html_span(sentences):
    format_span = lambda sid, text: u"<span id='ss_%d'>%s</span>" % (sid, text)
    # span_sentences = [ format_span(s.segment_id, s.text) for s in sentences ]
    for s in sentences:
        s.text = format_span(s.segment_id, s.text)
        
    html = sentences_as_html(sentences)
    return html

def _all_articles(article_model):
    articles = set(article_model.objects.order_by('title'))
    return articles

def all_source_articles():
    return _all_articles(SourceArticle)

def all_translated_articles():
    return _all_articles(TranslatedArticle)

def all_articles():
    source_articles = all_source_articles()
    translated_articles = all_translated_articles()
    
    return translated_articles.union(source_articles)

def _user_compatible_articles(user, article_model, language_direction):
    profile = user.get_profile()
    languages = set([lc.language for lc in
                     user.languagecompetancy_set.exclude(translation_options=language_direction)])

    languages.add(profile.native_language)
    languages.add(profile.display_language)
    
    articles = set(article_model.objects.filter(language__in=languages))
    return articles

def user_compatible_source_articles(user):
    return _user_compatible_articles(user, SourceArticle, TARGET_LANGUAGE)

def user_compatible_target_articles(user):
    return _user_compatible_articles(user, TranslatedArticle, SOURCE_LANGUAGE)

def user_compatible_articles(user):
    source_articles = user_compatible_source_articles(user)
    target_articles = user_compatible_target_articles(user)
    articles = target_articles.union(source_articles)
    return articles

def target_pairs_by_user(user, source):
    target_languages = set([lc.language for lc in
                            user.languagecompetancy_set.exclude(translation_options=SOURCE_LANGUAGE)])
    # Exclude identical source/target pairs
    target_languages.discard(source)
    
    st_pair_builder = lambda t: (t, '%s-%s' % (source, t))
    pairs = map(st_pair_builder, target_languages)
    return pairs   

def sync_serverland_host(url, token):
    '''
    Add or synchronize a remote Serverland XML-RPC host and its translators (workers).
    '''
    # First check if the host already exists
    hosts = ServerlandHost.objects.filter(url=url, token=token)
    if len(hosts) == 1:
        host = hosts[0]
    else:  
        # Create an instance of the host
        host = ServerlandHost()
        host.url = url
        host.token = token
        host.shortname = ""
        host.description = ""
    
    # Query the URL to get the rest of the host information.
    proxy = xmlrpclib.ServerProxy(host.url)
    workers = proxy.list_workers(host.token)
    
    # A query against the host succeeded, so save the host instance.
    host.save()
    
    # Force JSON/Dict result to a list.
    if not isinstance(workers, list):
        workers = [workers]
    
    # Fetch each worker and store it.
    for i in range(0, len(workers)):  
        # Check if the worker already exists in the database
        mts = host.translators.filter(shortname = workers[i]['shortname'])
        if len(mts) == 1:
            # Worker already exists
            mt = mts[0]
        else:
            mt = MachineTranslator()
            mt.shortname = workers[i]['shortname']
            
        mt.description = workers[i]['description']
        mt.is_alive = workers[i]['is_alive']
        mt.save()
        
        # Add the language pairs
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
                
            except KeyError:
                # Just continue if the language doesn't exist.
                continue
            except Language.DoesNotExist:
                # Just Continue if the language doesn't exist.
                # TODO: Should we automatically add languages? 
                continue
                
        host.translators.add(mt)
    
    return host

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