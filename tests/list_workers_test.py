import xmlrpclib
from wt_translation.models import ServerlandHost

host = ServerlandHost.objects.all()[0]
proxy = xmlrpclib.ServerProxy(host.url)


result = proxy.list_workers(host.token)

print result
print type(result)
