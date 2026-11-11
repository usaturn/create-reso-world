"""JSON result helpers for both directions of an adapter exchange.

``request_prompt`` appends the instruction a request asks for when the role's
result shape is JSON; ``json_object`` and ``first_json_object`` extract the
JSON object a response offers as its result. Both reject a malformed object
candidate instead of falling back to an earlier result or an object nested in
the broken candidate. A closed inline code span or a closed code fence with an
explicit non-JSON language is an example: a malformed object candidate inside
it does not reject the response and an object nested in that broken candidate
is not rescued, while a valid object inside the example remains a normal
candidate.
"""

import json
from typing import NamedTuple, cast

from tools.agent_runner.models import ResultShape

_JSON_WHITESPACE = " \t\n\r"


class _Fence(NamedTuple):
    marker: str
    size: int
    info: str
    line_end: int


class _FenceClose(NamedTuple):
    start: int
    end: int


def _object_candidate(text: str, index: int) -> bool:
    """Return whether the ``{`` at *index* begins a JSON object candidate.

    A brace in prose such as ``{name}`` or ``{key: value}`` is not a candidate;
    the next non-whitespace character must be a quote, a closing brace, or the
    end of the response.
    """
    index += 1
    while index < len(text) and text[index] in _JSON_WHITESPACE:
        index += 1
    return index == len(text) or text[index] in '"}'


def _first_object(value: object) -> dict[str, object] | None:
    """Return the first non-empty object in a successfully decoded value."""
    if isinstance(value, dict):
        mapping = cast(dict[str, object], value)
        return mapping or None
    if isinstance(value, list):
        for item in cast(list[object], value):
            found = _first_object(item)
            if found is not None:
                return found
    return None


def _run_length(text: str, index: int, character: str) -> int:
    """Return the length of the run of *character* starting at *index*."""
    end = index
    while end < len(text) and text[end] == character:
        end += 1
    return end - index


def _line_start(text: str, index: int) -> bool:
    """Return whether *index* is the first character of a line."""
    return index == 0 or text[index - 1] == "\n"


def _fence_line(text: str, index: int) -> _Fence | None:
    """Parse a code fence line at *index*, if one starts there."""
    start = index
    while start < len(text) and text[start] == " " and start - index < 3:
        start += 1
    if start >= len(text) or text[start] not in "`~":
        return None
    marker = text[start]
    size = _run_length(text, start, marker)
    if size < 3:
        return None
    line_end = text.find("\n", start + size)
    if line_end == -1:
        line_end = len(text)
    info = text[start + size : line_end].strip()
    if marker == "`" and "`" in info:
        return None
    return _Fence(marker, size, info, line_end)


def _closed_fence_end(text: str, fence: _Fence) -> _FenceClose | None:
    """Return the closing fence position for *fence*, if it is closed."""
    position = fence.line_end + 1
    while position < len(text):
        line_end = text.find("\n", position)
        if line_end == -1:
            line_end = len(text)
        start = position
        while start < line_end and text[start] == " " and start - position < 3:
            start += 1
        if start < line_end and text[start] == fence.marker:
            size = _run_length(text, start, fence.marker)
            if size >= fence.size and not text[start + size : line_end].strip():
                end = line_end + 1 if line_end < len(text) else len(text)
                return _FenceClose(position, end)
        if line_end == len(text):
            break
        position = line_end + 1
    return None


def _example_fence(fence: _Fence) -> bool:
    """Return whether *fence* explicitly names a non-JSON language."""
    if not fence.info:
        return False
    language = fence.info.split(maxsplit=1)[0]
    return not language.lower().startswith("json")


def _blank_line_after(text: str, newline: int) -> bool:
    """Return whether the line after the newline at *newline* is blank."""
    start = newline + 1
    end = text.find("\n", start)
    if end == -1:
        end = len(text)
    return not text[start:end].strip()


def _inline_code_end(text: str, index: int, decoder: json.JSONDecoder) -> int | None:
    """Return the end of a closed inline code span starting at *index*.

    Valid JSON containers are consumed whole while looking for the closing
    backticks, so a backtick inside a decoded string does not end the span.
    A line-start code fence is a boundary of the span search: it is block
    structure that an inline span cannot cross, so the span stays unclosed
    and the opening backticks remain literal characters.
    """
    size = _run_length(text, index, "`")
    position = index + size
    while position < len(text):
        if text[position] == "\n" and _blank_line_after(text, position):
            return None
        if _line_start(text, position) and _fence_line(text, position) is not None:
            return None
        if text[position] == "`":
            run = _run_length(text, position, "`")
            if run == size:
                return position + run
            position += run
            continue
        if text[position] in "{[":
            try:
                _, end = decoder.raw_decode(text, position)
            except json.JSONDecodeError:
                pass
            else:
                position = end
                continue
        position += 1
    return None


def _object_extent(text: str, index: int, limit: int) -> int:
    """Return the end of the object-shaped text starting at *index*.

    The text is not decoded; braces outside quoted strings are followed so a
    malformed object example is skipped as a unit and an object nested inside
    it is not picked up as an independent result. An unterminated object ends
    at *limit*.
    """
    depth = 0
    quote: str | None = None
    escaped = False
    position = index
    while position < limit:
        character = text[position]
        if quote is not None:
            if escaped:
                escaped = False
            elif character == "\\":
                escaped = True
            elif character == quote:
                quote = None
        elif character in "\"'":
            quote = character
        elif character == "{":
            depth += 1
        elif character == "}":
            depth -= 1
            if depth == 0:
                return position + 1
        position += 1
    return limit


def _extract_object(text: str, *, first: bool) -> dict[str, object] | None:
    """Scan *text*, rejecting any malformed JSON object candidate.

    A closed inline code span or a closed code fence with an explicit non-JSON
    language is an example: a malformed object candidate inside it does not
    reject the response, and an object nested in that broken candidate is not
    rescued. A valid object inside the example is still a candidate, so the
    usual first/last selection is unchanged. JSON fences and fences without a
    language are scanned as results, and a malformed candidate inside one still
    rejects the response. Scan text is consumed one decoded JSON container at a
    time, so a delimiter inside a decoded string does not start an example.

    A successful object decode is consumed whole, including an empty object; a
    successful array is consumed whole too, except that the first policy reads
    its first non-empty object because that was the codex/cursor behavior. A
    failed array is skipped to the decoder's error position without rejecting
    the response. A failed object candidate outside an example rejects the
    response even when an earlier or nested object decoded successfully.
    """
    decoder = json.JSONDecoder()
    candidate: dict[str, object] | None = None
    index = 0
    result_fence_end: int | None = None
    result_fence_resume: int | None = None
    example_end: int | None = None
    example_resume: int | None = None
    while index < len(text):
        if example_end is not None:
            if index >= example_end:
                index = example_resume if example_resume is not None else example_end
                example_end = None
                example_resume = None
                continue
        elif result_fence_end is not None:
            if index >= result_fence_end:
                index = result_fence_resume if result_fence_resume is not None else len(text)
                result_fence_end = None
                result_fence_resume = None
                continue
        elif _line_start(text, index):
            fence = _fence_line(text, index)
            if fence is not None:
                close = _closed_fence_end(text, fence)
                if close is not None and _example_fence(fence):
                    example_end = close.start
                    example_resume = close.end
                    index = min(fence.line_end + 1, len(text))
                    continue
                if close is not None:
                    result_fence_end = close.start
                    result_fence_resume = close.end
                index = min(fence.line_end + 1, len(text))
                continue
        if example_end is None and result_fence_end is None and text[index] == "`":
            inline_end = _inline_code_end(text, index, decoder)
            if inline_end is not None:
                example_end = inline_end
                index += _run_length(text, index, "`")
                continue
        character = text[index]
        if character == "{":
            if not _object_candidate(text, index):
                index += 1
                continue
            try:
                value, end = decoder.raw_decode(text, index)
            except json.JSONDecodeError:
                if example_end is not None:
                    index = _object_extent(text, index, example_end)
                    continue
                return None
            mapping = cast(dict[str, object], value)
            if not first:
                candidate = mapping
            elif candidate is None and mapping:
                candidate = mapping
            index = end
            continue
        if character != "[":
            index += 1
            continue
        try:
            value, end = decoder.raw_decode(text, index)
        except json.JSONDecodeError as error:
            index = max(index + 1, error.pos)
            continue
        if first and candidate is None:
            candidate = _first_object(value)
        index = end
    return candidate


def json_object(text: str) -> dict[str, object] | None:
    """Return the last JSON object in *text*, or ``None`` when there is none.

    When all of *text* is JSON, only an object is accepted; an array or another
    value is not searched for nested objects. Otherwise an object candidate
    starts at a ``{`` whose next non-whitespace character is ``"``, ``}``, or
    the end of the text. Braces in prose such as ``{name}`` are ignored, but a
    decode failure at a candidate outside an explicit example rejects the
    whole response; the decoder does not advance into the broken candidate,
    return to an earlier result, or search past it. A failed array is not a
    rejection: scanning resumes at the decoder's error position (at least one
    character later). A successful array is consumed whole, so its members are
    not candidates. The last successfully decoded object wins, including an
    empty one.

    A closed inline code span or a closed code fence with an explicit non-JSON
    language is an example. A malformed object candidate inside an example does
    not reject a result outside it, and an object nested in that broken
    candidate is not rescued; a valid object inside the example is still a
    candidate, so the first/last selection is unchanged. JSON fences, fences
    without a language, and bare object candidates keep the rejection behavior:
    intent is not inferred, so a malformed correction rejects even after a
    complete earlier result. A broken array wrapper, an unquoted key, or a
    single-quoted pseudo object gets no new meaning here.
    """
    try:
        whole: object = json.loads(text)
    except json.JSONDecodeError:
        pass
    else:
        return cast(dict[str, object], whole) if isinstance(whole, dict) else None
    return _extract_object(text, first=False)


def first_json_object(text: str) -> dict[str, object] | None:
    """Return the first non-empty JSON object in *text*, or ``None``.

    This keeps the codex/cursor selection policy: whole-text objects and the
    first non-empty object inside a valid array are accepted, while empty
    objects are skipped. The response is still scanned to its end, so a
    malformed object candidate after the selected result rejects the whole
    response. Candidate detection, explicit examples, and rejection follow
    :func:`json_object`; intent is not inferred, and broken array wrappers,
    unquoted keys, and single-quoted pseudo objects are outside this helper's
    guarantees.
    """
    return _extract_object(text, first=True)


JSON_REQUEST = "Answer with a single JSON object as your final message."


def request_prompt(prompt: str, shape: ResultShape) -> str:
    if shape != "json":
        return prompt
    return f"{prompt}\n\n{JSON_REQUEST}"
