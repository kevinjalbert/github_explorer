import argparse
import logging
import threading
import github_explorer

"""This python file drives multiple GitHub Explorer program concurrently

Multiple GitHub Explorer processes are started at the same time and given a
specific process number that dictates what repository page intervals it should
handle. Each process will have it's own logger that will log the progress in
individual log files. It's still possible to manually orchestrate the multiple
GitHub Explorer programs by making use of the -p and -m parameters in the
GitHub Explorer program.

"""


def _task(language, keywords, sourceStatements, clone, processNumber,
         maxProcesses):
  """This task is a single execution of the GitHub Explorer program

  This function is used in the threading approach to running multiple GitHub
  Explorer programs. A specific logger is created for the new execution of the
  GitHub Explorer.

  Args:
    language: A filter of the primary language for the repositories
    keywords: Filter of keywords for the repositories
    sourceStatements: Filter of source statements for the repositories
    clone: Flag that indicates repositories should be cloned
    processNumber: The current processNumber of this concurrent execution
    maxProcesses: The maximum number of concurrent processes executing

  """

  # Create custom logger to be used within new GitHub Explorer process
  logger = logging.getLogger("logger" + str(processNumber))
  handler = logging.FileHandler("worker_log_" + str(processNumber), "w")
  logger.setLevel(logging.DEBUG)
  formatter = logging.Formatter("%(asctime)s %(levelname)-8s P" +
                                str(processNumber) +
                                " %(message)s", datefmt="%d %b %H:%M:%S")
  handler.setFormatter(formatter)
  logger.addHandler(handler)

  # Create the GitHub Explorer which starts the process
  gitHubExplorer = github_explorer.GitHubExplorer(language, keywords,
      sourceStatements, clone, processNumber, maxProcesses, True, logger)

# If this module is ran as main
if __name__ == '__main__':

  # Define the argument options to be parsed
  parser = argparse.ArgumentParser(
      description="<https://github.com/kevinjalbert/github_explorer>",
      version="github_explorer_driver 0.3.0")
  parser.add_argument(
      '-m',
      action='store',
      default=1,
      dest='maxProcesses',
      help="The maximum number of concurrent executions (Manually done, or "
           "through the driver.py interface)")
  parser.add_argument(
      '-c',
      action='store_true',
      default=False,
      dest='clone',
      help="Enables repositories to be cloned for analysis and more accuracy "
           "(source statements can only be search if this is enabled)")
  parser.add_argument(
      '-l',
      action='store',
      default="",
      dest='language',
      help="Primary language to search for using GitHub's defined set of "
           "languages (ex: Python)")
  parser.add_argument(
      '-k',
      action='store',
      default="",
      dest='keywords',
      help="Keywords to be used in the search (ex: \"Testing Concurrency "
           "Android\")")
  parser.add_argument(
      '-s',
      action='store',
      default="",
      dest='sourceStatements',
      help="Source Statements to be used in the detailed search (ex: "
           "\"java.util synchronized latch\"), able to search with multiple "
           "terms (this-or-that)")

  userArgs = parser.parse_args()

  workers = []
  for processNumber in range(int(userArgs.maxProcesses)):
    worker = threading.Thread(target=_task, args=(userArgs.language,
                              userArgs.keywords, userArgs.sourceStatements,
                              userArgs.clone, processNumber + 1,
                              int(userArgs.maxProcesses)))
    workers.append(worker)
    worker.start()
