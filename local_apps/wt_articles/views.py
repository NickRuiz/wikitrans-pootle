from datetime import datetime
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponseRedirect, Http404
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.utils.translation import ugettext_lazy as _
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.views.generic import date_based
from django.conf import settings
from django.forms.formsets import formset_factory

from wt_articles.models import SourceArticle,TranslatedArticle
from wt_articles.models import SourceSentence,TranslatedSentence
from wt_articles.models import FeaturedTranslation, latest_featured_article
from wt_articles.models import ArticleOfInterest
from wt_articles.forms import TranslatedSentenceMappingForm, ArticleRequestForm, DummyFixArticleForm, AddTargetLanguagesForm
from wt_articles.utils import sentences_as_html, sentences_as_html_span, target_pairs_by_user
from wt_articles.utils import user_compatible_articles
from wt_articles.utils import user_compatible_target_articles
from wt_articles.utils import user_compatible_source_articles
from wt_articles.utils import all_articles, all_source_articles, all_translated_articles

# Pootle-related imports
from pootle_project.models import Project
from pootle_language.models import Language
from pootle_store.filetypes import filetype_choices, factory_classes, is_monolingual

from pootle_translationproject.models import TranslationProject

from urllib import quote_plus, unquote_plus

if "notification" in settings.INSTALLED_APPS:
    from notification import models as notification
else:
    notification = None

def landing(request, template_name="wt_articles/landing.html"):
    featured_translation = latest_featured_article()
    featured_text = u'No translations are featured'
    if featured_translation != None:
        featured_text = sentences_as_html(featured_translation.article.sentences.all())

    recent_translations = TranslatedArticle.objects.order_by('-timestamp')[:5]
    
    return render_to_response(template_name, {
        "featured_translation": featured_text,
        "recent_translations": recent_translations,
    }, context_instance=RequestContext(request))


def show_source(request, title, source, aid=None, template_name="wt_articles/show_article.html"):
    title = unquote_plus(title)
    
    if aid != None:
        sa_set = SourceArticle.objects.filter(id=aid)
    else:
        sa_set = SourceArticle.objects.filter(language=source,
                                              title=title).order_by('-timestamp')
    if len(sa_set) > 0:
        article_text = sentences_as_html_span(sa_set[0].sourcesentence_set.all())
    else:
        article_text = None

    return render_to_response(template_name, {
        "title": title,
        "article_text": article_text,
    }, context_instance=RequestContext(request))

def show_translated(request, title, source, target, aid=None, template_name="wt_articles/show_article.html"):
    title = unquote_plus(title)
    if aid != None:
        ta_set = TranslatedArticle.objects.filter(id=aid)
    else:
        ta_set = TranslatedArticle.objects.filter(article__language=source,
                                                  language=target,
                                                  title=title).order_by('-timestamp')
    if len(ta_set) > 0:
        article_text = sentences_as_html(ta_set[0].sentences.all())
    else:
        article_text = None
    return render_to_response(template_name, {
        "title": title,
        "article_text": article_text,
    }, context_instance=RequestContext(request))

def article_search(request, template_name="wt_articles/article_list.html"):
    if request.method == "POST" and request.POST.has_key('search'):
        name = request.POST['search']
        articles = TranslatedArticle.objects.filter(title__icontains=name)
        print articles
    else:
        articles = []
    return render_to_response(template_name, {
        'articles': articles,
    }, context_instance=RequestContext(request))
 
    
@login_required
def article_list(request, template_name="wt_articles/article_list.html"):
    # TODO: Request user-compatible articles; for now, we show all articles, since we are merging with Pootle.
    # articles = user_compatible_articles(request.user)
    articles = all_source_articles()
    from django.utils.encoding import smart_unicode
    
    content_dict = { "articles": articles, }
    content_dict.update(request_article(request))

    return render_to_response(template_name, content_dict, 
                              context_instance=RequestContext(request))

@login_required
def fix_article_list(request, template_name="wt_articles/fix_article_list.html"):
    articles = user_compatible_articles(request.user)
    from django.utils.encoding import smart_unicode

    return render_to_response(template_name, {
        "articles": articles,
    }, context_instance=RequestContext(request))

@login_required
def translatable_list(request, template_name="wt_articles/article_list.html"):
    import copy
    user = request.user
    source_articles = user_compatible_source_articles(request.user)
    articles = []
    for sa in source_articles:
        lang_pairs = target_pairs_by_user(user, sa.language)
        for pair in lang_pairs:
            article = copy.deepcopy(sa)
            article.target = pair[0]
            article.link = u'/articles/translate/new/%s' % (article.get_relative_url(pair[1]))
            articles.append(article)
    
    return render_to_response(template_name, {
        "articles": articles,
        "translatable": True,
    }, context_instance=RequestContext(request))

@login_required
def posteditable_list(request, template_name="wt_articles/article_list.html"):
    import copy
    user = request.user
    target_articles = user_compatible_target_articles(request.user)
    articles = []
    for ta in target_articles:
        lang_pairs = target_pairs_by_user(user, ta.language)
        for pair in lang_pairs:
            article = copy.deepcopy(ta)
            article.target = pair[0]
            article.link = u'/articles/translate/postedit/%s' % (article.get_relative_url())
            articles.append(article)
    
    return render_to_response(template_name, {
        "articles": articles,
        "translatable": True,
    }, context_instance=RequestContext(request))

@login_required
def translate_from_scratch(request, source, target, title, aid, template_name="wt_articles/translate_form.html"):
    """
    Loads a source article by provided article id (aid) and generates formsets
    to contain each sentence in the requested translation.
    """
    sa_set = SourceArticle.objects.filter(id=aid)
    if len(sa_set) < 1:
        no_match = True
        return render_to_response(template_name,
                                  {"no_match": True},
                                  context_instance=RequestContext(request))
    article = sa_set[0]
    ss_list = article.sourcesentence_set.all()
    TranslatedSentenceSet = formset_factory(TranslatedSentenceMappingForm, extra=0)
    
    if request.method == "POST":
        formset = TranslatedSentenceSet(request.POST, request.FILES)
        if formset.is_valid():
            ts_list = []
            ta = TranslatedArticle()
            for form in formset.forms:
                ss = form.cleaned_data['source_sentence']
                text = form.cleaned_data['text']
                ts = TranslatedSentence(segment_id=ss.segment_id,
                                        source_sentence=ss,
                                        text=text,
                                        translated_by=request.user.username,
                                        translation_date=datetime.now(),
                                        language=target,
                                        best=True, ### TODO figure something better out
                                        end_of_paragraph=ss.end_of_paragraph)
                ts_list.append(ts)
            ta.article = ss.article
            ta.title = ss.article.title
            ta.timestamp = datetime.now()
            ta.language = target
            ta.save()
            for ts in ts_list:
                ts.save()
            ta.sentences = ts_list
            ta.save()
            return HttpResponseRedirect(ta.get_absolute_url())
    else:
        initial_ss_set = [{'source_sentence': s} for s in ss_list]
        formset = TranslatedSentenceSet(initial=initial_ss_set)
    for form,s in zip(formset.forms,ss_list):
        form.fields['text'].label = s.text
    
    return render_to_response(template_name, {
        "formset": formset,
        "title": article.title,
    }, context_instance=RequestContext(request))

@login_required
def translate_post_edit(request, source, target, title, aid, template_name="wt_articles/translate_form.html"):
    """
    Loads a translated article by its article id (aid) and generates formsets
    with the source article and translated sentence. It then generates a new
    translated article out of the input from the user
    """
    ta_set = TranslatedArticle.objects.filter(id=aid)
    if len(ta_set) < 1:
        no_match = True
        return render_to_response(template_name,
                                  {"no_match": True},
                                  context_instance=RequestContext(request))
    translated_article = ta_set[0]
    ts_list = translated_article.sentences.all()
    ss_list = translated_article.article.sourcesentence_set.all()
    TranslatedSentenceSet = formset_factory(TranslatedSentenceMappingForm, extra=0)
    
    if request.method == "POST":
        formset = TranslatedSentenceSet(request.POST, request.FILES)
#        if formset.is_valid():
#            ts_list = []
#            ta = TranslatedArticle()
#            for form in formset.forms:
#                ss = form.cleaned_data['source_sentence']
#                text = form.cleaned_data['text']
#                ts = TranslatedSentence(segment_id=ss.segment_id,
#                                        source_sentence=ss,
#                                        text=text,
#                                        translated_by=request.user.username,
#                                        translation_date=datetime.now(),
#                                        language=target,
#                                        best=True, ### TODO figure something better out
#                                        end_of_paragraph=ss.end_of_paragraph)
#                ts_list.append(ts)
#            ta.article = ss.article
#            ta.title = ss.article.title
#            ta.timestamp = datetime.now()
#            ta.language = target
#            ta.save()
#            for ts in ts_list:
#                ts.save()
#            ta.sentences = ts_list
#            ta.save()
#            return HttpResponseRedirect(ta.get_absolute_url())
    else:
        initial_ts_set = [{'text': s.text} for s in ts_list]
        formset = TranslatedSentenceSet(initial=initial_ts_set)
    for form,s in zip(formset.forms,ss_list):
        form.fields['text'].label = s.text
        form.fields['text'].__dict__
    
    return render_to_response(template_name, {
        "formset": formset,
        "title": translated_article.title,
    }, context_instance=RequestContext(request))
    

@login_required
def fix_article(request, aid, form_class=DummyFixArticleForm, template_name="wt_articles/fix_article.html"):
    """
    aid in this context is the source article id
    """
    sa_set = SourceArticle.objects.filter(id=aid)
    if len(sa_set) < 1:
        no_match = True
        return render_to_response(template_name,
                                  {"no_match": True},
                                  context_instance=RequestContext(request))
    article = sa_set[0]
    
    if request.method == "POST":
        # fix_form = form_class(request.POST, instance=article)
        fix_form = DummyFixArticleForm(request.POST)
        
        if fix_form.is_valid():
            # TODO: Process the form.
            article.title = fix_form.cleaned_data['title']
            lines = fix_form.cleaned_data['sentences']
            
            # Convert the textarea of lines to SourceSentences
            sentences = article.lines_to_sentences(lines)
            
            # Delete the old sentences before saving the new ones
            article.delete_sentences()
            article.save(manually_splitting=True, source_sentences=sentences)
            
            return HttpResponseRedirect(article.get_absolute_url())
    else:
        # TODO: For some reason, FixArticleForm worked in the original WikiTrans, but is no longer working when merged with Pootle.
        # fix_form = form_class(instance=article, initial={'sentences': article.sentences_to_lines()})
        
        dummy_fix_form = DummyFixArticleForm(initial={'sentences': article.sentences_to_lines(), 'title': article.title})
        
    return render_to_response(template_name, {
        "article": article,
        # "fix_form": fix_form
        "fix_form": dummy_fix_form
    }, context_instance=RequestContext(request))

@login_required
def request_article(request, form_class=ArticleRequestForm, template_name="wt_articles/request_form.html"):
    """
    aid in this context is the source article id
    """
    if request.method == "POST":
        request_form = form_class(request.POST)
        if request_form.is_valid():
            title = request_form.cleaned_data['title']
            title_language = request_form.cleaned_data['title_language']
#            target_language = request_form.cleaned_data['target_language']
            exists = ArticleOfInterest.objects.filter(title__exact=title,
                                                      title_language__exact=title_language)
#                                                      target_language__exact=target_language)
            if len(exists) < 1:
                translation_request = request_form.save(commit=False)
                translation_request.date = datetime.now()
                translation_request.save()
#            return render_to_response("wt_articles/requests_thankyou.html", {},
#                                      context_instance=RequestContext(request))

                request_form = form_class()
                
                return {"article_requested": True,
                        "request_form": request_form}
    else:
        request_form = form_class()
        
#    return render_to_response(template_name, {
#        "request_form": request_form,
#    }, context_instance=RequestContext(request))
        return {"article_requested": False,
                "request_form": request_form}

@login_required
def source_to_po(request, aid, template_name="wt_articles/source_export_po.html"):
    """
    aid in this context is the source article id
    """
    from django.utils.encoding import smart_str
    
    sa_set = SourceArticle.objects.filter(id=aid)
    if len(sa_set) < 1:
        no_match = True
        return render_to_response(template_name,
                                  {"no_match": True},
                                  context_instance=RequestContext(request))
    
    article = sa_set[0]
    po = article.sentences_to_po()
    
    return render_to_response(template_name, {
        "po": smart_str( po ),
        "title": article.title
    }, context_instance=RequestContext(request))

# # Deprecated. Added to SourceArticle class in models.py.
#def _source_to_pootle_project(article): 
#    import logging
#    from django.utils.encoding import smart_str
#    from pootle_app.models.signals import post_template_update
#
#
#    # Fetch the source_language
#    sl_set = Language.objects.filter(code = article.language)
#    
#    if len(sl_set) < 1:
#        return false
#
#    source_language = sl_set[0]
#        
#     # Construct the project
#    project = Project()
#    project.fullname = u"%s:%s" % (article.language, article.title)
#    project.code = project.fullname.replace(" ", "_").replace(":", "_")
#    # PO filetype
#    #project.localfiletype = "po" # filetype_choices[0]
#    
#    project.source_language = source_language
#  # Save the project
#    project.save()
#    
#    templates_language = Language.objects.filter(code='templates')[0]
#    
#    # Check to see if the templates language exists. If not, add it.
#    #if not project.language_exists(templates_language):
#    if len(TranslationProject.objects.filter(language = templates_language, id=project.id)) == 0:
#        project.add_language(templates_language)
#        project.save()
#    
#    #code copied for wr_articles
#    logging.debug ( "project saved")
#    # Export the article to .po and store in the templates "translation project". This will be used to generate translation requests for other languages.
#    templatesProject = project.get_template_translationproject()
#    po = article.sentences_to_po()
#    poFilePath = "%s/article.pot" % (templatesProject.abs_real_path)
#    
#    oldstats = templatesProject.getquickstats()
#    
#    # Write the file
#    with open(poFilePath, 'w') as f:
#        f.write(smart_str(po.__str__()))
#    
#    # Force the project to scan for changes.
#    templatesProject.scan_files()
#    templatesProject.update(conservative=False)
#    
#    # Log the changes
#    newstats = templatesProject.getquickstats()
#    post_template_update.send(sender=templatesProject, oldstats=oldstats, newstats=newstats)
#        
#    
#    
#    return project

@login_required
def delete_pootle_project(request, aid):
# TODO: Display notification on page that the project has been deleted.
    """
    Deletes a pootle Project by id (aid).
    """
    # Fetch the article
    no_match = False
    
    sa_set = SourceArticle.objects.filter(id=aid)
    if len(sa_set) < 1:
        no_match = True
    else:
        article = sa_set[0]
        article.delete_pootle_project(delete_local=True)
     
    # Display the article list.   
    return article_list(request)
            
@login_required
def create_pootle_project(request, aid):
# TODO: Display notification on page that the project has been created.
# def create_pootle_project(request, aid, template_name="wt_articles/source_export_project.html"):
    """
    Converts an article to a Pootle project by id (aid).
    """
    # Fetch the article
    no_match = False
    
    sa_set = SourceArticle.objects.filter(id=aid)
    if len(sa_set) < 1:
        no_match = True
    else:
        article = sa_set[0]
        project = article.create_pootle_project()
    
    # Display the article list
    return article_list(request)
    
#    if no_match or project == False:
#        return render_to_response(template_name,
#                                  {"no_match": True},
#                                  context_instance=RequestContext(request))
#    else:
#        return render_to_response(template_name,
#                                  {"project_name": project.fullname},
#                                  context_instance=RequestContext(request))

@login_required
def add_target_languages(request, aid, template_name="wt_articles/add_target_languages.html"):
    """
    Adds one or more target language translations to a source article. 
    """
    content_dict = {}
    
    # Fetch the article
    no_match = False
    
    sa_set = SourceArticle.objects.filter(id=aid)
    if len(sa_set) < 1:
        no_match = True
        content_dict['no_match'] = no_match
    else:
        article = sa_set[0]
        content_dict['article'] = article
        
        if request.method == "POST":
            target_language_form = AddTargetLanguagesForm(article, request.POST)
            
            if target_language_form.is_valid():
                languages = target_language_form.cleaned_data['languages']
                
                article.add_target_languages(languages)
                return HttpResponseRedirect('/articles/list')
        else:
            target_language_form = AddTargetLanguagesForm(article)
        
        content_dict['target_language_form'] = target_language_form
    return render_to_response(template_name, content_dict, 
                              context_instance=RequestContext(request))