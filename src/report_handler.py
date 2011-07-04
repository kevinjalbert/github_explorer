import logging
import csv

class ReportHandler():

  """This class handles the reporting of the gathered repository information

  The report generated consists of the information of the gather repository
  information. The reports can be generated in the implemented formates which
  is currently only CSV. The reports are placed in the present working
  directory called "repository_report.ext" where ext is the file extension.

  """

  # The CSV column headers
  _headers = None

  # List of all recognized GitHub languages
  _languages = None

  # The CSV report's file name
  _CSV_NAME = "repository_report.csv"

  # Logger being used for this execution
  _logger = None

  def __init__(self, headers, languages, logger):
    """Constructor that initializes the ReportHandler

    This constructor sets the list of languages and headers so the reports
    have the fields of the values being passed to it. The ordering of the data
    and the headers/languages must match.

    Args:
      headers: The list of headers as fields for the report
      languages: The list of languages as fields for the report
      logger: The custom logger to be used for this executing process

    """

    self._headers = headers
    self._languages = languages
    self._logger = logger

  def readyCSVReport(self):
    """Creates the CSV report with the necessary header

    This function creates the CSV report file with the necessary header.

    """

    csv_file = open(self._CSV_NAME,'wb')
    csv_writer = csv.writer(csv_file)

    header = []
    header.extend(self._headers)
    header.extend(self._languages)
    header.pop()
    csv_writer.writerow(header)

    csv_file.close()
    self._logger.info("CSV report file is ready")

  def appendCSVData(self, data):
    """Appends new data to the CSV report

    This function appends new data of the past repository page to the already
    present CSV report (created via the readyCSVReport function).

    Args:
      data: The list of new data from the last page of repositories

    """

    csv_file = open(self._CSV_NAME,'a')
    csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_NONNUMERIC)

    csv_writer.writerows(data)

    csv_file.close()
    self._logger.info("Repository data appended to CSV report")
