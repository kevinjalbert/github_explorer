import logging
import time
import urllib2
try: import simplejson as json
except ImportError: import json

class APIHandler():

  """This class handles all calls to the GitHub API

  There are two API calls made through this class. The first one is used to
  acquire the next page of repositories given the search criteria, that is 100
  repositories) at a time. The second one is used to acquire the size of each
  of the languages used in the repository. Error handling is used to retry API
  calls if the rate limit is reached or bad connection occurs.

  """

  # The general API call to acquire repository information from GitHub
  API_CALL = "https://github.com/api/v2/json/repos/"

  # Logger being used for this execution
  logger = None

  def __init__(self, logger):
    """Constructor that just makes a log entry

      Args:
        logger: The custom logger to be used for this executing process

    """

    self._logger = logger
    self._logger.info("API Handler is ready for use")

  def getNextPage(self, nextPage, language, keywords):
    """API call that requests the next page of repositories

    Args:
      nextPage: The next page number of the repository search
      language: The language for the search being conducted
      keywords: The keywords for the search being conducted

    Returns:
      A list of repositories from the specified repository page

    """

    self._logger.info("Acquiring new list of repositories from page %d" %nextPage)
    APICall = self.API_CALL + "search/\"%s\"?language=%s&start_page=%d" %(keywords, language, nextPage)
    return self._makeAPICall(APICall)['repositories']

  def getLanguages(self, repositoryName, repositoryOwner):
    """API call that requests the language->size values of a repository

    Args:
      repositoryName: The name of the repository
      repositoryOwner: The owner of the repository

    Returns:
      A list of language->size values of the specified repository

    """

    self._logger.info("Acquiring language information from repository %s" %repositoryName)
    APICall = self.API_CALL + "show/%s/%s/languages" %(repositoryOwner, repositoryName)
    return self._makeAPICall(APICall)['languages']

  def _makeAPICall(self, apiCall):
    """Makes the actual API request given the specified apiCall.

    The API call will retry after waiting the 60 second API rate reset. The
    retrying process will occur 5 times, in which after that it stop.

    Args:
      apiCall: The custom formated API call to be used

    Returns:
      The JSON result of the API call or None if call fails

    """

    currentAttempt = 0
    maxAttempts = 10  # The number of attempts to retry the API call
    successful = False

    # Keep trying to complete a successful API call (up to maxAttempts times)
    while not successful:

      # If the API call doesn't succeed wait 60 seconds and try again
      try:
        repositories = json.load(urllib2.urlopen(apiCall))
        successful = True
      except urllib2.HTTPError, e:
        self._logger.warn("Unsuccessful API call -> HTTP Error: %s" %e.code)
        if currentAttempt <= maxAttempts:
          self._logger.info("Retrying API call attempt %d/%d" %(currentAttempt, maxAttempts))
          self._logger.info("Waiting 60 seconds")
          time.sleep(60)
        else:
          self._logger.warn("API call attempts exceeded")
          return None

    return repositories
