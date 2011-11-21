from datetime import datetime
from django import forms
from django.utils.translation import ugettext_lazy as _
from django.db.models import Q

from wt_articles.models import SourceArticle, SourceSentence, TranslatedSentence
from wt_articles.models import TranslatedArticle,ArticleOfInterest
from wt_articles import DEFAULT_TRANNY
from django.forms.formsets import formset_factory
from pootle_language.models import Language

class TranslatedSentenceMappingForm(forms.ModelForm):
    source_sentence = forms.ModelChoiceField(SourceSentence.objects.all(),
                                             widget=forms.HiddenInput())
    text = forms.CharField(widget=forms.Textarea())

    class Meta:
        model = TranslatedSentence
        exclude = ('segment_id','translated_by','language',
                   'translation_date','best','end_of_paragraph')

    def __init__(self, user=None, *args, **kwargs):
        self.user = user
        super(TranslatedSentenceMappingForm, self).__init__(*args, **kwargs)


class ArticleRequestForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super(ArticleRequestForm, self).__init__(*args, **kwargs)
        
        # Make sure the user can't request an article with the "templates" language
        self.fields['title_language'].queryset = Language.objects.exclude(code = "templates")
    class Meta:
        model = ArticleOfInterest
        
#class FixArticleForm(forms.ModelForm):
#    sentences = forms.CharField(widget=forms.Textarea())
#    
#    class Meta:
#        model = SourceArticle
#        fields = ('title')
        
class DummyFixArticleForm(forms.Form):
    title = forms.CharField()
    sentences = forms.CharField(widget=forms.Textarea())

class AddTargetLanguagesForm(forms.Form):
    def __init__(self, article=None, *args, **kwargs):
        super(AddTargetLanguagesForm, self).__init__(*args, **kwargs)
        self.fields['languages'].queryset = Language.objects.exclude(
                            Q(id = article.language.id) |
                            Q(id__in=[o.id for o in article.get_target_languages()]) |
                            Q(code="templates"))
        
    languages = forms.ModelMultipleChoiceField(_("Languages"))
    