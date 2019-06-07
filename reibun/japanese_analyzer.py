"""Utilities for analyzing Japanese text."""

import gzip
import logging
import os
import shutil
import subprocess
import sys
import urllib
from contextlib import closing
from typing import Optional, Set
from xml.etree import ElementTree

import MeCab

import reibun.utils as utils

_log = logging.getLogger(__name__)

_RESOURCE_FILE_DIR = os.path.dirname(os.path.realpath(__file__))

_MECAB_NEOLOGD_DIR_NAME = 'mecab-ipadic-neologd'
_MECABRC_PATH = os.path.join(_RESOURCE_FILE_DIR, 'mecabrc')
_MECABRC_CONTENT_FORMAT = 'dicdir = {dict_path}\n'
_MECAB_PYTHON_MECABRC_KEY = 'MECABRC'

_JMDICT_XML_FILEPATH = os.path.join(_RESOURCE_FILE_DIR, 'JMdict_e.xml')
_JMDICT_GZ_FILEPATH = os.path.join(_RESOURCE_FILE_DIR, 'JMdict_e.gz')
_JMDICT_LATEST_FTP_URL = 'ftp://ftp.monash.edu.au/pub/nihongo/JMdict_e.gz'

_JMDICT_KANJI_ELEMENT_TAG = 'k_ele'
_JMDICT_KANJI_REP_ELEMENT_TAG = 'keb'
_JMDICT_READING_ELEMENT_TAG = 'r_ele'
_JMDICT_READING_REP_ELEMENT_TAG = 'reb'

utils.toggle_reibun_debug_log()


def update_dictionary_files() -> None:
    """Downloads the latest versions of dict files used for JPN analysis."""
    _update_jmdict_files()


def _update_jmdict_files() -> None:
    """Downloads and unpacks the latest JMdict files."""
    _log.debug(
        f'Downloading JMdict gz file from {_JMDICT_LATEST_FTP_URL} to '
        f'{_JMDICT_GZ_FILEPATH}'
    )
    with closing(urllib.request.urlopen(_JMDICT_LATEST_FTP_URL)) as response:
        with open(_JMDICT_GZ_FILEPATH, 'wb') as jmdict_gz_file:
            shutil.copyfileobj(response, jmdict_gz_file)

    _log.debug(
        f'Decompressing {_JMDICT_GZ_FILEPATH} to {_JMDICT_XML_FILEPATH}'
    )
    with gzip.open(_JMDICT_GZ_FILEPATH, 'rb') as jmdict_decomp_file:
        with open(_JMDICT_XML_FILEPATH, 'wb') as jmdict_xml_file:
            shutil.copyfileobj(jmdict_decomp_file, jmdict_xml_file)

    _log.debug(f'Removing {_JMDICT_GZ_FILEPATH}')
    os.remove(_JMDICT_GZ_FILEPATH)


class InitFailureError(Exception):
    """Raised when an analyzer fails to initialize."""
    pass


@utils.add_method_debug_logging
class JapaneseTextAnalyzer(object):
    """Analyzes Japanese text to determine used words and phrases."""

    def __init__(self) -> None:
        self._jmdict_entries = self._load_jmdict_entries(_JMDICT_XML_FILEPATH)
        self._mecab_tagger = self._init_mecab_tagger()

    @utils.skip_method_debug_logging
    def _get_jmdict_reprs(self, jmdict_entry: ElementTree.Element) -> Set[str]:
        """Get all representations for a given JMdict XML element.

        Because many Japanese words can be written using kanji as well as kana,
        there are often different ways to write the same word. JMdict entries
        include each or these representations as seperate elements, so this
        function parses all of the representations for a given entry and adds
        them to a set.

        DEBUG_SKIP

        Args:
            jmdict_entry: An XML entry element from a JMdict XML file.

        Returns:
            A set of all of the representations for the given entry.
        """
        reprs = set()
        for element in jmdict_entry:
            if element.tag == _JMDICT_KANJI_ELEMENT_TAG:
                reprs.add(element.find(_JMDICT_KANJI_REP_ELEMENT_TAG).text)
            elif element.tag == _JMDICT_READING_ELEMENT_TAG:
                reprs.add(element.find(_JMDICT_READING_REP_ELEMENT_TAG).text)

        return reprs

    def _load_jmdict_entries(self, filepath: str) -> Set[str]:
        """Loads string entries from a JMdict XML file into a set."""
        if not os.path.exists(filepath):
            _log.error(f'JMdict file not found at {_JMDICT_XML_FILEPATH}')
            raise InitFailureError(
                f'JMdict file not found at {_JMDICT_XML_FILEPATH}'
            )

        _log.debug(f'Loading JMdict file from {_JMDICT_XML_FILEPATH}')
        tree = ElementTree.parse(filepath)
        _log.debug('Loading of JMdict file complete')

        entries = set()
        root = tree.getroot()
        for entry in root:
            entries.update(self._get_jmdict_reprs(entry))

        return entries

    def _get_mecab_neologd_dict_path(self) -> Optional[str]:
        """Attempts to find the path to the NEologd dict in the system.

        This function is best effort. Logs warning if NEologd dictionary cannot
        be found on the system.

        Returns:
            The path to the directory containing the NEologd dictionary, or
            None if the NEologd dictionary could not be found.
        """
        output = subprocess.run(['mecab-config', '--version'])
        if output.returncode != 0:
            _log.warning(
                'MeCab is not installed on this system, so the '
                'mecab-ipadic-NEologd dictionary cannot be used.'
            )
            return None

        output = subprocess.run(
            ['mecab-config', '--dicdir'], capture_output=True
        )
        if output.returncode != 0:
            _log.warning(
                'MeCab dictionary directory could not be retrieved, so the '
                'mecab-ipadic-NEologd dictionary cannot be used.'
            )
            return None

        neologd_path = os.path.join(
            output.stdout.decode(sys.stdout.encoding).strip(),
            _MECAB_NEOLOGD_DIR_NAME
        )
        if not os.path.exists(neologd_path):
            _log.warning(
                'mecab-ipadic-NEologd is not installed on this system, so the '
                'mecab-ipadic-NEologd dictionary cannot be used.'
            )
            return None

        return neologd_path

    def _init_mecab_tagger(self) -> MeCab.Tagger:
        """Init and return the MeCab tagger used by the analyzer.

        Attempts to use the mecab-ipadic-NEologd dictionary if available on the
        system. Logs warning if NEologd cannot be used, and, in that case,
        mecab-python3 will use the default mecab-ipadic dictionary instead.
        """
        neologd_path = self._get_mecab_neologd_dict_path()
        if neologd_path:
            return MeCab.Tagger(f'-Ochasen -d {neologd_path}')
        return MeCab.Tagger('-Ochasen')
