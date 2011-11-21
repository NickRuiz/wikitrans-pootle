from wt_translation.models import ServerlandHost, MachineTranslator, TranslationRequest, send_translation_requests
from pootle_store.models import Store, Unit, Suggestion

host = ServerlandHost.objects.all()[0]
host.fetch_translations()
