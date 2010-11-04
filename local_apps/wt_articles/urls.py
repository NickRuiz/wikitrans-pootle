from django.conf.urls.defaults import *

from wt_articles import views
from wt_articles.forms import *


urlpatterns = patterns('wt_articles.views',
    ### Articles related stuff
    url(r'^$', 'landing', name="articles_landing"),
    
    # Export projects
    url(r'^source/export/project/(?P<aid>\d+)', 'source_to_pootle_project', name="source_to_pootle_project"),
    
    # Export articles
    url(r'^source/export/po/(?P<aid>\d+)', 'source_to_po', name="source_to_po"),

    url(r'^source/(?P<source>\w+)/(?P<title>[^/]+)/(?P<aid>\d+)',
        'show_source', name="articles_show_source"),
    url(r'^source/(?P<source>\w+)/(?P<title>[^/]+)/',
        'show_source', name="articles_show_source"),
    url(r'^fix/(?P<aid>\d+)', 'fix_article', name="fix_article"),

    url(r'^translated/(?P<source>\w+)-(?P<target>\w+)/(?P<title>[^/]+)/(?P<aid>\d+)',
        'show_translated', name="articles_show_translated"),
    url(r'^translated/(?P<source>\w+)-(?P<target>\w+)/(?P<title>[^/]+)/',
        'show_translated', name="articles_show_translated"),

    url(r'^list/', 'article_list', name="article_list"),
    url(r'^search/', 'article_search', name="article_search"),
    url(r'^translatable/', 'translatable_list', name="translatable_list"),
    url(r'^posteditable/', 'posteditable_list', name="posteditable_list"),
    url(r'^fix/', 'fix_article_list', name="fix_article_list"),

    url(r'^translate/new/(?P<source>\w+)-(?P<target>\w+)/(?P<title>[^/]+)/(?P<aid>\d+)',
        'translate_from_scratch', name="translate_from_scratch"),
    url(r'^translate/postedit/(?P<source>\w+)-(?P<target>\w+)/(?P<title>[^/]+)/(?P<aid>\d+)',
        'translate_post_edit', name="translate_post_edit"),

    ### Translation request related stuff
    url(r'^request_translation/', 'request_translation', name="request_translation")
)
