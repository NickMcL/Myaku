"""Exceptions raised by the reibun package."""


class CannotAccessPageError(Exception):
    """A page navigated to by a crawler could not be accessed.

    This could be due to an HTTP error, but it could also be due to a website's
    url structure unexpectedly changing among other possible issues.
    """
    pass


class CannotParsePageError(Exception):
    """A crawler was unable to parse an article from a page."""
    pass


class EnvironmentNotSetError(Exception):
    """A needed parameter from the environment was not set."""
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


class TextAnalysisError(Exception):
    """An unexpected error occurred related to text analysis."""
    pass
