from wt_translation.models import MachineTranslator, ServerlandHost

host = ServerlandHost()
host.shortname = "local"
host.url = "http://0.0.0.0:6666"
host.token = "7594f0db"
host.description = "A local XML-RPC serverland host"

host.save()
