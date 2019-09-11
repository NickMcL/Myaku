"""Package containing all components of the Myaku app."""

from typing import Dict

import myaku.japanese_analysis
from myaku._version import __version__

LOG_DIR_ENV_VAR = 'MYAKU_LOG_DIR'
APP_DATA_DIR_ENV_VAR = 'MYAKU_APP_DATA_DIR'


def get_version_info() -> Dict[str, str]:
    """Return a dict with all Myaku-related version info.

    In addition to the version of this myaku Python package, the returned dict
    includes the versions of the resources outside of the module such as
    Japanese dictionaries currently being used by Myaku.
    """
    version_info = {}
    version_info['myaku_python_package'] = __version__
    version_info.update(
        myaku.japanese_analysis.get_resource_version_info()
    )

    return version_info
