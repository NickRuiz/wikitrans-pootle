import xmlrpclib
from wt_translation.models import ServerlandHost

host = ServerlandHost.objects.all()[0]
proxy = xmlrpclib.ServerProxy(host.url)

with open('/home/nick/Documents/test_files/test.txt') as f:
	file_contents = f.read()


result = proxy.delete_translation(host.token, 
                         "test30")

print result
