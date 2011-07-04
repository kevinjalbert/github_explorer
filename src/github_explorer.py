import argparse
import logging
import repository_handler

class GitHubExplorer():

  """This class drives the GitHub Explorer program

  This program explores GitHub repositories by using a keyword and language
  filter. Further analysis of the repositories can be carried out after cloning
  them and looking for specify words or statements within the files. A custom
  method can be tailored as well if the  user wants to perform anything in
  addition to the identification of relevant repositories. Additionally, the
  relevant repository information is stored in a report file.

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

  # List of repository information headers
  _headers = ["created", "created_at", "description", "followers", "fork",
      "forks", "has_downloads", "has_issues", "has_wiki", "homepage",
      "master_branch", "name", "open_issues", "owner", "private", "pushed",
      "pushed_at", "score", "size", "type", "url", "username", "watchers"]

  # Logger being used for this execution
  _logger = None

  def __init__(self, primaryLanguage, keywords, sourceStatements, clone, processNumber, maxProcesses, writeLog, logger=None):
    """Constructor that initializes the GitHubExplorer

    This constructor uses the specified parameters when setting up the rest of
    the instance. It will also handle the parameters in their own special way
    before they are used. The logging is handled in a specially way to ensure
    that each process will have a unique logger if the search is concurrent.

    Args:
      primaryLanguage: A filter of the primary language for the repositories
      keywords: Filter of keywords for the repositories
      sourceStatements: Filter of source statements for the repositories
      clone: Flag that indicates repositories should be cloned
      processNumber: The current processNumber of this concurrent execution
      maxProcesses: The maximum number of concurrent processes executing
      writeLog: Flag that indicates that the log file should be written out
      logger: The custom logger to be used for this executing process

    """

    # If there is no logger passed, then form a basic one; otherwise use given
    if logger == None:

      logger = logging.getLogger("logger")
      handler = None

      if writeLog:
        handler = logging.FileHandler("worker_log_" + str(processNumber), "w")
      else:
        handler = logging.StreamHandler()

      logger.setLevel(logging.DEBUG)
      formatter = logging.Formatter("%(asctime)s %(levelname)-8s P" + str(processNumber) + " %(message)s", datefmt="%d %b %H:%M:%S")
      handler.setFormatter(formatter)
      logger.addHandler(handler)
      self._logger = logger

    else:
      self._logger = logger

    # Check to see if process numbers are valid; exit if necessary
    if processNumber > maxProcesses or processNumber < 0:
      self._logger.fatal("The number of process is invalid, exiting now")
      exit()

    if primaryLanguage not in self._languages:
      self.logger.fatal("%s is not not valid language, so using no set language" %(primaryLanguage))
      primaryLanguage = ""

    primaryLanguage = self._cleanInput(primaryLanguage)  # Must clean the input
    keywords = '+'.join(keywords.split())  # Join words with +
    sourceStatements = '|'.join(sourceStatements.split())  # Join words with |

    # Create the repository handler and start crawling
    self._logger.info("GitHub Explorer is about to commence its search")
    repositoryHandler = repository_handler.RepositoryHandler(self._headers, self._languages, primaryLanguage, keywords, sourceStatements, clone, processNumber, maxProcesses, logger)
    repositoryHandler.crawlRepositories()

  def _cleanInput(self, input):
    """Cleans the input from special characters

    GitHub's language parameter can have special characters that can break the
    search functionality, thus they must be cleaned first.

    Args:
      input: The string that will be cleansed from special characters

    Returns:
      The input that has been cleansed from special characters

    """

    input = input.replace(":", "%3A")
    input = input.replace("/", "%2F")
    input = input.replace("#", "%23")
    input = input.replace("+", "%2B")

    return input

# If this module is ran as main
if __name__ == '__main__':

  # Define the argument options to be parsed
  parser = argparse.ArgumentParser(
      description = 'github_crawler <https://github.com/kevinjalbert/github_explorer>',
      version = 'github_explorer 0.3.0')
  parser.add_argument(
      '-p',
      action='store',
      default=1,
      dest='processNumber',
      help='The process number of this executing (Manually done, or through the driver.py interface)')
  parser.add_argument(
      '-m',
      action='store',
      default=1,
      dest='maxProcesses',
      help='The maximum number of concurrent executions (Manually done, or through the driver.py interface)')
  parser.add_argument(
      '-c',
      action='store_true',
      default=False,
      dest='clone',
      help='Enables repositories to be cloned for additional analysis and accuracy (source statements can only be search if this is enabled)')
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
      help='Keywords to be used in the search (ex: "Testing Concurrency Android")')
  parser.add_argument(
      '-s',
      action='store',
      default="",
      dest='sourceStatements',
      help='Source Statements to be used in the detailed search (ex: "java.util synchronized latch"), able to search with multiple terms (this-or-that)')
  parser.add_argument(
      '-w',
      action='store_true',
      default=False,
      dest='writeLog',
      help='Enables the output to be written to a log file')

  userArgs = parser.parse_args()

  # Create the GitHub Explorer which starts this process
  gitHubExplorer = GitHubExplorer(userArgs.language, userArgs.keywords, userArgs.sourceStatements, userArgs.clone, int(userArgs.processNumber), int(userArgs.maxProcesses), userArgs.writeLog)
