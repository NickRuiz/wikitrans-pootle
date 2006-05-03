#!/usr/bin/env python

from Pootle import pootlefile
from Pootle import projects
from Pootle import potree
from Pootle import pootle
from Pootle import users
from translate.storage import po
from jToolkit.data import indexer
import os
import profile
import pstats

class PootleBenchmarker:
    """class to aid in benchmarking pootle"""
    StoreClass = pootlefile.pootlefile
    UnitClass = pootlefile.pootleelement
    def __init__(self, test_dir):
        """sets up benchmarking on the test directory"""
        self.test_dir = test_dir

    def clear_test_dir(self):
        """removes the given directory"""
        if os.path.exists(self.test_dir):
            for dirpath, subdirs, filenames in os.walk(self.test_dir, topdown=False):
                for name in filenames:
                    os.remove(os.path.join(dirpath, name))
                for name in subdirs:
                    os.rmdir(os.path.join(dirpath, name))
        if os.path.exists(self.test_dir): os.rmdir(self.test_dir)
        assert not os.path.exists(self.test_dir)

    def create_sample_files(self, num_dirs, files_per_dir, strings_per_file, source_words_per_string, target_words_per_string):
        """creates sample files for benchmarking"""
        if not os.path.exists(self.test_dir):
            os.mkdir(self.test_dir)
        for dirnum in range(num_dirs):
            if num_dirs > 1:
                dirname = os.path.join(self.test_dir, "sample_%d" % dirnum)
                if not os.path.exists(dirname):
                    os.mkdir(dirname)
            else:
                dirname = self.test_dir
            for filenum in range(files_per_dir):
                sample_file = self.StoreClass(pofilename=os.path.join(dirname, "file_%d.po" % filenum))
                for stringnum in range(strings_per_file):
                    source_string = " ".join(["word%d" % i for i in range(source_words_per_string)])
                    sample_unit = sample_file.addsourceunit(source_string)
                    sample_unit.target = " ".join(["drow%d" % i for i in range(target_words_per_string)])
                sample_file.savepofile()

    def parse_po_files(self):
        """parses all the po files in the test directory into memory"""
        count = 0
        for dirpath, subdirs, filenames in os.walk(self.test_dir, topdown=False):
            for name in filenames:
                pofilename = os.path.join(dirpath, name)
                parsedfile = po.pofile(open(pofilename, 'r'))
                count += len(parsedfile.units)
        print "counted %d elements" % count

    def parse_and_create_stats(self):
        """parses all the po files in the test directory into memory, using pootlefile, which creates Stats"""
        count = 0
        indexer.HAVE_INDEXER = False
        for dirpath, subdirs, filenames in os.walk(self.test_dir, topdown=False):
            for name in filenames:
                pofilename = os.path.join(dirpath, name)
                parsedfile = pootlefile.pootlefile(pofilename=pofilename, stats=True)
                count += len(parsedfile.units)
        print "stats on %d elements" % count

    def parse_and_create_index(self):
        """parses all the po files in the test directory into memory, using pootlefile, and allow index creation"""
        count = 0
        indexer.HAVE_INDEXER = True
        project = projects.TranslationProject("zxx", "benchmark", potree.DummyPoTree(self.test_dir))
        for name in project.browsefiles():
            count += len(project.getpofile(name).units)
        print "indexed %d elements" % count
        assert os.path.exists(os.path.join(self.test_dir, ".poindex-%s-%s" % (project.projectcode, project.languagecode)))

    def get_server(self):
        """gets a pootle server"""
        cwd = os.path.abspath(os.path.curdir)
        parser = pootle.PootleOptionParser()
        prefsfile = os.path.join(self.test_dir, "pootle.prefs")
        pootleprefsstr = """
importmodules.pootleserver = 'Pootle.pootle'
Pootle:
  serverclass = pootleserver.PootleServer
  sessionkey = 'dummy'
  baseurl = "/"
  userprefs = "users.prefs"
  podirectory = "%s"
  projects.benchmark:
    fullname = "Benchmark"
    description = "Benchmark auto-created files"
    checkstyle = "standard"
  languages.zxx.fullname = "Test Language"
""" % (self.test_dir)
        open(prefsfile, "w").write(pootleprefsstr)
        userprefsfile = os.path.join(self.test_dir, "users.prefs")
        open(userprefsfile, "w").write("testuser.activated=1\ntestuser.passwdhash = 'dd82c1882969461de74b46427961ea2c'\n")
        options, args = parser.parse_args(["prefsfile=%s" % prefsfile])
        options.servertype = "dummy"
        server = parser.getserver(options)
        os.chdir(cwd)
        return server

    def generate_main_page(self):
        """tests generating the main page"""
        server = self.get_server()
        session = users.PootleSession(server.sessioncache, server)
        server.getpage(["index.html"], session, {})

    def generate_projectindex_page(self):
        """tests generating the index page for the project"""
        server = self.get_server()
        session = users.PootleSession(server.sessioncache, server)
        server.getpage(["zxx/benchmark/"], session, {})

    def generate_translation_page(self):
        """tests generating the translation page for the file"""
        server = self.get_server()
        session = users.PootleSession(server.sessioncache, server)
        server.getpage(["zxx/benchmark/translate.html"], session, {})

if __name__ == "__main__":
    for sample_file_sizes in [
      # (1, 1, 1, 1, 1),
      (1, 1, 30, 10, 10),
      # (1, 5, 10, 10, 10),
      (1, 10, 10, 10, 10),
      (5, 10, 10, 10, 10),
      # (5, 10, 100, 20, 20),
      # (10, 20, 100, 10, 10),
      ]:
        benchmarker = PootleBenchmarker("BenchmarkDir")
        benchmarker.clear_test_dir()
        benchmarker.create_sample_files(*sample_file_sizes)
        methods = ["parse_po_files", "parse_and_create_stats", "parse_and_create_index", "generate_main_page", "generate_projectindex_page", "generate_translation_page"]
        for methodname in methods:
            print methodname, "%d dirs, %d files, %d strings, %d/%d words" % sample_file_sizes
            print "_______________________________________________________"
            statsfile = methodname + '_%d_%d_%d_%d_%d.stats' % sample_file_sizes
            profile.run('benchmarker.%s()' % methodname, statsfile)
            stats = pstats.Stats(statsfile)
            stats.sort_stats('cumulative').print_stats(20)
            print "_______________________________________________________"
        benchmarker.clear_test_dir()

