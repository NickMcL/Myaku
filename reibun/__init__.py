"""Package containing all components of the Reibun app."""
from typing import Dict

import reibun.japanese_analysis
from reibun._version import __version__


def get_version_info() -> Dict[str, str]:
    """Returns a dict with all Reibun-related version info.

    In addition to the version of this reibun Python package, the returned dict
    includes the versions of the resources outside of the module such as
    Japanese dictionaries currently being used by Reibun.
    """
    version_info = {}
    version_info['reibun_package'] = __version__
    version_info.update(
        reibun.japanese_analysis.get_resource_version_info()
    )

    return version_info
