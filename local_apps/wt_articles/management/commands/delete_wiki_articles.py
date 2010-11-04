from django.core.management.base import NoArgsCommand, CommandError
from datetime import datetime
from wikipydia import query_text_rendered, query_text_raw

from wt_articles.models import ArticleOfInterest, SourceArticle, TranslationRequest
from wt_articles import DEFAULT_TRANNY

class Command(NoArgsCommand):
    help = "Delete all articles"

    requires_model_validation = False

    def handle_noargs(self, **options):
        articles_of_interest = SourceArticle.objects.all()
        for article in articles_of_interest:                        
            article.delete()
            
