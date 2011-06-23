""" Script that drives the GitHub Explorer program that acquires information
about public repositories. The user inputed parameters are used to tailor the
search of repositories. The information is stored in a CSV file for later use.
"""
import csv
import argparse
import time
import socket
import urllib2
import logging
import subprocess
try: import simplejson as json
except ImportError: import json

class GitHubExplorer():

  """Class that crawls GitHub for repository information.

  The crawling process will take into account the user parameters to narrow
  the search down. The found repositories will be saved into a CSV file.
  """

  # Log everything, and send it to stderr.
  logging.basicConfig( level=logging.DEBUG )

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

  # List of keywords to be used in the search (ex: "android testing units")
  _keywords = None

  # List of source statements to be used in the search (ex: term1|term2)
  _sourceStatements = None

  # The CSV column headers
  _headers = ["created", "created_at", "description", "followers", "fork",
      "forks", "has_downloads", "has_issues", "has_wiki", "homepage",
      "master_branch", "name", "open_issues", "owner", "private", "pushed",
      "pushed_at", "score", "size", "type", "url", "username", "watchers"]

  # API delay (controls the rate of API calls (x/60 = # of calls per minute)
  _apiDelay = None

  # API repository call
  API_CALL = "https://github.com/api/v2/json/repos/"

  def __init__(self, language, keywords, sourceStatements, apiDelay, apiTimeout):
    """Default constructor that initializes the GitHubExplorer to use the
    specified primary language, keywords, API call delay and the API timeout.

    Args:
      language: The primary language to be used in the search
      keywords: The string of keywords to be used in the search
      sourceStatements: The string of source statements to be used in the search
      apiDelay: The value to be used for the API call delay
      apiTimeout: The value to be used for the API timeout
    """
    if language not in self._languages:
      logging.fatal("%s is not not valid language" %(language))
      language = ""

    self._primaryLanguage = self.cleanInput(language)  # Must clean the input
    self._keywords = '+'.join(keywords.split())  # Replace whitespace with +
    self._sourceStatements = sourceStatements
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
      logging.info("Acquiring new list of repository from page %d" %page)

      # API search for all repositories of the primary language on given page
      successful = False
      while not successful:
        try:
          repositories = json.load(urllib2.urlopen((self.API_CALL + "search/\"%s\"?language=%s&start_page=%d" %(self._keywords, self._primaryLanguage, page))))['repositories']
          successful = True
        except urllib2.HTTPError, e:
          if e.code == 502:
            logging.warn("Retrying to acquire list of repositories (Bad API Call)")
          else:
            logging.error("Unable to fetch repositories (API Limit/Invalid Page)")
            logging.info("Waiting 60 seconds")
            time.sleep(60)
            logging.info("Waiting done")

      if repositories == None or len(repositories) == 0:
        logging.info("No repositories left in search")
        moreRepositories = False
      else:
        pageOfRepositories = []
        count = 0
        # Loop over list of repositories
        for repository in repositories:
          time.sleep(float(self._apiDelay))  # To control over-calling the API
          count += 1
          logging.info("Handling Repository %s (%d/100)" %(repository['name'], count))
          pageOfRepositories.append(self.examineRepository(repository))

          # Perform the handle Repository cloning
          self.cloneRepository(repository)

          # Perform grepping of source statements
          relavant = self.isStatementInRepository(repository)

          if relavant:
            # Perform custom handling of the repository
            self.customHandleRepository(repository)
          else:
            # Clean up repository
            self.cleanRepository(repository)

        # Append repository page information to csv file
        csv_file = open('repositories.csv','a')
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_NONNUMERIC)
        csv_writer.writerows(pageOfRepositories)
        csv_file.close()

  def cloneRepository(self, repository):
    logging.info("Cloning Repository %s" %repository['name'])
    process = subprocess.Popen( ['git', 'clone', repository['url']], stdout=subprocess.PIPE, shell=False)
    output,error = process.communicate()
    print output
    logging.info("Finished cloning repository %s" %repository['name'])

  def customHandleRepository(self, repository):
    pass

  def isStatementInRepository(self, repository):
    logging.info("Grepping for sourceStatements (%s) in Repository %s" %(self._sourceStatements, repository['name']))
    process = subprocess.Popen( ['egrep', self._sourceStatements, '-riswl', repository['name'], '--exclude-dir=*/.git/*'], stdout=subprocess.PIPE, shell=False)
    output,error = process.communicate()

    if len(output) > 0:
      logging.info("Statements found in repository %s" %repository['name'])
      return True
    else:
      logging.info("Statements not found in repository %s" %repository['name'])
      return False

  def cleanRepository(self, repository):
    logging.info("Removing cloned repository %s" %repository['name'])
    process = subprocess.Popen( ['rm', '-rf', repository['name']], stdout=subprocess.PIPE, shell=False)
    logging.info("Removed cloned repository %s" %repository['name'])

  def examineRepository(self, repository):
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
          logging.warn("Retrying to acquire language information of repository (Bad API Call)")
        else:
          logging.error("Unable to fetch repository information (API Limit/Invalid Page)")
          logging.info("Waiting 60 seconds")
          time.sleep(60)
          logging.info("Waiting done")

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
      version = 'github_explorer 0.2.0')
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
      '-s',
      action='store',
      default="",
      dest='sourceStatements',
      help='Source Statements to search (ex: "java.util|synchronized|latch"), able to search with multiple terms (this-or-that)')
  parser.add_argument(
      '-d',
      action='store',
      default="1",
      dest='apiDelay',
      help='Delay in seconds between API calls (apiDelay/60 = # of calls per minute, cannot exceed 60/minute) [DEFAULT=1]')
  parser.add_argument(
      '-t',
      action='store',
      default="10",
      dest='apiTimeout',
      help='Timeout of API calls in seconds [DEFAULT=10]')

  # Parse the arguments passed from the shell
  userArgs = parser.parse_args()

  gitHubExplorer = GitHubExplorer(userArgs.language, userArgs.keywords, userArgs.sourceStatements, userArgs.apiDelay, userArgs.apiTimeout)