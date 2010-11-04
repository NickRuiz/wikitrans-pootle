from django.core.management.base import NoArgsCommand, CommandError
from datetime import datetime
from wikipydia import query_text_rendered, query_text_raw

from wt_articles.models import ArticleOfInterest, SourceArticle, TranslationRequest
from wt_articles import DEFAULT_TRANNY

class Command(NoArgsCommand):
    help = "Updates the texts for wikipedia articles of interest"

    requires_model_validation = False

    def handle_noargs(self, **options):
        articles_of_interest = ArticleOfInterest.objects.all()
        for article in articles_of_interest:
            #article_dict = query_text_raw(article.title,
                                               #language=article.title_language)
            article_dict = query_text_rendered(article.title,
                                               language=article.title_language)
            # don't import articles we already have
            if SourceArticle.objects.filter(doc_id__exact='%s' % article_dict['revid'],
                                            language=article.title_language):
                continue
            try:
                source_article = SourceArticle(title=article.title,
                                               language=article.title_language,
                                               # source_text = article_dict['text'],
                                               source_text=article_dict['html'],
                                               timestamp=datetime.now(),
                                               doc_id=article_dict['revid'])
                source_article.save()
                #tr = TranslationRequest(article=source_article,
                #                         target_language=article.target_language,
                #                         date=datetime.now(),
                #                         translator=DEFAULT_TRANNY)
                #tr.save()
            except Exception as e:
                print type(e)
                print e.args
                try:
                    source_article.delete()
                    tr.delete()
                except:
                    pass
