#!/usr/bin/env python

from Pootle import pootlefile
from Pootle import projects
from Pootle import potree
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

if __name__ == "__main__":
    for sample_file_sizes in [
      # (1, 1, 1, 1, 1),
      (1, 5, 10, 10, 10),
      # (1, 10, 10, 10, 10),
      (5, 10, 10, 10, 10),
      # (5, 10, 100, 20, 20),
      # (10, 20, 100, 10, 10),
      ]:
        benchmarker = PootleBenchmarker("BenchmarkDir")
        benchmarker.clear_test_dir()
        benchmarker.create_sample_files(*sample_file_sizes)
        for methodname in ("parse_po_files", "parse_and_create_stats", "parse_and_create_index"):
            print methodname, "%d dirs, %d files, %d strings, %d/%d words" % sample_file_sizes
            print "_______________________________________________________"
            statsfile = methodname + '_%d_%d_%d_%d_%d.stats' % sample_file_sizes
            profile.run('benchmarker.%s()' % methodname, statsfile)
            stats = pstats.Stats(statsfile)
            stats.sort_stats('cumulative').print_stats(10)
            print "_______________________________________________________"
        benchmarker.clear_test_dir()

