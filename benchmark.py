#!/usr/bin/env python

from Pootle import pootlefile
from translate.storage import po
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

if __name__ == "__main__":
    for sample_file_sizes in [
      (1, 1, 1, 1, 1),
      (1, 10, 10, 10, 10),
      (10, 20, 100, 10, 10),
      ]:
        print "%d dirs, %d files, %d strings, %d/%d words" % sample_file_sizes
        benchmarker = PootleBenchmarker("BenchmarkDir")
        benchmarker.clear_test_dir()
        benchmarker.create_sample_files(*sample_file_sizes)
        profile.run('benchmarker.parse_po_files()', 'Benchmark.stats')
        stats = pstats.Stats('Benchmark.stats')
        stats.sort_stats('cumulative').print_stats(10)
        benchmarker.clear_test_dir()

