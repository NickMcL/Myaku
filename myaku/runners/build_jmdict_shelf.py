"""Builder for a shelf for quick loading of JMdict data."""

import logging

from myaku import utils
from myaku.japanese_analysis import JapaneseTextAnalyzer

_log = logging.getLogger(__name__)


def main() -> None:
    """Build a shelf for JMdict data."""
    utils.toggle_myaku_package_log(filename_base='build_shelf')

    # Creating a JapanenTextAnalyzer object will automatically create the
    # JMdict shelf if it's not already created.
    JapaneseTextAnalyzer()


if __name__ == '__main__':
    _log = logging.getLogger('myaku.runners.build_cache')
    try:
        main()
    except BaseException:
        _log.exception('Unhandled exception in main')
        raise
