"""Module for creating previews of the article for a search result."""

import logging
import re
from collections import deque
from dataclasses import dataclass
from typing import Deque, Iterable, List, Tuple

from myaku import utils
from myaku.datastore import JpnArticleSearchResult
from myaku.datatypes import ArticleTextPosition, JpnArticle

_log = logging.getLogger(__name__)

_MIN_ACCEPTABLE_SAMPLE_LEN = 50
_MIN_IDEAL_SAMPLE_LEN = 70
_MAX_IDEAL_SAMPLE_LEN = 90
_MAX_ACCEPTABLE_SAMPLE_LEN = 100

_MAX_PREVIEW_ARTICLE_SAMPLES = 3
_MAX_PREVIEW_ARTICLE_PERCENT = 0.15

_TRIMMED_INDICATOR_STR = '...'
_MIN_CHARS_BETWEEN_MATCH_AND_TRIM = 8

_WHITESPACE_REGEX = re.compile(r'\s+')


def _collapse_whitespace(text: str) -> str:
    """Collapses blocks of whitespace in text into single spaces.

    Collapses whitespace into a full-width space (\u3000).
    """
    return _WHITESPACE_REGEX.sub('\u3000', text)


def _sentence_group_preview_quality_key(
    sentence_group: Tuple[ArticleTextPosition, Tuple[ArticleTextPosition, ...]]
) -> Tuple[int, int]:
    """Determines preview quality value of article sentence for sorting.

    Args:
        sentence_group: Sentence group returned by
            JpnArtilce.group_text_positions_by_sentence.

    Returns:
        A 2-tuples with the values ranking:
            1. How close the sentence lenght is to the ideal preview sentence
                length.
            2. How long the sentence lenght is.
    """
    sentence_len = sentence_group[0].len
    if _MIN_IDEAL_SAMPLE_LEN <= sentence_len <= _MAX_IDEAL_SAMPLE_LEN:
        return (2, sentence_len)
    elif _MIN_ACCEPTABLE_SAMPLE_LEN <= sentence_len < _MIN_IDEAL_SAMPLE_LEN:
        return (1, sentence_len)
    elif _MAX_IDEAL_SAMPLE_LEN < sentence_len <= _MAX_ACCEPTABLE_SAMPLE_LEN:
        return (0, sentence_len)
    elif sentence_len < _MIN_ACCEPTABLE_SAMPLE_LEN:
        return (-1, sentence_len)
    else:  # _MAX_ACCEPTABLE_SAMPLE_LEN < sentence_len
        return (-2, sentence_len)


@dataclass
class PreviewSampleTextSegment(object):
    """A single segment of a preview sentence for an article search result.

    Attributes:
        is_match_segment: True if the text of this segment matches the searched
            query, and False otherwise.
        text: Text for this segment of the sample sentence.
    """
    is_query_match: bool
    text: str


@dataclass
class PreviewSampleText(object):
    """Data for preview text for an article search result.

    Attributes:
        article: Article the sample text is from.
        text_len: Total length of the preview text.
        text_start_index: Starting index of the sample in the article text.
        segments: Segments that make up the sample text.
    """
    article: JpnArticle
    text_len: int
    text_start_index: int
    segments: List[PreviewSampleTextSegment]

    def get_humanized_text_position(self) -> str:
        """Gets a humanized string of the position of the text in article."""
        if self.text_start_index < len(self.article.title):
            return 'Article title'

        percent_pos = round(
            (self.text_start_index / len(self.article.full_text)) * 100
        )
        return '{}% into article'.format(percent_pos)


def _segments_len(segments: Iterable[PreviewSampleTextSegment]) -> int:
    """Returns the summed len of all of the segments in the list."""
    return sum(len(s.text) for s in segments)


class SearchResultArticlePreview(object):
    """Creates an appropriate preview of the article for a search result.

    An appropriate preview of an article is one that gives a decent view of how
    the queried term is used in the article without showing too much of the
    article.

    Attributes:
        main_sample_text: Main PreviewSampleText objects for the preview.
            Will always be set after init.
        extra_sample_texts: List of additional PreviewSampleText objects to
            use for the article preview.
            Will be an empty list if it was either not possible or not
            appropriate to have additional sample texts for this preview.
    """

    def __init__(self, search_result: JpnArticleSearchResult) -> None:
        """Creates an article preview for the given search result."""
        self._article = search_result.article
        sentence_groups = self._article.group_text_positions_by_sentence(
            search_result.found_positions
        )
        sentence_groups.sort(
            key=_sentence_group_preview_quality_key, reverse=True
        )

        # ID sentences by their start index
        self._sentence_found_positions_map = {
            g[0].start: g[1] for g in sentence_groups
        }
        self._used_sentences = set()

        sample_texts = self._create_all_sample_texts(sentence_groups)
        self.main_sample_text = sample_texts[0]
        self.extra_sample_texts = sample_texts[1:]

    def _create_all_sample_texts(
        self, sentence_groups: List[
            Tuple[ArticleTextPosition, Tuple[ArticleTextPosition, ...]]
        ]
    ) -> List[PreviewSampleText]:
        """Creates all the samples texts to use for the preview.

        Args:
            sentence_groups: List of tuples mapping the positions of each
                sentence in the article for the search result containing a
                match for the query to the positions of the text matching the
                query in that sentence.
                Should be sorted by the preview quality of the sentence.

        Returns:
            A list of the preview texts to use for the search result.
        """
        preview_texts = []
        article_len = len(_collapse_whitespace(self._article.full_text))
        for sentence_group in sentence_groups:
            if sentence_group[0].start in self._used_sentences:
                continue
            preview_texts.append(self._create_sample_text(*sentence_group))

            total_preview_len = sum(pt.text_len for pt in preview_texts)
            preview_article_percent = total_preview_len / article_len
            if (len(preview_texts) > 1
                    and (preview_article_percent
                         > _MAX_PREVIEW_ARTICLE_PERCENT)):
                preview_texts.pop()
                break

            if len(preview_texts) >= _MAX_PREVIEW_ARTICLE_SAMPLES:
                break

        return preview_texts

    def _create_sample_text(
        self, sentence_position: ArticleTextPosition,
        found_positions: Tuple[ArticleTextPosition]
    ) -> PreviewSampleText:
        """Creates a sample text from a sentence and matching text positions.

        Args:
            sentence_positions: Position of a sentence in the article for the
                search result.
            found_positions: List of positions of text in the given sentence
                that matches the search query.

        Returns:
            A sample text created containing as much of the given sentence as
            possible.
        """
        segments = self._create_sample_segments(
            sentence_position, found_positions
        )
        sample_text = PreviewSampleText(
            article=self._article,
            text_len=_segments_len(segments),
            text_start_index=sentence_position.start,
            segments=segments
        )
        self._used_sentences.add(sentence_position.start)

        if sample_text.text_len > _MAX_ACCEPTABLE_SAMPLE_LEN:
            self._trim_sample_text(sample_text)
        else:
            self._expand_sample_text(sample_text, sentence_position)

        return sample_text

    def _create_sample_segments(
        self, sample_position: ArticleTextPosition,
        found_positions: List[ArticleTextPosition]
    ) -> List[PreviewSampleTextSegment]:
        """Creates the text segments for a preview sample text.

        Args:
            sample_position: Article position of the sampel text.
            found_positions: Article positions where the text matching the
                search was found in the sample text.

        Returns:
            The PreviewSampleTextSegment objects for the sample text.
        """
        segments = []

        article_text = self._article.full_text
        last_end_index = sample_position.start
        for pos in found_positions:
            if last_end_index != pos.start:
                segment_text = article_text[last_end_index:pos.start]
                segments.append(PreviewSampleTextSegment(False, segment_text))
                last_end_index += len(segment_text)

            match_text = article_text[pos.slice()]
            segments.append(PreviewSampleTextSegment(True, match_text))
            last_end_index += pos.len

        sample_end_index = sample_position.start + sample_position.len
        end_text = article_text[last_end_index:sample_end_index]
        if len(end_text) > 0:
            segments.append(PreviewSampleTextSegment(False, end_text))

        segments[0].text = segments[0].text.lstrip()
        segments[-1].text = segments[-1].text.rstrip()
        for segment in segments:
            segment.text = _collapse_whitespace(segment.text)
        return segments

    def _get_max_query_match_bounds(
        self, sample_text: PreviewSampleText
    ) -> Tuple[int, int]:
        """Gets the bounds of the segments for the max acceptable query match.

        The max acceptable query match section is the continuous section of the
        sample text segments that has the most text positions matching the
        search query while being within _MAX_ACCEPTABLE_SAMPLE_LEN characters
        in total length.

        Args:
            sample_text: Sample text to get the indexes of its segments list
                for the max acceptable query match section.

        Returns:
            The indexes of the segments list for the given sample text that are
            the bounds of the max acceptable query match section for the sample
            text.
        """
        segs = sample_text.segments
        max_matches = -1
        for i, seg in enumerate(segs):
            if not seg.is_query_match:
                continue

            matches = 0
            section_len = 0
            last_match = i
            for j in range(i, len(segs)):
                section_len += len(segs[j].text)
                if section_len >= _MAX_ACCEPTABLE_SAMPLE_LEN:
                    break

                if not segs[j].is_query_match:
                    continue
                else:
                    last_match = j
                    matches += 1

            if matches > max_matches:
                max_matches = matches
                max_match_start = i
                max_match_end = last_match + 1

        return (max_match_start, max_match_end)

    def _append_segments_full_left_remainder_right(
        self, segs: List[PreviewSampleTextSegment],
        sub_segs: Deque[PreviewSampleTextSegment],
        sub_start_index: int, sub_end_index: int
    ) -> None:
        """Appends segs to sub segs using full left remainder right strategy.

        In this strategy, all segments to the left of the sub segment list are
        appended to its left, then characters from the segments to the right of
        the sub segment list are appended until the total lenght of the sub
        segment list reaches _MAX_ACCEPTABLE_SAMPLE_LEN.

        Args:
            segs: Full list of the segments considered.
            sub_segs: Deque of a sub-section of the given segs list.
            sub_start_index: Index in segs of the first segment in sub_segs.
            sub_end_index: Index in segs of the first segment not in sub_segs.

        Returns:
            The total number of characters in the segments added to the left of
            sub_segs.
        """
        sub_segs.extendleft(reversed(segs[0:sub_start_index]))
        sub_segs_len = _segments_len(sub_segs)
        if sub_segs_len < _MAX_ACCEPTABLE_SAMPLE_LEN:
            sub_segs.append(PreviewSampleTextSegment(
                False, segs[sub_end_index].text[
                    :_MAX_ACCEPTABLE_SAMPLE_LEN - sub_segs_len
                ]
            ))
        sub_segs.append(PreviewSampleTextSegment(
            False, _TRIMMED_INDICATOR_STR
        ))

        return len(sub_segs[0].text)

    def _append_segments_full_right_remainder_left(
        self, segs: List[PreviewSampleTextSegment],
        sub_segs: Deque[PreviewSampleTextSegment],
        sub_start_index: int, sub_end_index: int
    ) -> None:
        """Appends segs to sub segs using full right remainder left strategy.

        In this strategy, all segments to the right of the sub segment list are
        appended to its right, then characters from the segments to the left of
        the sub segment list are appended until the total lenght of the sub
        segment list reaches _MAX_ACCEPTABLE_SAMPLE_LEN.

        Args:
            segs: Full list of the segments considered.
            sub_segs: Deque of a sub-section of the given segs list.
            sub_start_index: Index in segs of the first segment in sub_segs.
            sub_end_index: Index in segs of the first segment not in sub_segs.

        Returns:
            The total number of characters in the segments added to the left of
            sub_segs.
        """
        left_added_chars = 0

        sub_segs.extend(segs[sub_end_index:])
        sub_segs_len = _segments_len(sub_segs)
        if sub_segs_len < _MAX_ACCEPTABLE_SAMPLE_LEN:
            sub_segs.appendleft(PreviewSampleTextSegment(
                False, segs[sub_start_index - 1].text[
                    -1 * (_MAX_ACCEPTABLE_SAMPLE_LEN - sub_segs_len):
                ]
            ))
            left_added_chars = len(sub_segs[0].text)
        sub_segs.appendleft(PreviewSampleTextSegment(
            False, _TRIMMED_INDICATOR_STR
        ))

        return left_added_chars

    def _append_segments_left_right_balance(
        self, segs: List[PreviewSampleTextSegment],
        sub_segs: Deque[PreviewSampleTextSegment],
        sub_start_index: int, sub_end_index: int
    ) -> None:
        """Appends segs to sub segs using left right balance strategy.

        In this strategy, characters from the segments to the left and right of
        sub segment list are evenly appended until the total length of the sub
        segment list reached _MAX_ACCEPTABLE_SAMPLE_LEN.

        Args:
            segs: Full list of the segments considered.
            sub_segs: Deque of a sub-section of the given segs list.
            sub_start_index: Index in segs of the first segment in sub_segs.
            sub_end_index: Index in segs of the first segment not in sub_segs.

        Returns:
            The total number of characters in the segments added to the left of
            sub_segs.
        """
        sub_segs_len = _segments_len(sub_segs)
        remaining_chars = _MAX_ACCEPTABLE_SAMPLE_LEN - sub_segs_len
        prev_seg_text = segs[sub_start_index - 1].text
        next_seg_text = segs[sub_end_index].text

        sub_segs.appendleft(PreviewSampleTextSegment(
            False, prev_seg_text[
                -1 * (remaining_chars // 2 + remaining_chars % 2)
            ]
        ))
        left_added_chars = len(sub_segs[0].text)
        sub_segs.appendleft(PreviewSampleTextSegment(
            False, _TRIMMED_INDICATOR_STR
        ))

        sub_segs.append(PreviewSampleTextSegment(
            False, next_seg_text[:remaining_chars // 2]
        ))
        sub_segs.append(PreviewSampleTextSegment(
            False, _TRIMMED_INDICATOR_STR
        ))

        return left_added_chars

    def _trim_sample_text(self, sample_text: PreviewSampleText) -> None:
        """Trims the sample text to be within the acceptable max length.

        Potentially can modify the text_len, text_start_index, and segments
        attrs of the given sample text object.

        Args:
            sample_text: Sample text to trim.
        """
        segs = sample_text.segments
        max_match_start, max_match_end = self._get_max_query_match_bounds(
            sample_text
        )
        trimmed_segs = deque(segs[max_match_start:max_match_end])
        trimmed_len = _segments_len(trimmed_segs)
        sample_text.text_start_index += _segments_len(segs[0:max_match_start])

        chars_from_start = _segments_len(segs[0:max_match_start])
        chars_to_end = _segments_len(segs[max_match_end:])
        if trimmed_len >= _MAX_ACCEPTABLE_SAMPLE_LEN:
            left_added_chars = 0
        elif (trimmed_len + chars_from_start
                + _MIN_CHARS_BETWEEN_MATCH_AND_TRIM
                <= _MAX_ACCEPTABLE_SAMPLE_LEN):
            left_added_chars = self._append_segments_full_left_remainder_right(
                segs, trimmed_segs, max_match_start, max_match_end
            )
        elif (trimmed_len + chars_to_end
                + _MIN_CHARS_BETWEEN_MATCH_AND_TRIM
                <= _MAX_ACCEPTABLE_SAMPLE_LEN):
            left_added_chars = self._append_segments_full_right_remainder_left(
                segs, trimmed_segs, max_match_start, max_match_end
            )
        else:
            left_added_chars = self._append_segments_left_right_balance(
                segs, trimmed_segs, max_match_start, max_match_end
            )

        sample_text.text_start_index -= left_added_chars
        sample_text.segments = list(trimmed_segs)
        sample_text.text_len = _segments_len(trimmed_segs)

    def _should_expand(
        self, segs: Iterable[PreviewSampleTextSegment],
        expand_segs: Iterable[PreviewSampleTextSegment]
    ) -> bool:
        """Checks if a segment expansion will improve the sample text quality.

        Args:
            segs: Current segments for a sample text.
            expand_segs: Segments being considered to expand segs with.

        Returns:
            True if expanding segs with expand_segs will create better sample
            text quality.
        """
        segs_current_len = _segments_len(segs)
        segs_expanded_len = segs_current_len + _segments_len(expand_segs)

        if _MIN_IDEAL_SAMPLE_LEN <= segs_expanded_len <= _MAX_IDEAL_SAMPLE_LEN:
            return True
        if _MIN_IDEAL_SAMPLE_LEN <= segs_current_len <= _MAX_IDEAL_SAMPLE_LEN:
            return False

        if (segs_current_len < _MIN_IDEAL_SAMPLE_LEN
                and segs_expanded_len < _MIN_IDEAL_SAMPLE_LEN):
            return True
        if (segs_current_len > _MAX_IDEAL_SAMPLE_LEN
                and segs_expanded_len > _MAX_IDEAL_SAMPLE_LEN):
            return False

        if (_MIN_IDEAL_SAMPLE_LEN - segs_current_len
                < segs_expanded_len - _MAX_IDEAL_SAMPLE_LEN):
            return False
        else:
            return True

    def _can_expand_left(self, pos: ArticleTextPosition) -> bool:
        """Returns True if it's possible to expand sample text to the left.

        Returns False when:
            - The start of the article is immediately to the left.
            - The title of the article is immediately to the left.
            - The sentence to the left has already been used in the preview.
        """
        if pos.start == 0:
            return False

        # Expansion from outside the title to inside it is not allowed
        left_start = utils.find_jpn_sentence_start(
            self._article.full_text, pos.start - 1
        )
        if (pos.start >= len(self._article.title)
                and left_start < len(self._article.title)):
            return False

        if left_start in self._used_sentences:
            return False

        return True

    def _paragraph_continues_left(self, pos: ArticleTextPosition) -> bool:
        """Returns True if the paragraph continues to the left of pos."""
        if pos.start == 0:
            return False
        return not self._article.full_text[pos.start - 1].isspace()

    def _get_left_sentence_segs(
        self, pos: ArticleTextPosition
    ) -> Tuple[List[PreviewSampleTextSegment], int]:
        """Gets the segments and start index of the sentence left of pos."""
        left_start = utils.find_jpn_sentence_start(
            self._article.full_text, pos.start - 1
        )
        found_positions = self._sentence_found_positions_map.get(
            left_start, []
        )
        left_segs = self._create_sample_segments(
            ArticleTextPosition(left_start, pos.start - left_start),
            found_positions
        )

        return (left_segs, left_start)

    def _expand_left(
        self, sample_text: PreviewSampleText, sample_pos: ArticleTextPosition,
        only_if_paragraph_continues: bool
    ) -> None:
        """Expands the sample text to the left to be closer to ideal length.

        Only expands by adding full sentences.

        Args:
            sample_text: Sample text to expand.
            sample_position: Article position of the text used to create
                the given sample text.
            only_if_paragraph_continues: If True, will only expand left if the
                article paragraph continues to the left.
        """
        current_pos = sample_pos
        segs = deque(sample_text.segments)
        while (self._can_expand_left(current_pos)
               and (not only_if_paragraph_continues
                    or self._paragraph_continues_left(current_pos))):
            left_segs, left_start = self._get_left_sentence_segs(current_pos)
            if not self._should_expand(segs, left_segs):
                break

            segs.extendleft(reversed(left_segs))
            current_pos = ArticleTextPosition(
                left_start,
                current_pos.len + current_pos.start - left_start
            )
            self._used_sentences.add(left_start)

        sample_text.text_start_index = current_pos.start
        sample_text.text_len = _segments_len(segs)
        sample_text.segments = list(segs)
        return current_pos

    def _can_expand_right(self, pos: ArticleTextPosition) -> bool:
        """Returns True if it's possible to expand sample text to the right.

        Only returns False when expanding right would expand outside the title
        of the article or outside of the end of the article.
        Returns False when:
            - The end of the article is immediately to the right.
            - Expanding right would expand from inside the article title to
                outside of it.
            - The sentence to the right has already been used in the preview.
        """
        if (pos.start + pos.len) == len(self._article.full_text):
            return False

        # Expansion from inside the title to outside it is not allowed
        if pos.start < len(self._article.title):
            right_end = utils.find_jpn_sentence_start(
                self._article.full_text, pos.start + pos.len
            )
            while right_end > 0 and self._article.full_text[right_end] == '\n':
                right_end -= 1
            if right_end >= len(self._article.title):
                return False

        if (pos.start + pos.len) in self._used_sentences:
            return False

        return True

    def _paragraph_continues_right(self, pos: ArticleTextPosition) -> bool:
        """Returns True if the paragraph continues to the right of pos."""
        pos_end = pos.start + pos.len
        if pos_end == len(self._article.full_text):
            return False
        return not self._article.full_text[pos_end].isspace()

    def _get_right_sentence_segs(
        self, pos: ArticleTextPosition
    ) -> Tuple[List[PreviewSampleTextSegment], int]:
        """Gets the segments and end index of the sentence right of pos."""
        right_start = pos.start + pos.len
        right_end = utils.find_jpn_sentence_end(
            self._article.full_text, right_start
        )
        found_positions = self._sentence_found_positions_map.get(
            right_start, []
        )
        right_segs = self._create_sample_segments(
            ArticleTextPosition(
                right_start, right_end - right_start + 1
            ),
            found_positions
        )

        return (right_segs, right_end)

    def _expand_right(
        self, sample_text: PreviewSampleText, sample_pos: ArticleTextPosition,
        only_if_paragraph_continues: bool
    ) -> None:
        """Expands the sample text to the right to be closer to ideal length.

        Only expands by adding full sentences.

        Args:
            sample_text: Sample text to expand.
            sample_position: Article position of the text used to create
                the given sample text.
            only_if_paragraph_continues: If True, will only expand right if the
                article paragraph continues to the left.
        """
        current_pos = sample_pos
        segs = sample_text.segments
        while (self._can_expand_right(current_pos)
               and (not only_if_paragraph_continues
                    or self._paragraph_continues_right(current_pos))):
            right_start = current_pos.start + current_pos.len
            right_segs, right_end = self._get_right_sentence_segs(current_pos)
            if not self._should_expand(segs, right_segs):
                break

            segs.extend(right_segs)
            current_pos = ArticleTextPosition(
                current_pos.start,
                current_pos.len + right_end - right_start + 1
            )
            self._used_sentences.add(right_start)

        sample_text.text_start_index = current_pos.start
        sample_text.text_len = _segments_len(segs)
        sample_text.segments = segs
        return current_pos

    def _force_expand_left_up_to_max(
        self, sample_text: PreviewSampleText, sample_pos: ArticleTextPosition
    ) -> None:
        """Expands the sample text to the left up to max acceptable lengt.

        Unlike expand_left, will expand using only part of the sentence to the
        left.

        Args:
            sample_text: Sample text to expand.
            sample_position: Article position of the text used to create
                the given sample text.
        """
        current_pos = sample_pos
        segs = deque(sample_text.segments)
        while self._can_expand_left(current_pos):
            left_segs, left_start = self._get_left_sentence_segs(current_pos)
            excess_chars = 0
            for seg in reversed(left_segs):
                segs.appendleft(seg)
                new_segs_len = _segments_len(segs)
                if new_segs_len >= _MAX_ACCEPTABLE_SAMPLE_LEN:
                    excess_chars = new_segs_len - _MAX_ACCEPTABLE_SAMPLE_LEN
                    text = segs[0].text
                    segs[0].text = text[excess_chars:len(text)]
                    break

            if _segments_len(segs) >= _MAX_ACCEPTABLE_SAMPLE_LEN:
                if excess_chars > 0:
                    segs.appendleft(PreviewSampleTextSegment(
                        False, _TRIMMED_INDICATOR_STR
                    ))
                break

            current_pos = ArticleTextPosition(
                left_start,
                current_pos.len + current_pos.start - left_start
            )
            self._used_sentences.add(left_start)

        sample_text.text_start_index = current_pos.start
        sample_text.text_len = _segments_len(segs)
        sample_text.segments = list(segs)
        return current_pos

    def _force_expand_right_up_to_max(
        self, sample_text: PreviewSampleText, sample_pos: ArticleTextPosition
    ) -> None:
        """Expands the sample text to the right up to max acceptable lengt.

        Unlike expand_right, will expand using only part of the sentence to the
        right.

        Args:
            sample_text: Sample text to expand.
            sample_position: Article position of the text used to create
                the given sample text.
        """
        current_pos = sample_pos
        segs = sample_text.segments
        while self._can_expand_left(current_pos):
            right_start = current_pos.start + current_pos.len
            right_segs, right_end = self._get_right_sentence_segs(current_pos)
            excess_chars = 0
            for seg in right_segs:
                segs.append(seg)
                new_segs_len = _segments_len(segs)
                if new_segs_len >= _MAX_ACCEPTABLE_SAMPLE_LEN:
                    excess_chars = new_segs_len - _MAX_ACCEPTABLE_SAMPLE_LEN
                    text = segs[0].text
                    segs[0].text = text[:len(text) - excess_chars]
                    break

            if _segments_len(segs) >= _MAX_ACCEPTABLE_SAMPLE_LEN:
                if excess_chars > 0:
                    segs.append(PreviewSampleTextSegment(
                        False, _TRIMMED_INDICATOR_STR
                    ))
                break

            current_pos = ArticleTextPosition(
                current_pos.start,
                current_pos.len + right_end - right_start + 1
            )
            self._used_sentences.add(right_start)

        sample_text.text_start_index = current_pos.start
        sample_text.text_len = _segments_len(segs)
        sample_text.segments = segs
        return current_pos

    def _expand_sample_text(
        self, sample_text: PreviewSampleText, sample_pos: ArticleTextPosition
    ) -> None:
        """Expands the sample text to be closer to the ideal length.

        Potentially can modify the text_len, text_start_index, and segments
        attrs of the given sample text object.

        Args:
            sample_text: Sample text to expand.
            sample_position: Article position of the text used to create
                the given sample text.
        """
        # Try full sentence expanding only if paragraph continues
        sample_pos = self._expand_left(sample_text, sample_pos, True)
        sample_pos = self._expand_right(sample_text, sample_pos, True)
        if _segments_len(sample_text.segments) >= _MIN_ACCEPTABLE_SAMPLE_LEN:
            return

        # Try full sentence expanding even if paragraph doesn't continue
        sample_pos = self._expand_left(sample_text, sample_pos, False)
        sample_pos = self._expand_right(sample_text, sample_pos, False)
        if _segments_len(sample_text.segments) >= _MIN_ACCEPTABLE_SAMPLE_LEN:
            return

        # Can't full sentence expand either way, so force expand left
        self._force_expand_left_up_to_max(sample_text, sample_pos)
        if _segments_len(sample_text.segments) >= _MIN_ACCEPTABLE_SAMPLE_LEN:
            return

        # Can't force expand left, so force expand right. If this still doesn't
        # expand the sample past the min acceptable length, it means the whole
        # article length is less than the min acceptable sample length.
        self._force_expand_right_up_to_max(sample_text, sample_pos)
