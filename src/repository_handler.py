import logging
import subprocess
import time
from datetime import datetime, timedelta
import api_handler
import report_handler


class RepositoryHandler():

  """This class handles the repository creation and manipulation

  The crawling of GitHub for repositories that fall in the search criteria
  occurs in this class. The data is extracted from repositories and passed
  to the ReportHandler. If enabled the repositories will be cloned and check
  to see if indicated source statements are present (using egrep on Linux).
  Given a positive hit on the search for source statements the repository
  is kept, otherwise it is removed. There is a customHandleRepository function
  that allows for a special handling of a repository based on the user.

  """

  # The API handler
  _apiHandler = None

  # The report handler
  _reportHandler = None

  # List of all recognized GitHub languages
  _languages = None

  # Primary language to be used in the search
  _primaryLanguage = None

  # List of keywords to be used in the search (ex: "android testing units")
  _keywords = None

  # List of source statements to be used in the search (ex: "term1 term2")
  _sourceStatements = None

  # The CSV column headers
  _headers = None

  # Flag that specifies if repository cloning should occur
  _clone = None

  # The ID of this process
  _processNumber = None

  # The max number of processes being ran
  _maxProcesses = None

  # Logger being used for this execution
  _logger = None

  def __init__(self, headers, languages, primaryLanguage, keywords,
               sourceStatements, clone, processNumber, maxProcesses, logger):
    """Constructor that sets the passed parameters as well as the handlers

    The parameters are sets within the class for future use. The APIHandler
    and the ReportHandler are created here, to be user within this class.

    Args:
      headers: The list of header fields that repositories have
      languages: The list of languages that GitHub has available
      primaryLanguage: A filter of the primary language for the repositories
      keywords: Filter of keywords for the repositories
      sourceStatements: Filter of source statements for the repositories
      clone: Flag that indicates repositories should be cloned
      processNumber: The ID of this process, used as a modifier to the pages
      maxProcesses: The max number of concurrent processes running
      logger: The custom logger to be used for this executing process

    """

    self._reportHandler = report_handler.ReportHandler(headers, languages,
                                                       logger)
    self._apiHandler = api_handler.APIHandler(logger)

    self._languages = languages
    self._primaryLanguage = primaryLanguage
    self._keywords = keywords
    self._sourceStatements = sourceStatements
    self._headers = headers
    self._clone = clone
    self._processNumber = processNumber
    self._maxProcesses = maxProcesses
    self._logger = logger

    self._reportHandler.readyCSVReport()

  def crawlRepositories(self):
    """Function that crawls the GitHub repositories given the search criteria

    Crawls GitHub using their API to incrementally acquire a list of
    repositories that match the primary language and search keywords. The
    repositories come in sets of 100 per page, and are handled one at a time.
    This terminates when there are no more repositories or an error occurs.
    Given the situation the repository can be cloned and further examined. The
    pages are incremented based on the number of max processes searching.

    """

    page = self._processNumber
    done = False

    while not done:

      # Acquire next page of repositories
      repositories = self._apiHandler.getNextPage(page, self._primaryLanguage,
                                                  self._keywords)

      # Consider terminating condition
      if repositories == None or len(repositories) == 0:
        self._logger.info("No repositories left in current search")
        done = True
      else:
        dataOfRepositories = []

        for repository in repositories:

          # Make a unique name so forks and leading '-' don't cause problems
          repository['uniqueName'] = "_%s_%s" %(repository['name'],
                               repository['owner'])

          # Change the repository url from 'https' to 'git', much faster
          repository['url'] = "git" + repository['url'][5:]

          startTime = datetime.now()  # Make note of the starting time
          size, data = self._examineRepository(repository)

          # If the API call failed for examining the repository, skip it
          if data == None:
            self._logger.warn("Language acquisition process failed, skipping %s"
                                  %repository['uniqueName'])
            continue

          if size > 0:
            dataOfRepositories.append(data)

            if self._clone:
              cloned = self._cloneRepository(repository)

              if cloned:

                if self._sourceStatements != "":
                  relavant = self._isStatementInRepository(repository)

                  if relavant:
                    self._customHandleRepository(repository)
                  else:
                    self._cleanRepository(repository)
              else:
                self._logger.warn("Clone process failed, therefore skipping")
                continue

          else:
            self._logger.warn("No content found in repository, therefore "
                              "skipping")
            continue

          timeTaken = datetime.now() - startTime  # Figure out the time taken
          print "P%d Done: %s (took %s)" \
                %(self._processNumber, repository['uniqueName'], timeTaken)
          self._logger.info("Done: %s (took %s)" \
                            %(repository['uniqueName'], timeTaken))

        self._reportHandler.appendCSVData(dataOfRepositories)
      page += self._maxProcesses

  def _cloneRepository(self, repository):
    """Clones the specified repository into the present working directory

    Performs a shallow git clone of the specified repository into the present
    working directory of the file system.

    Args:
      repository: The repository information in a JSON format (dictionary)

    """

    self._logger.info("Cloning Repository %s" %repository['uniqueName'])

    currentAttempt = 0
    maxAttempts = 10  # The number of attempts to retry the API call
    successful = False

    # Keep trying to complete a successful clone (up to maxAttempts times)
    while not successful:
      process = subprocess.Popen(['git', 'clone', '--depth', '1',
                                 repository['url'],
                                 repository['uniqueName']],
                                 stdout=subprocess.PIPE,
                                 stderr=subprocess.PIPE,
                                 shell=False)
      output, error = process.communicate()

      # If the clone doesn't succeed wait 60 seconds and try again
      if len(error) > 0 and "fatal: destination path" not in error and \
         "error: unable to write sha1" not in error:
        self._logger.warn("Unsuccessful clone -> Error (%s " %error)
        currentAttempt += 1
        if currentAttempt <= maxAttempts:
          self._logger.info("Retrying clone %d/%d" %(currentAttempt,
                            maxAttempts))
          self._logger.info("Waiting 60 seconds")
          time.sleep(60)
        else:
          self._logger.warn("Max clone attempts exceeded")
          break

      else:
        successful = True

    return successful

  def _customHandleRepository(self, repository):
    """Executes the custom handle function on the repository

    This function is implemented by the user, and can include anything. The
    user is given the repository dictionary, and is able to navigate the
    directory that contains the cloned repository. The cloned repository is
    located under the present working directory with the name found from
    repository['uniqueName'].

    Performs a shallow git clone of the specified repository into the present
    working directory of the file system.

    Args:
      repository: The repository information in a JSON format (dictionary)

    """

    # Replace with own implementation
    # self._logger.info("Executing custom handle function on repository")
    pass

  def _isStatementInRepository(self, repository):
    """Searches within the repository for the source statements

    Searches for the source statements using a recursive egrep command.

    Args:
      repository: The repository information in a JSON format (dictionary)

    Returns:
      True if the statement was found, otherwise false

    """

    self._logger.info("Grepping for sourceStatements (%s)"
                      %self._sourceStatements)
    process = subprocess.Popen(['egrep', self._sourceStatements, '-riswl',
                                repository['uniqueName'],
                                '--exclude-dir=*/.git/*'],
                                stdout=subprocess.PIPE, shell=False)
    output, error = process.communicate()

    if len(output) > 0:
      self._logger.info("Statements found")
      return True
    else:
      self._logger.info("Statements not found")
      return False

  def _cleanRepository(self, repository):
    """Cleans up the cloned repository

    Recursively removes the cloned repository from the file system.

    Args:
      repository: The repository information in a JSON format (dictionary)

    """

    process = subprocess.Popen(['rm', '-rf', repository['uniqueName']],
                                stdout=subprocess.PIPE, shell=False)
    output, error = process.communicate()
    self._logger.info("Removed cloned repository")

  def _examineRepository(self, repository):
    """Examines the repository and acquires all the information from it

    An individual repository is handled here by acquiring all of its general
    information. To acquire the language information, another GitHub API call
    is needed. The total size of the repository is also calculated here based
    on the individual languages.

    Args:
      repository: The repository that will be examined to acquire information

    Returns:
      List of language size for repository.
      Total size of the repository (in terms of languages)
    """
    totalSize = 0
    allInfo = []
    repositoryLanguages = self._apiHandler.getLanguages(repository)

    if repositoryLanguages == None:
      return None, None

    for language in self._languages:
      try:
        allInfo.append(repositoryLanguages[language])
        totalSize += repositoryLanguages[language]
      except KeyError: allInfo.append(0)

    # If there is content in the repository then the data is useful
    if totalSize > 0:

      # Acquire list of all the repository information
      for info in self._headers:
        try: allInfo.append(repository[info].encode("utf-8"))
        except KeyError: allInfo.append(0)
        except AttributeError: allInfo.append(repository[info])

    return totalSize, allInfo
