from django import forms
from django.forms.formsets import formset_factory
from django.db.models import Q

from wt_translation.models import MachineTranslator, LanguagePair, ServerlandHost, TranslationRequest
from pootle_language.models import Language

#class MachineTranslatorSelectorForm(forms.Form):
#    """
#    A custom form used to select a machine translator to translate a language pair.
#    """
#    def __init__(self, source_language, target_language, *args, **kwargs):
#        self.source_language = source_language
#        self.target_language = target_language
#        
#        # Call the parent constructor
#        super(MachineTranslatorSelectorForm, self).__init__(*args, **kwargs)
#        self.fields['translators'].queryset = MachineTranslator.objects.filter(
#                            supported_languages__source_language = source_language,
#                            supported_languages__target_language = target_language                                                   
#                        )
#        
#    translators = forms.ModelMultipleChoiceField(_("Translators"))
    
class TranslationRequestForm(forms.ModelForm):
    def __init__(self, translation_project=None, *args, **kwargs):
        super(TranslationRequestForm, self).__init__(*args, **kwargs)
        
        if translation_project != None:
            self.translation_project = translation_project
            
            self.fields['translator'].queryset = MachineTranslator.objects.filter(supported_languages__in = 
                            LanguagePair.objects.filter(
                                Q(source_language=translation_project.project.source_language), 
                                Q(target_language=translation_project.language)
                            ))
        
    class Meta:
        model = TranslationRequest
        exclude = ('status', 'external_id', 'timestamp',)