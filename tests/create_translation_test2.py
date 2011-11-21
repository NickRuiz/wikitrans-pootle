import xmlrpclib
from wt_translation.models import ServerlandHost, MachineTranslator, request_translation
from pootle_language.models import Language
from django.db.models import Q

host = ServerlandHost.objects.all()[0]
translator = host.translators.filter(shortname="GoogleWorker")[0]

[source, target] = Language.objects.filter(Q(code = "en") | Q(code = "es"))

with open('/home/nick/Documents/test_files/test3.txt') as f:
	file_contents = f.read()

result = request_translation(translator, file_contents, source, target)

print type(result)
print result
