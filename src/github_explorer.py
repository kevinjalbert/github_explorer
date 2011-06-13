""" Script that drives the GitHub Explorer program that acquires information
about public repositories. The user inputed parameters are used to tailor the
search of repositories. The information is stored in a CSV file for later use.
"""
import csv
import argparse
import time
import socket
import urllib2
try: import simplejson as json
except ImportError: import json

class GitHubExplorer():

  """Class that crawls GitHub for repository information.

  The crawling process will take into account the user parameters to narrow
  the search down. The found repositories will be saved into a CSV file.
  """

  # List of all recognized GitHub languages
  _languages = ["ActionScript", "Ada", "Arc", "ASP", "Assembly", "Boo", "C",
      "C#", "C++", "Clojure", "CoffeeScript", "ColdFusion", "Common Lisp", "D",
      "Delphi", "Duby", "Eiffel", "Emacs Lisp", "Erlang", "F#", "Factor",
      "FORTRAN", "Go", "Groovy", "Haskell", "HaXe", "Io", "Java", "JavaScript",
      "Lua", "Max/FMSP", "Nu", "Objective-C", "Objective-J", "OCaml", "ooc",
      "Perl", "PHP", "Pure Data", "Python", "R", "Racket", "Ruby", "Scala",
      "Scheme", "sclang", "Self", "Shell", "Smalltalk", "SuperCollider", "Tcl",
      "Vala", "Verilog", "VHDL", "VimL", "Visual Basic", "XQuery", ""]

  # Primary language to be used in the search
  _primaryLanguage = None

  # List of keywords to be used in the search
  _keywords = None

  # The CSV column headers
  _headers = ["created", "created_at", "description", "followers", "fork",
      "forks", "has_downloads", "has_issues", "has_wiki", "homepage",
      "master_branch", "name", "open_issues", "owner", "private", "pushed",
      "pushed_at", "score", "size", "type", "url", "username", "watchers"]

  # API delay (controls the rate of API calls (x/60 = # of calls per minute)
  _apiDelay = None

  # API repository call
  API_CALL = "https://github.com/api/v2/json/repos/"

  def __init__(self, language, keywords, apiDelay, apiTimeout):
    """Default constructor that initializes the GitHubExplorer to use the
    specified primary language, keywords, API call delay and the API timeout.

    Args:
      language: The primary language to be used in the search
      keywords: The string of keywords to be used in the search
      apiDelay: The value to be used for the API call delay
      apiTimeout: The value to be used for the API timeout
    """
    if language not in self._languages:
      raise Exception("%s is not not valid language" %(language))

    self._primaryLanguage = self.cleanInput(language)  # Must clean the input
    self._keywords = '+'.join(keywords.split())  # Replace whitespace with +
    self._apiDelay = apiDelay
    socket.setdefaulttimeout(float(apiTimeout)) # Set API timeout

    # Get repositories.csv ready
    csv_file = open('repositories.csv','wb')
    csv_writer = csv.writer(csv_file)
    header = []
    header.extend(self._headers)
    header.extend(self._languages)
    header.pop()
    csv_writer.writerow(header)
    csv_file.close()

    self.crawlRepositories()

  def cleanInput(self, input):
    """Cleans the input from special characters, as GitHub's language parameter
    can have special characters that can break the search.

    Args:
      input: The string that will be cleansed from special characters
    """
    input = input.replace(":", "%3A")
    input = input.replace("/", "%2F")
    input = input.replace("#", "%23")
    input = input.replace("+", "%2B")
    return input

  def crawlRepositories(self):
    """Crawls GitHub using their API to incrementally acquire a list of
    repositories that match the primary language and search keywords. The
    repositories come in sets of 100 per page, and are handled one at a time.
    This terminates when there are no more repositories or an error occurs.
    """
    page = 0
    moreRepositories = True
    repositories = None
    while (moreRepositories):
      # Try to grab list of repositories
      page += 1
      print "LOG: Acquiring new list of repository from page", page

      # API search for all repositories of the primary language on given page
      successful = False
      while not successful:
        try:
          repositories = json.load(urllib2.urlopen((self.API_CALL + "search/\"%s\"?language=%s&start_page=%d" %(self._keywords, self._primaryLanguage, page))))['repositories']
          successful = True
        except urllib2.HTTPError, e:
          if e.code == 502:
            print "WARNING: Retrying to acquire list of repositories (Bad API Call)"
          else:
            print "ERROR: Unable to fetch repositories (API Limit/Invalid Page)"
            print "WAIT: 60 seconds"
            time.sleep(60)
            print "WAIT: Done"

      if repositories == None or len(repositories) == 0:
        print "LOG: No repositories left in search"
        moreRepositories = False
      else:
        pageOfRepositories = []
        count = 0
        # Loop over list of repositories
        for repository in repositories:
          time.sleep(float(self._apiDelay))  # To control over-calling the API
          count += 1
          print "LOG: Handling Repository %s (%d/100)" %(repository['name'], count)
          pageOfRepositories.append(self.handleRepository(repository))

        # Append repository page information to csv file
        csv_file = open('repositories.csv','a')
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_NONNUMERIC)
        csv_writer.writerows(pageOfRepositories)
        csv_file.close()


  def handleRepository(self, repository):
    """An individual repository is handled here by acquiring all of its general
    information. To acquire the language information, another GitHub API call
    is needed.

    Args:
      repository: The repository that will be examined to acquire information

    Returns:
      List of language size for repository.
    """
    # Acquire the languages of the repository
    successful = False
    while not successful:
      try:
        repositoryLanguages = json.load(urllib2.urlopen(self.API_CALL + "show/%s/%s/languages" %(repository['owner'], repository['name'])))['languages']
        successful = True
      except urllib2.HTTPError, e:
        if e.code == 502:
          print "WARNING: Retrying to acquire language information of repository (Bad API Call)"
        else:
          print "ERROR: Unable to fetch repository information (API Limit/Invalid Page)"
          print "WAIT: 60 seconds"
          time.sleep(60)
          print "WAIT: Done"

    # Acquire list all the information
    allInfo = []
    for info in self._headers:
      try: allInfo.append(repository[info].encode("utf-8"))
      except KeyError: allInfo.append(0)
      except AttributeError: allInfo.append(repository[info])

    for language in self._languages:
      try: allInfo.append(repositoryLanguages[language])
      except KeyError: allInfo.append(0)

    return allInfo

# If this module is ran as main
if __name__ == '__main__':

  # Define the argument options to be parsed
  parser = argparse.ArgumentParser(
      description = 'github_crawler <https://github.com/kevinjalbert/github_explorer>',
      version = 'github_explorer 0.2.0',
      usage = 'python github_explorer.py -l LANGUAGE -k KEYWORDS')
  parser.add_argument(
      '-l',
      action='store',
      default="",
      dest='language',
      help='Primary language to search for using GitHub\'s defined set of languages (ex: Python)')
  parser.add_argument(
      '-k',
      action='store',
      default="",
      dest='keywords',
      help='Keywords to search (ex: "Testing Concurrency Android")')
  parser.add_argument(
      '-d',
      action='store',
      default="1.25",
      dest='apiDelay',
      help='Delay in seconds between API calls (apiDelay/60 = # of calls per minute, cannot exceed 60/minute) [DEFAULT=1.25]')
  parser.add_argument(
      '-t',
      action='store',
      default="10",
      dest='apiTimeout',
      help='Timeout of API calls in seconds [DEFAULT=10]')

  # Parse the arguments passed from the shell
  userArgs = parser.parse_args()

  gitHubExplorer = GitHubExplorer(userArgs.language, userArgs.keywords, userArgs.apiDelay, userArgs.apiTimeout)
