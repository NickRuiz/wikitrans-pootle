#!/usr/bin/env python

"""Top-level tests using urllib2 to check interaction with servers
This uses test_cmdlineserver / test_service / test_apache (which are for different webservers)
ServerTester is mixed in with the different server tests below to generate the required tests"""

from Pootle import test_create
from Pootle import test_cmdlineserver
import urllib
import urllib2
try:
	import cookielib
except ImportError:
	# fallback for python before 2.4
	cookielib = None
	import ClientCookie

class ServerTester:
	"""Tests things directly against the socket of the server. Requires self.baseaddress"""
	setup_class = test_create.TestCreate.setup_class

	def setup_cookies(self):
		"""handle cookies etc"""
		if cookielib:
			self.cookiejar = cookielib.CookieJar()
			self.opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(self.cookiejar))
			self.urlopen = self.opener.open
		else:
			self.urlopen = ClientCookie.urlopen

	def setup_prefs(self, method):
		"""sets up any extra preferences required..."""
		if method in (self.test_add_project, self.test_admin_rights):
			self.prefs.setvalue("Pootle.users.testuser.rights.siteadmin", True)

	def fetch_page(self, relative_url):
		"""Fetches a page from the webserver installed in the service"""
		url = "%s/%s" % (self.baseaddress, relative_url)
		print "fetching", url
		stream = self.urlopen(url)
		contents = stream.read()
		return contents

	def login(self):
		"""calls the login method with username and password"""
		return self.fetch_page("?islogin=1&username=testuser&password=")

	def test_login(self):
		"""checks that login works and sets cookies"""
		contents = self.login()
		# check login leads us to a normal page
		assert "Log In" not in contents
		# check login is retained on next fetch
		contents = self.fetch_page("")
		print contents
		assert "Log In" not in contents

	def test_non_admin_rights(self):
		"""checks that without admin rights we can't access the admin screen"""
		contents = self.login()
		adminlink = '<A href="/admin/">Admin</A>' in contents
		assert not adminlink
		contents = self.fetch_page("admin/")
		denied = "You do not have the rights to administer pootle" in contents
		assert denied

	def test_admin_rights(self):
		"""checks that admin rights work properly"""
		contents = self.login()
		adminlink = '<A href="/admin/">Admin</A>' in contents
		assert adminlink
		contents = self.fetch_page("admin/")
		admintitle = "<title>Pootle Admin Page</title>" in contents
		assert admintitle

	def test_add_project(self):
		"""checks that we can add a project successfully"""
		self.login()
		projects_list = self.fetch_page("admin/projects.html")
		testproject_present = '<A href="../projects/testproject/admin.html">testproject</A>' in projects_list
		assert testproject_present
		testproject2_present = '<A href="../projects/testproject2/admin.html">testproject2</A>' in projects_list
		assert not testproject2_present
		add_dict = {"newprojectcode": "testproject2", "newprojectname": "Test Project 2", 
			"newprojectdescription": "Test Project Addition", "changeprojects": "Save changes"}
                add_args = "&".join(["%s=%s" % (key, urllib.quote_plus(value)) for key, value in add_dict.items()])
		add_url = "admin/projects.html?" + add_args
		add_result = self.fetch_page(add_url)
		testproject2_present = '<A href="../projects/testproject2/admin.html">testproject2</A>' in add_result
		assert testproject2_present

def MakeServerTester(baseclass):
	"""Makes a new Server Tester class using the base class to setup webserver etc"""
	class TestServer(baseclass, ServerTester):
		def setup_method(self, method):
			ServerTester.setup_prefs(self, method)
			baseclass.setup_method(self, method)
			ServerTester.setup_cookies(self)
	return TestServer

TestServerCmdLine = MakeServerTester(test_cmdlineserver.TestCmdlineServer)
# TestServerService = MakeServerTester(test_service.TestjLogbookService)
# TestServerApache = MakeServerTester(test_apache.TestApachejLogbook)

