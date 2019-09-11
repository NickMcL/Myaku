"""Util functions for parsing HTML."""

import logging
import re
from datetime import datetime
from typing import List, Optional, Union

from bs4 import BeautifulSoup
from bs4.element import NavigableString, Tag

from myaku import utils
from myaku.errors import HtmlParsingError

_log = logging.getLogger(__name__)

_HTML_TAG_REGEX = re.compile(r'<.*?>')

_RUBY_TAG_REGEX = re.compile(r'</?ruby.*?>')
_RT_CONTENT_REGEX = re.compile(r'<rt.*?>.*?</rt>')
_RP_CONTENT_REGEX = re.compile(r'<rp.*?>.*?</rp>')
_ALLOWABLE_HTML_TAGS_IN_TEXT = {
    'a', 'b', 'blockquote', 'br', 'em', 'i', 'img', 'span', 'strong', 'sup'
}


def _raise_parsing_error(error_msg: str) -> None:
    """Raise and log error encountered during HTML parsing."""
    utils.log_and_raise(_log, HtmlParsingError, error_msg)


def parse_valid_child_text(
    parent: Tag, raise_on_no_text: bool = True
) -> Optional[str]:
    """Parse the child text within an HTML tag if valid.

    The child text of an HTML tag is considered invalid and will not be
    parsed by this function if any of the descendants of the tag are
    structural HTML elements such as section, div, p, h1, etc.

    See _ALLOWABLE_HTML_TAGS_IN_TEXT for a set of HTML tags allowable as
    descendants for a tag with valid child text under this definition.

    Args:
        parent: HTML tag whose child text to attempt to parse.
        raise_on_no_text: If True, will raise an HtmlParsingError if no valid
            child text could be parsed from the parent. If False, will return
            None in that case instead of raising an error.

    Returns:
        The valid child text of tag, or None if the tag contained no valid
        child text could be parsed from the parent.

    Raises:
        HtmlParsingError: raise_on_no_text is True and no valid child text
            could be parsed from the parent.
    """
    for descendant in parent.descendants:
        if (descendant.name is not None
                and descendant.name not in _ALLOWABLE_HTML_TAGS_IN_TEXT):
            if raise_on_no_text:
                _raise_parsing_error(
                    'Structural tag "{}" found while parsing child text in: '
                    '"{}"'.format(descendant, parent)
                )
            else:
                return None

    if not any(isinstance(d, NavigableString) for d in parent.descendants):
        if raise_on_no_text:
            _raise_parsing_error('No child text found in: "{}"'.format(parent))
        else:
            return None

    return re.sub(_HTML_TAG_REGEX, '', str(parent))


def parse_text_from_descendant_by_class(
    parent: Tag, classes: Union[str, List[str]], tag_name: str = '',
    tag_index: int = 0, expected_tag_count: int = 1
) -> str:
    """Parse the text from a tag_name descendant of parent with classes.

    Args:
        parent: Tag whose descendants to search.
        classes: Single or list of classes that the tag to parse text
            from must have.
        tag_name: Type of tag to parse the text from (e.g. span). An
            emptry string matches any tag.
        tag_index: Ordinal index of the tag to parse out of the list of
            tag_name descendants with the classes (i.e. 0 would parse the first
            tag_name descendant with classes, 1 would parse the second, etc.).

            The indexing starts at 0 and proceeds in depth-first order from the
            parent.
        expected_tag_count: Expected number of tag_name descendants with
            classes. If the total tag_name descendants with classes is not
            equal to this amount, an HtmlParsingError will be raised.

            If None, will not raise an exception as long as the total matched
            tag descendants is >= tag_index.

    Returns:
        The parsed text.

    Raises:
        HtmlParsingError: There was an issue parsing text from a tag_name
            descendant with classes from the given parent.
    """
    if not isinstance(classes, list):
        classes = [classes]

    found_tags = parent.select(
        '{}.{}'.format(tag_name, '.'.join(classes))
    )
    if (expected_tag_count is not None
            and len(found_tags) != expected_tag_count):
        _raise_parsing_error(
            'Found {} "{}" tags with class(es) "{}" instead of {} in: '
            '"{}"'.format(
                len(found_tags), tag_name, classes, expected_tag_count, parent
            )
        )

    text = parse_valid_child_text(found_tags[tag_index], False)
    if text is None:
        _raise_parsing_error(
            'Unable to determine text from "{}" tag "{}" in: "{}"'.format(
                tag_name, found_tags[tag_index], parent
            )
        )

    return text


def parse_text_from_descendant_by_id(parent: Tag, tag_id: str) -> str:
    """Parse the text from a tag_name descendant with id.

    Args:
        parent: Tag whose descendants to search.
        tag_id: Id that the tag to parse text from must have.

    Returns:
        The parsed text.

    Raises:
        HtmlParsingError: There was an issue parsing text from a tag_name
            descendant with id from the given parent.
    """
    found_tags = parent.find_all(id=tag_id)

    if len(found_tags) != 1:
        _raise_parsing_error(
            'Found {} tags with id "{}" instead of 1 in: "{}"'.format(
                len(found_tags), tag_id, parent
            )
        )

    text = parse_valid_child_text(found_tags[0], False)
    if text is None:
        _raise_parsing_error(
            'Unable to determine text from "{}" in: "{}"'.format(
                found_tags[0], parent
            )
        )

    return text


def parse_text_from_descendant_by_tag(
    parent: Tag, tag_name: str = '', tag_index: int = 0,
    expected_tag_count: int = 1
) -> str:
    """Parse the text from a tag_name descendant of parent.

    Args:
        parent: Tag whose descendants to search.
        tag_name: Type of tag to parse the text from (e.g. span).
        tag_index: Ordinal index of the tag to parse out of the list of
            tag_name descendants (i.e. 0 would parse the first tag_name
            descendant, 1 would parse the second, etc.).

            The indexing starts at 0 and proceeds in depth-first order from the
            parent.
        expected_tag_count: Expected number of tag_name descendants. If the
            total tag_name descendants is not equal to this amount, an
            HtmlParsingError will be raised.

            If None, will not raise an exception as long as the total matched
            tag descendants is >= tag_index.

    Returns:
        The parsed text.

    Raises:
        HtmlParsingError: There was an issue parsing text from a tag_name
            descendant from the given parent.
    """
    found_tags = parent.select(tag_name)
    if (expected_tag_count is not None
            and len(found_tags) != expected_tag_count):
        _raise_parsing_error(
            'Found {} "{}" tags instead of {} in: "{}"'.format(
                len(found_tags), tag_name, expected_tag_count, parent
            )
        )

    text = parse_valid_child_text(found_tags[tag_index], False)
    if text is None:
        _raise_parsing_error(
            'Unable to determine text from "{}" tag "{}" in: "{}"'.format(
                tag_name, found_tags[tag_index], parent
            )
        )

    return text


def parse_time_descendant(
    parent: Tag, datetime_format: str, convert_from_jst: bool = False,
    tag_index: int = 0, expected_tag_count: int = 1
) -> datetime:
    """Parse the datetime from a time tag descendant.

    If no timezone is specified in the datetime attr of the time element,
    assumes the time JST (Japan Standard Time) and coverts to UTC.

    Args:
        parent: Tag whose descendants to search for a time tag.
        datetime_format: Format to use with strptime to parse the datetime attr
            of the time tag.
        convert_from_jst: If True, will convert the parsed datetime from JST
            (Japan Standard Time) to UTC. If False, assumes the parsed time is
            in UTC and requires no conversion.
        tag_index: Ordinal index of the time tag to parse out of the list of
            time tag descendants (i.e. 0 would parse the first time tag
            descendant, 1 would parse the second, etc.).

            The indexing starts at 0 and proceeds in depth-first order from the
            parent.
        expected_tag_count: Expected number of time descendants. If the total
            time tag descendants is not equal to this amount, an
            HtmlParsingError will be raised.

            If None, will not raise an exception as long as the total time tag
            descendants is >= tag_index.

    Returns:
        UTC datetime parsed from the time tag descendant.

    Raises:
        HtmlParsingError: There was an issue parsing the datetime from the time
            descendant from the given parent.
    """
    time_tags = parent.select('time')

    if expected_tag_count is not None and len(time_tags) != expected_tag_count:
        _raise_parsing_error(
            'Found {} time tags instead of {} in "{}"'.format(
                len(time_tags), expected_tag_count, parent
            )
        )

    if not time_tags[tag_index].has_attr('datetime'):
        _raise_parsing_error(
            'Time tag "{}" has no datetime attribute in: "{}"'.format(
                time_tags[tag_index], parent
            )
        )

    try:
        parsed_datetime = datetime.strptime(
            time_tags[tag_index]['datetime'], datetime_format
        )
    except ValueError:
        _raise_parsing_error(
            'Failed to parse datetime "{}" of "{}" using format "{}" in: '
            '"{}"'.format(
                time_tags[tag_index]['datetime'], time_tags[tag_index],
                datetime_format, parent
            )
        )

    if convert_from_jst:
        return utils.convert_jst_to_utc(parsed_datetime)
    return parsed_datetime


def parse_link_descendant(
    parent: Tag, tag_index: int = 0, expected_tag_count: int = 1
) -> str:
    """Parse the href link from an <a> tag descendant.

    Args:
        parent: Tag whose descendants to search for a <a> tag.
        tag_index: Ordinal index of the <a> tag to parse out of the list of
            <a> tag descendants (i.e. 0 would parse the first <a> tag
            descendant, 1 would parse the second, etc.).

            The indexing starts at 0 and proceeds in depth-first order from the
            parent.
        expected_tag_count: Expected number of <a> tag descendants. If the
            total <a> tag descendants is not equal to this amount, an
            HtmlParsingError will be raised.

            If None, will not raise an exception as long as the total <a> tag
            descendants is >= tag_index.

    Returns:
        The href link from an <a> tag descendant.

    Raises:
        HtmlParsingError: There was an issue parsing the href link from the <a>
            tag descendant from the given parent.
    """
    link_tags = parent.select('a')

    if expected_tag_count is not None and len(link_tags) != expected_tag_count:
        _raise_parsing_error(
            'Found {} <a> tags instead of {} in: "{}"'.format(
                len(link_tags), expected_tag_count, parent
            )
        )

    if not link_tags[tag_index].has_attr('href'):
        _raise_parsing_error(
            '<a> tag "{}" has no href attribute in: "{}"'.format(
                link_tags[tag_index], parent
            )
        )

    return link_tags[tag_index]['href']


def parse_desc_list_data_text(desc_list: Tag, term_text: str) -> str:
    """Parse the associated data text for a term in a description list.

    Args:
        desc_list: Description list tag containing the entry to parse.
        term_text: Text contained by the <dt> element for the entry in the list
            whose data tag to parse.

    Returns:
        The text of the <dd> tag associated with the <dt> tag with text
        term_text in the given desc_list.

    Raises:
        HtmlParsingError: There was an issue parsing the given desc_list.
    """
    dt_tag = desc_list.find('dt', string=term_text)
    if dt_tag is None:
        _raise_parsing_error(
            'Could not find <dt> tag with text "{}" in: "{}"'.format(
                term_text, desc_list
            )
        )

    dd_tag = dt_tag.find_next_sibling('dd')
    if dd_tag is None:
        _raise_parsing_error(
            'Could not find <dd> tag after <dt> tag with text "{}" in: '
            '"{}"'.format(
                term_text, desc_list
            )
        )

    dd_text = parse_valid_child_text(dd_tag, False)
    if dd_text is None:
        _raise_parsing_error(
            '<dd> tag does not contain valid child text: "{}"'.format(dd_tag)
        )

    return dd_text


def select_desc_list_data(desc_list: Tag, term_text: str) -> str:
    """Select the associated data tag for a term in a description list.

    Args:
        desc_list: Description list tag containing the entry to parse.
        term_text: Text contained by the <dt> element for the entry in the list
            whose data tag to select.

    Returns:
        The <dd> tag associated with the <dt> tag with text term_text in the
        given desc_list.

    Raises:
        HtmlParsingError: There was an issue parsing the given desc_list.
    """
    dt_tag = desc_list.find('dt', string=term_text)
    if dt_tag is None:
        _raise_parsing_error(
            'Could not find <dt> tag with text "{}" in: "{}"'.format(
                term_text, desc_list
            )
        )

    dd_tag = dt_tag.find_next_sibling('dd')
    if dd_tag is None:
        _raise_parsing_error(
            'Could not find <dd> tag after <dt> tag with text "{}" in: '
            '"{}"'.format(
                term_text, desc_list
            )
        )

    return dd_tag


def select_descendants_by_class(
    parent: Tag, classes: Union[str, List[str]], tag_name: str = '',
    expected_tag_count: int = None
) -> List[Tag]:
    """Select tag_name descendant(s) with classes within parent.

    Args:
        parent: Tag whose descendants to search.
        classes: A single or list of classes that the tag to select must have.
        tag_name: Type of tag to search for (e.g. span). An empty
            string will match any tag.
        expected_tag_count: Expected number of selected tags. If the total
            selected tags is not equal to this amount, an HtmlParsingError
            will be raised.

            If None, no error will be raised if at least one tag is selected.

    Returns:
        The found tag_name descendant tag(s). If expected_tag_count == 1, will
        not return the tag in a list.

    Raises:
        HtmlParsingError: There was an issue parsing the html for the given
            parent.
    """
    if not isinstance(classes, list):
        classes = [classes]

    tags = parent.select('{}.{}'.format(tag_name, '.'.join(classes)))
    if expected_tag_count is not None and len(tags) != expected_tag_count:
        _raise_parsing_error(
            'Found {} "{}" tags with class(es) "{}" instead of {} in: '
            '"{}"'.format(
                len(tags), tag_name, classes, expected_tag_count, parent
            )
        )

    if len(tags) == 0:
        _raise_parsing_error(
            'Found 0 "{}" tags with class(es) "{}" in: "{}"'.format(
                tag_name, classes, parent
            )
        )

    return tags


def select_one_descendant_by_class(
    parent: Tag, classes: Union[str, List[str]], tag_name: str = ''
) -> Tag:
    """Select a single tag_name descendant with classes within parent.

    Raises an error if more or less than exactly 1 tag_name descendant exists
    within parent with classes.

    Args:
        parent: Tag whose descendants to search.
        classes: A single or list of classes that the tag to select must have.
        tag_name: Type of tag to search for (e.g. span). An empty
            string will match any tag.

    Returns:
        The found tag_name descendant tag.

    Raises:
        HtmlParsingError: There was an issue parsing the html for the given
            parent.
    """
    return select_descendants_by_class(parent, classes, tag_name, 1)[0]


def select_descendants_by_tag(
    parent: Tag, tag_name: str, expected_tag_count: int = None
) -> List[Tag]:
    """Select tag_name descendant(s) within parent.

    Args:
        parent: Tag whose descendants to search.
        tag_name: Type of tag to search for (e.g. span).
        expected_tag_count: Expected number of selected tags. If the total
            selected tags is not equal to this amount, an HtmlParsingError
            will be raised.

            If None, no error will be raised if at least one tag is selected.

    Returns:
        The found tag_name descendant tag(s).

    Raises:
        HtmlParsingError: There was an issue parsing the html for the given
            parent.
    """
    tags = parent.select(tag_name)
    if expected_tag_count is not None and len(tags) != expected_tag_count:
        _raise_parsing_error(
            'Found {} "{}" tags instead of {} in: "{}"'.format(
                len(tags), tag_name, expected_tag_count, parent
            )
        )

    if len(tags) == 0:
        _raise_parsing_error(
            'Found 0 "{}" tags in: "{}"'.format(tag_name, parent)
        )

    return tags


def select_one_descendant_by_tag(parent: Tag, tag_name: str) -> Tag:
    """Select a single tag_name descendant within parent.

    Raises an error if more or less than exactly 1 tag_name descendant exists
    within parent.

    Args:
        parent: Tag whose descendants to search.
        tag_name: Type of tag to search for (e.g. span).

    Returns:
        The found tag_name descendant tag.

    Raises:
        HtmlParsingError: There was an issue parsing the html for the given
            parent.
    """
    return select_descendants_by_tag(parent, tag_name, 1)[0]


def select_descendant_by_id(parent: Tag, id_: str) -> Tag:
    """Select the descendant with the given id within parent.

    Args:
        parent: Tag whose descendants to search.
        id_: Id that the tag to select must have.

    Returns:
        The found descendant tag with the given id.

    Raises:
        HtmlParsingError: There was an issue parsing the html for the given
            parent.
    """
    tag = parent.find(id=id_)
    if tag is None:
        _raise_parsing_error(
            'Found no tag with id "{}" in: "{}"'.format(id_, parent)
        )

    return tag


def descendant_with_class_exists(
    parent: Tag, classes: Union[str, List[str]], tag_name: str = ''
) -> bool:
    """Check if a tag_name descendent exists with classes within parent.

    Args:
        parent: Tag whose descendants to search.
        classes: A single or list of classes that the tag to parse must have.
        tag_name: Type of tag to search for (e.g. span). An empty string will
            match any tag.

    Returns:
        True if a tag_name descendent exists with classes with parent,
        False otherwise.
    """
    if not isinstance(classes, list):
        classes = [classes]

    tags = parent.select('{}.{}'.format(tag_name, '.'.join(classes)))
    return len(tags) != 0


def strip_ruby_tags(tag: Tag) -> Tag:
    """Strip ruby tags from within the given tag.

    Leaves the normal text within the ruby tag while striping out any
    content in the rt and rp tags.
    """
    html_str = str(tag)
    html_str = re.sub(_RT_CONTENT_REGEX, '', html_str)
    html_str = re.sub(_RP_CONTENT_REGEX, '', html_str)
    html_str = re.sub(_RUBY_TAG_REGEX, '', html_str)

    return BeautifulSoup(html_str, 'html.parser')
