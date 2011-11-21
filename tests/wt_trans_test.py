from pootle_language.models import Language
from wt_translation.models import MachineTranslator, ServerlandHost, LanguagePair, request_translation

l1 = Language.objects.filter(code="en")[0]
l2 = Language.objects.filter(code="es")[0]

host = ServerlandHost.objects.all()[0]
# host.translators.all().delete()
# host.sync()
translator = host.translators.filter(shortname="GoogleWorker")[0]

request_translation(translator, text, l1, l2)

