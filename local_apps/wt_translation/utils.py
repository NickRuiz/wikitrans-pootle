import pycountry
import uuid
from BeautifulSoup import BeautifulStoneSoup

from pootle_language.models import Language 

def get_iso639_2(language):
    """
    Gets the iso-639-2 language format.
    """
    # TODO: Need to handle the case where a language isn't valid.
    # print "Language:", language
    
    language_length = len(language)
    
    if language_length == 2:
        return pycountry.languages.get(alpha2=language).bibliographic
    elif language_length == 3:
        return language
    else:
        # TODO: Add exception handling if the language locale doesn't exist
        return ''
    
def generate_request_id():
    return uuid.uuid1().hex

def cast_to_list(input):
    """
    If the input isn't a list, cast it to a list
    """
    if not isinstance(input, list):
        input = [input]
        
    return input

def clean_string(input):
    return BeautifulStoneSoup(input, convertEntities=BeautifulStoneSoup.ALL_ENTITIES).contents[0]