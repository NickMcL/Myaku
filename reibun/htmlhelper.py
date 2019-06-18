"""Util functions for parsing HTML."""

import logging
import re
from datetime import datetime
from typing import List, Optional, Union

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

import reibun.utils as utils

_log = logging.getLogger(__name__)


class HtmlHelper(object):
    """Helper functions for HTML parsing."""
    _HTML_TAG_REGEX = re.compile(r'<.*?>')

    _RUBY_TAG_REGEX = re.compile(r'</?ruby.*?>')
    _RT_CONTENT_REGEX = re.compile(r'<rt.*?>.*?</rt>')
    _RP_CONTENT_REGEX = re.compile(r'<rp.*?>.*?</rp>')

    _ALLOWABLE_HTML_TAGS_IN_TEXT = {
        'a', 'b', 'blockquote', 'br', 'em', 'span', 'strong', 'sup'
    }

    _TIME_TAG_DATETIME_FORMAT = '%Y-%m-%dT%H:%M'

    def __init__(self, error_handler=None):
        """Inits with the given error handling function.

        Args:
            error_handler: A function to be called with an error message as the
                first arg anytime a method has an unexpected error parsing
                HTML. If None, will just debug log the errors.
        """
        if error_handler is not None:
            self._error_handler = error_handler
        else:
            self._error_handler = _log

    def parse_valid_child_text(self, tag: Tag) -> Optional[str]:
        """Parses the child text within an HTML tag if valid.

        The child text of an HTML tag is considered invalid and will not be
        parsed by this function if any of the descendants of the tag are
        structural HTML elements such as section, div, p, h1, etc.

        See _ALLOWABLE_HTML_TAGS_IN_TEXT for a set of HTML tags allowable as
        descendants for a tag with valid child text under this definition.

        Args:
            tag: HTML tag whose child text to attempt to parse.

        Returns:
            The child text of tag, or None if the tag contained no text
            elements OR if the child text was considered invalid for parsing.
        """
        contains_text = False
        for descendant in tag.descendants:
            if (descendant.name is not None and
                    descendant.name not in self._ALLOWABLE_HTML_TAGS_IN_TEXT):
                return None

            if isinstance(descendant, NavigableString):
                contains_text = True

        if contains_text:
            return re.sub(self._HTML_TAG_REGEX, '', str(tag))
        else:
            return None

    def parse_text_from_desendant(
        self, parent: Tag, tag_name: str, classes: Union[str, List[str]]
    ) -> Optional[str]:
        """Parses the text from a tag_name descendant within parent.

        Considers it an error if more than one tag_name descendant with the
        specified classes exists within parent.

        Args:
            parent: The tag whose descendants to search.
            tag_name: The type of tag to parse the text from (e.g. span).
            classes: A single or list of classes that the class attribute of
                tag to parse text from must exactly match.

        Returns:
            The parsed text if the parse was successful, None otherwise.
        """
        found_tags = parent.find_all(tag_name, class_=classes)

        if len(found_tags) != 1:
            self._error_handler(
                'Found {} "{}" tags instead of 1 in: "{}"'.format(
                    len(found_tags), tag_name, parent
                )
            )
            return None

        text = self.parse_valid_child_text(found_tags[0])
        if text is None:
            self._error_handler(
                'Unable to determine text from "{}" tag "{}" in: "{}"'.format(
                    tag_name, found_tags[0], parent
                )
            )
            return None

        return text

    def parse_jst_time_desendant(self, parent: Tag) -> Optional[datetime]:
        """Parses the datetime from a time tag descendant with a JST time.

        Considers it an error if more than one time descendant exists within
        parent.

        JST is Japan Standard Time, the timezone used throughout Japan.

        Args:
            parent: The tag whose descendants to search for a time tag.

        Returns:
            UTC datetime parsed from a time tag desendant if the parse was
            successful, None otherwise.
        """
        time_tags = parent.find_all('time')

        if len(time_tags) != 1:
            self._error_handler(
                'Found {} time tags instead of 1 in "{}"'.format(
                    len(time_tags), parent
                )
            )
            return None

        if not time_tags[0].has_attr('datetime'):
            self._error_handler(
                'Time tag "{}" has no datetime attribute in: "{}"'.format(
                    time_tags[0], parent
                )
            )
            return None

        try:
            parsed_datetime = datetime.strptime(
                time_tags[0]['datetime'], self._TIME_TAG_DATETIME_FORMAT
            )
        except ValueError:
            self._error_handler(
                'Failed to parse datetime "{}" of "{}" in: "{}"'.format(
                    time_tags[0]["datetime"], time_tags[0], parent
                )
            )
            return None

        return utils.convert_jst_to_utc(parsed_datetime)

    def parse_link_desendant(
        self, parent: Tag, take_first: bool = False
    ) -> Optional[str]:
        """Parses the url from an <a> tag descendant.

        If take_first is False, considers it an error if more than one <a> tag
        descendant exists within parent.

        Args:
            parent: The tag whose descendants to search for a <a> tag.
            take_first: If True, returns the first <a> descendant found without
                checking if more exist.

        Returns:
            The link from an <a> tag descendant if the parse was successful,
            None otherwise.
        """
        link_tags = parent.find_all('a')

        if len(link_tags) == 0:
            self._error_handler(
                'Found 0 <a> tags in "{}"'.format(len(link_tags), parent)
            )
            return None

        if len(link_tags) > 1 and not take_first:
            self._error_handler(
                'Found {} <a> tags instead of 1 in "{}"'.format(
                    len(link_tags), parent
                )
            )
            return None

        if not link_tags[0].has_attr('href'):
            self._error_handler(
                '<a> tag "{}" has no href attribute in: "{}"'.format(
                    link_tags[0], parent
                )
            )
            return None

        return link_tags[0]['href']

    def parse_descendant_by_class(
        self, parent: Tag, tag_name: str, classes: Union[str, List[str]],
        allow_multiple: bool = False
    ) -> Optional[Union[Tag, List[Tag]]]:
        """Parses a tag_name descendant with classes within parent.

        If allow_multiple != True, considers it an error if more than one
        tag_name descendant with the specified classes exists within parent.

        Args:
            parent: The tag whose descendants to search.
            tag_name: The type of tag to search for (e.g. span).
            classes: A single or list of classes that the class attribute of
                tag to parse text from must exactly match.
            allow_multiple: If True, it will not be an error if there are
                multiple descendants found and all of the found descendants
                will be returned in a list.

        Returns:
            The found tag_name tag(s) if the parse was successful, None
            otherwise.
        """
        tags = parent.find_all(tag_name, class_=classes)
        if len(tags) > 1 and not allow_multiple:
            self._error_handler(
                'Found {} "{}" tags with class(es) "{}" instead of 1 in '
                '"{}"'.format(
                    len(tags), tag_name, classes, parent
                )
            )
        if len(tags) == 0:
            self._error_handler(
                'Found 0 "{}" tags with class(es) "{}" in "{}"'.format(
                    tag_name, classes, parent
                )
            )

        if allow_multiple:
            return tags
        return tags[0]

    def strip_ruby_tags(self, tag: Tag) -> Tag:
        """Strips ruby tags from within the given tag.

        Leaves the normal text within the ruby tag while striping out any
        content in the rt and rp tags.
        """
        html_str = str(tag)
        html_str = re.sub(self._RT_CONTENT_REGEX, '', html_str)
        html_str = re.sub(self._RP_CONTENT_REGEX, '', html_str)
        html_str = re.sub(self._RUBY_TAG_REGEX, '', html_str)

        soup = BeautifulSoup(html_str, 'html.parser')
        return soup.contents[0]
