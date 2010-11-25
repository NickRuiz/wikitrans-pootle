from datetime import datetime
from django import forms
from django.utils.translation import ugettext_lazy as _

from wt_articles.models import SourceArticle, SourceSentence, TranslatedSentence
from wt_articles.models import TranslatedArticle,ArticleOfInterest
from wt_articles import DEFAULT_TRANNY
from django import forms
from django.forms.formsets import formset_factory

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
    class Meta:
        model = ArticleOfInterest
        
class FixArticleForm(forms.ModelForm):
    sentences = forms.CharField(widget=forms.Textarea())
    
    class Meta:
        model = SourceArticle
        fields = ('title')
        
class DummyFixArticleForm(forms.Form):
    title = forms.CharField()
    sentences = forms.CharField(widget=forms.Textarea())

