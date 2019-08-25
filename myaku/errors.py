"""Exceptions raised by the myaku package."""


class CannotAccessPageError(Exception):
    """A page navigated to by a crawler could not be accessed.

    This could be due to an HTTP error, but it could also be due to a website's
    url structure unexpectedly changing among other possible issues.
    """
    pass


class DbPermissionError(Exception):
    """A database operation was attempted without proper permissions.

    For example, if a read-only client connection to the database was used to
    perform a write operation to the database.
    """
    pass


class EnvironmentNotSetError(Exception):
    """A needed parameter from the environment was not set."""
    pass


class HtmlParsingError(Exception):
    """Parsing for a segement of HTML failed."""
    pass


class MissingDataError(Exception):
    """Data needed for an operation is missing.

    For example, if an Article method is called that depends on certain attrs
    of the Article having data set, but those attrs are not set.
    """
    pass


class ResourceLoadError(Exception):
    """A necessary external resource failed to load.

    For example, a Japanese analyzer fails to load a dictionary file necessary
    for its operation.
    """
    pass


class ResourceNotReadyError(Exception):
    """A resource was used before it was ready to be used.

    For example, trying to use an object interface to an external dictionary
    before the dictionary has been loaded.
    """
    pass


class ScriptArgsError(Exception):
    """The arguments passed to a script were invalid."""
    pass


class TextAnalysisError(Exception):
    """An unexpected error occurred related to text analysis."""
    pass
