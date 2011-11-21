import xmlrpclib
from wt_translation.models import ServerlandHost
from wt_translation import utils

host = ServerlandHost.objects.all()[0]
proxy = xmlrpclib.ServerProxy(host.url)

with open('/home/nick/Documents/test_files/test.txt') as f:
	file_contents = f.read()


result = proxy.create_translation(host.token, 
                         utils.generate_request_id(), 
                         "GoogleWorker",
                         "eng",
                         "spa",
                         "test.txt",
                         file_contents)
print type(result)
print result
