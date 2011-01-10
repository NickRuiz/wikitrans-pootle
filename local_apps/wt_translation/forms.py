from django import forms
from django.forms.formsets import formset_factory
from django.db.models import Q

from wt_translation.models import MachineTranslator, LanguagePair, ServerlandHost
from pootle_language.models import Language

class MachineTranslatorSelectorForm(forms.ModelForm):
    """
    A custom form used to select a machine translator to translate a language pair.
    """
    def __init__(self, source_language, target_language, *args, **kwargs):
        self.source_language = source_language
        self.target_language = target_langauge
        
        # Call the parent constructor
        super(MachineTranslatorSelectorForm, self).__init__(*args, **kwargs)
        self.fields['translators'].queryset = MachineTranslator.objects.filter(
                            supported_languages__source_language = source_language,
                            supported_languages__target_language = target_language                                                   
                        )
        
        translators = forms.ModelMultipleChoiceField(_("Translators"))