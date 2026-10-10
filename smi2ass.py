#!/usr/bin/env python3
# -*- coding: UTF-8 -*-
#
# Copyright (C) 2018  Trustin Heuiseung Lee and other contributors
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.
#
# Forked from: https://github.com/hojel/service.subtitles.gomtv/blob/3a7342961e140eaf8250659b0ac6158ce5e6bc5c/resources/lib

import argparse
import chardet
import html
import re
import sys
from collections import defaultdict
from copy import deepcopy
from dataclasses import dataclass
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

default_lang_code = 'kor'
default_font_name = 'sans-serif'

# lang class for multiple language subtitle
langCode = {'KRCC':'kor','KOCC':'kor','KR':'kor','KO':'kor','KOREANSC':'kor','KRC':'kor',
            'ENCC':'eng','EGCC':'eng','EN':'eng','EnglishSC':'eng','ENUSCC':'eng','ERCC':'eng',
            'CNCC':'chi','JPCC':'jpn','UNKNOWNCC':'und','COMMENTARY':'commentary'
            }

script_info =\
"""[Script Info]
;This is an Advanced Sub Station Alpha v4+ script.
;Converted by smi2ass
ScriptType: v4.00+
Collisions: Normal
PlayResX: 384
PlayResY: 288
Timer: 100.0000

"""

styles=\
"""
[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,""" + default_font_name + """,22,&H00ffffff,&H0000ffff,&H00000000,&H80000000,0,0,0,0,100,100,0,0.00,1,1,1,2,20,20,20,1

"""

events=\
"""
[Events]
Format: Layer, Start, End, Style, Actor, MarginL, MarginR, MarginV, Effect, Text
"""

# for color code conversion including some common typos
css3_names_to_hex = {
    'aliceblue': '#f0f8ff',
    'antiquewhite': '#faebd7',
    'aqua': '#00ffff',
    'aquamarine': '#7fffd4',
    'azure': '#f0ffff',
    'beige': '#f5f5dc',
    'bisque': '#ffe4c4',
    'black': '#000000',
    'blanchedalmond': '#ffebcd',
    'blue': '#0000ff',
    'blueviolet': '#8a2be2',
    'brown': '#a52a2a',
    'burlywood': '#deb887',
    'cadetblue': '#5f9ea0',
    'chartreuse': '#7fff00',
    'chocolate': '#d2691e',
    'coral': '#ff7f50',
    'cornflowerblue': '#6495ed',
    'cornsilk': '#fff8dc',
    'crimson': '#dc143c',
    'cyan': '#00ffff',
    'darkblue': '#00008b',
    'darkcyan': '#008b8b',
    'darkgoldenrod': '#b8860b',
    'darkgray': '#a9a9a9',
    'darkgrey': '#a9a9a9',
    'darkgreen': '#006400',
    'darkkhaki': '#bdb76b',
    'darkmagenta': '#8b008b',
    'darkolivegreen': '#556b2f',
    'darkorange': '#ff8c00',
    'darkorchid': '#9932cc',
    'darkred': '#8b0000',
    'darksalmon': '#e9967a',
    'darkseagreen': '#8fbc8f',
    'darkslateblue': '#483d8b',
    'darkslategray': '#2f4f4f',
    'darkslategrey': '#2f4f4f',
    'darkturquoise': '#00ced1',
    'darkviolet': '#9400d3',
    'deeppink': '#ff1493',
    'deepskyblue': '#00bfff',
    'dimgray': '#696969',
    'dimgrey': '#696969',
    'dodgerblue': '#1e90ff',
    'firebrick': '#b22222',
    'floralwhite': '#fffaf0',
    'forestgreen': '#228b22',
    'fuchsia': '#ff00ff',
    'gainsboro': '#dcdcdc',
    'ghostwhite': '#f8f8ff',
    'gold': '#ffd700',
    'goldenrod': '#daa520',
    'gray': '#808080',
    'grey': '#808080',
    'green': '#008000',
    'greenyellow': '#adff2f',
    'honeydew': '#f0fff0',
    'hotpink': '#ff69b4',
    'indianred': '#cd5c5c',
    'indigo': '#4b0082',
    'ivory': '#fffff0',
    'khaki': '#f0e68c',
    'lavender': '#e6e6fa',
    'lavenderblush': '#fff0f5',
    'lawngreen': '#7cfc00',
    'lemonchiffon': '#fffacd',
    'lightblue': '#add8e6',
    'lightcoral': '#f08080',
    'lightcyan': '#e0ffff',
    'lightgoldenrodyellow': '#fafad2',
    'lightgray': '#d3d3d3',
    'lightgrey': '#d3d3d3',
    'lightgreen': '#90ee90',
    'lightpink': '#ffb6c1',
    'lightsalmon': '#ffa07a',
    'lightseagreen': '#20b2aa',
    'lightskyblue': '#87cefa',
    'lightslategray': '#778899',
    'lightslategrey': '#778899',
    'lightsteelblue': '#b0c4de',
    'lightyellow': '#ffffe0',
    'lime': '#00ff00',
    'limegreen': '#32cd32',
    'linen': '#faf0e6',
    'magenta': '#ff00ff',
    'maroon': '#800000',
    'mediumaquamarine': '#66cdaa',
    'mediumblue': '#0000cd',
    'mediumorchid': '#ba55d3',
    'mediumpurple': '#9370d8',
    'mediumseagreen': '#3cb371',
    'mediumslateblue': '#7b68ee',
    'mediumspringgreen': '#00fa9a',
    'mediumturquoise': '#48d1cc',
    'mediumvioletred': '#c71585',
    'midnightblue': '#191970',
    'mintcream': '#f5fffa',
    'mistyrose': '#ffe4e1',
    'moccasin': '#ffe4b5',
    'navajowhite': '#ffdead',
    'navy': '#000080',
    'oldlace': '#fdf5e6',
    'olive': '#808000',
    'olivedrab': '#6b8e23',
    'orange': '#ffa500',
    'orangered': '#ff4500',
    'orchid': '#da70d6',
    'palegoldenrod': '#eee8aa',
    'palegreen': '#98fb98',
    'paleturquoise': '#afeeee',
    'palevioletred': '#d87093',
    'papayawhip': '#ffefd5',
    'peachpuff': '#ffdab9',
    'peru': '#cd853f',
    'pink': '#ffc0cb',
    'plum': '#dda0dd',
    'powderblue': '#b0e0e6',
    'purple': '#800080',
    'red': '#ff0000',
    'rosybrown': '#bc8f8f',
    'royalblue': '#4169e1',
    'saddlebrown': '#8b4513',
    'salmon': '#fa8072',
    'sandybrown': '#f4a460',
    'scarlet': '#9c0606',
    'seagreen': '#2e8b57',
    'seashell': '#fff5ee',
    'sienna': '#a0522d',
    'silver': '#c0c0c0',
    'skyblue': '#87ceeb',
    'slateblue': '#6a5acd',
    'slategray': '#708090',
    'slategrey': '#708090',
    'snow': '#fffafa',
    'springgreen': '#00ff7f',
    'steelblue': '#4682b4',
    'tan': '#d2b48c',
    'teal': '#008080',
    'thistle': '#d8bfd8',
    'tomato': '#ff6347',
    'turquoise': '#40e0d0',
    'violet': '#ee82ee',
    'wheat': '#f5deb3',
    'white': '#ffffff',
    'whitesmoke': '#f5f5f5',
    'yellow': '#ffff00',
    'yellowgreen': '#9acd32',
}

space_chars = [
    u'\u00A0', u'\u180E', u'\u2000', u'\u2001', u'\u2002', u'\u2003', u'\u2004', u'\u2005', u'\u2006',
    u'\u2007', u'\u2008', u'\u2009', u'\u200A', u'\u200B', u'\u202F', u'\u205F', u'\u3000' ]

@dataclass(frozen=True)
class ConversionDiagnostic:
    code: str
    severity: str
    line: int
    message: str


@dataclass(frozen=True)
class FileConversionResult:
    source: Path
    outputs: tuple
    diagnostics: tuple
    skipped_existing: tuple


@dataclass(frozen=True)
class SyncEntry:
    tag: object
    timestamp: int
    line: int


SYNC_TOKEN_RE = re.compile(r'<\s*(/?)\s*sync\b[^>]*>', re.IGNORECASE)
SYNC_OPEN_RE = re.compile(r'<\s*sync\b[^>]*>', re.IGNORECASE)
PARAGRAPH_TOKEN_RE = re.compile(r'<\s*(/?)\s*(p|sync)\b[^>]*>', re.IGNORECASE)
FORMAT_BOUNDARY_RE = re.compile(r'<\s*(/?)\s*(b|i|u|s|font|rt|p|sync)\b[^>]*>', re.IGNORECASE)
TIMESTAMP_RE = re.compile(r'^\s*([+-]?\d+)\s*$')
TIMESTAMP_SUFFIX_RE = re.compile(r'^\s*(\d+)([?!.,;:]+)\s*$')


def _line_number(source, offset):
    return source.count('\n', 0, offset) + 1


def _add_diagnostic(diagnostics, source, code, severity, offset, message):
    diagnostics.append(ConversionDiagnostic(
        code=code,
        severity=severity,
        line=_line_number(source, offset),
        message=message,
    ))


def _repair_sync_boundaries(source, diagnostics):
    repaired = []
    cursor = 0
    current_sync = None

    for match in SYNC_TOKEN_RE.finditer(source):
        repaired.append(source[cursor:match.start()])
        token = match.group(0)
        is_closing = bool(match.group(1))

        if is_closing:
            if current_sync is None:
                _add_diagnostic(
                    diagnostics, source, 'SYNC_CLOSE_REMOVED', 'repair',
                    match.start(), 'Removed a closing SYNC tag without an open SYNC tag.',
                )
            else:
                repaired.append(token)
                current_sync = None
        else:
            if current_sync is not None:
                repaired.append('</sync>')
                _add_diagnostic(
                    diagnostics, source, 'SYNC_CLOSE_INSERTED', 'repair',
                    current_sync, 'Inserted a closing SYNC tag before the next SYNC tag.',
                )
            repaired.append(token)
            current_sync = match.start()
        cursor = match.end()

    repaired.append(source[cursor:])
    return ''.join(repaired)


def _repair_paragraph_boundaries(source):
    """Make optional SAMI P closings explicit before HTML parsing."""
    repaired = []
    cursor = 0
    opening = None
    for match in PARAGRAPH_TOKEN_RE.finditer(source):
        repaired.append(source[cursor:match.start()])
        closing, name = bool(match.group(1)), match.group(2).lower()
        if opening is not None and (name == 'sync' or (name == 'p' and not closing)):
            repaired.append('</p>')
            opening = None
        repaired.append(match.group(0))
        if name == 'p':
            opening = None if closing else match.start()
        cursor = match.end()
    repaired.append(source[cursor:])
    if opening is not None:
        repaired.append('</p>')
    return ''.join(repaired)


def _repair_formatting_tags(source, diagnostics):
    sync_matches = list(SYNC_OPEN_RE.finditer(source))
    if not sync_matches:
        return source

    repaired = []
    cursor = 0
    for index, sync_match in enumerate(sync_matches):
        next_sync = sync_matches[index + 1].start() if index + 1 < len(sync_matches) else len(source)
        repaired.append(source[cursor:sync_match.end()])
        region = source[sync_match.end():next_sync]
        region_start = sync_match.end()
        region_output = []
        region_cursor = 0
        stack = []

        for match in FORMAT_BOUNDARY_RE.finditer(region):
            region_output.append(region[region_cursor:match.start()])
            token = match.group(0)
            closing = bool(match.group(1))
            tag_name = match.group(2).lower()

            if tag_name in ('p', 'sync'):
                while stack:
                    unclosed_tag, opening_offset = stack.pop()
                    region_output.append('</%s>' % unclosed_tag)
                    _add_diagnostic(diagnostics, source, 'FORMAT_CLOSE_INSERTED', 'repair',
                                    opening_offset, 'Closed an unclosed %s tag at a paragraph boundary.' % unclosed_tag)
                region_output.append(token)
                region_cursor = match.end()
                continue

            if not closing and not token.rstrip().endswith('/>'):
                stack.append((tag_name, region_start + match.start()))
                region_output.append(token)
            elif closing:
                stack_index = next(
                    (stack_index for stack_index in range(len(stack) - 1, -1, -1)
                     if stack[stack_index][0] == tag_name),
                    None,
                )
                if stack_index is None:
                    _add_diagnostic(
                        diagnostics, source, 'FORMAT_CLOSE_REMOVED', 'repair',
                        region_start + match.start(),
                        'Removed an unmatched closing %s tag.' % tag_name,
                    )
                else:
                    while len(stack) - 1 > stack_index:
                        unclosed_tag, opening_offset = stack.pop()
                        region_output.append('</%s>' % unclosed_tag)
                        _add_diagnostic(
                            diagnostics, source, 'FORMAT_CLOSE_INSERTED', 'repair',
                            opening_offset,
                            'Closed an unclosed %s tag before mismatched markup.' % unclosed_tag,
                        )
                    stack.pop()
                    region_output.append(token)
            else:
                region_output.append(token)
            region_cursor = match.end()

        region_output.append(region[region_cursor:])
        while stack:
            tag_name, opening_offset = stack.pop()
            region_output.append('</%s>' % tag_name)
            _add_diagnostic(
                diagnostics, source, 'FORMAT_CLOSE_INSERTED', 'repair',
                opening_offset, 'Closed an unclosed %s tag at the end of its SYNC cue.' % tag_name,
            )
        repaired.append(''.join(region_output))
        cursor = next_sync

    repaired.append(source[cursor:])
    return ''.join(repaired)


def _parse_timestamp(raw_value, source, source_offset, diagnostics):
    if raw_value is None:
        _add_diagnostic(
            diagnostics, source, 'INVALID_TIMESTAMP', 'skip', source_offset,
            'Skipped a cue with no Start timestamp.',
        )
        return None

    match = TIMESTAMP_RE.fullmatch(str(raw_value))
    if match:
        timestamp = int(match.group(1))
        if timestamp < 0:
            _add_diagnostic(
                diagnostics, source, 'INVALID_TIMESTAMP', 'skip', source_offset,
                'Skipped a cue with a negative Start timestamp.',
            )
            return None
        return timestamp

    match = TIMESTAMP_SUFFIX_RE.fullmatch(str(raw_value))
    if match:
        timestamp = int(match.group(1))
        _add_diagnostic(
            diagnostics, source, 'TIMESTAMP_SUFFIX_REMOVED', 'repair', source_offset,
            'Removed trailing punctuation from Start=%s; using %s milliseconds.' %
            (raw_value, timestamp),
        )
        return timestamp

    _add_diagnostic(
        diagnostics, source, 'INVALID_TIMESTAMP', 'skip', source_offset,
        'Skipped a cue with an ambiguous Start timestamp: %r.' % raw_value,
    )
    return None


def ass_bgr_color(color_value):
    color_value = str(color_value).strip().lower()
    if color_value in css3_names_to_hex:
        color_value = css3_names_to_hex[color_value]

    match = re.fullmatch(r'#?([0-9a-f]{6})', color_value)
    if match is None:
        return None

    red, green, blue = (
        match.group(1)[0:2],
        match.group(1)[2:4],
        match.group(1)[4:6],
    )
    return blue + green + red


def smi2ass(smi_sgml):
    return convert_smi(smi_sgml)[0]


def convert_smi(smi_sgml):
    diagnostics = []
    smi_sgml = _repair_sync_boundaries(smi_sgml, diagnostics)
    smi_sgml = _repair_paragraph_boundaries(smi_sgml)
    smi_sgml = _repair_formatting_tags(smi_sgml, diagnostics)
    diagnostic_source = smi_sgml
    sync_offsets = [match.start() for match in SYNC_OPEN_RE.finditer(diagnostic_source)]
    sync_lines = [_line_number(diagnostic_source, offset) for offset in sync_offsets]

    # CRLF, LF or tab to a whitespace
    smi_sgml = smi_sgml.replace(u'\u000D\u000A', u' ')
    smi_sgml = smi_sgml.replace(u'\u000A', u' ')
    smi_sgml = smi_sgml.replace(u'\u000D', u' ')
    smi_sgml = smi_sgml.replace('\t', ' ')

    # Replace special space characters so that BeautifulSoup can't remove them.
    for spaceChar in space_chars:
        smi_sgml = smi_sgml.replace(spaceChar, 'smi2ass_unicode(' + str(ord(spaceChar)) + ')')

    # Replace spaces around a tag with '&nbsp;' so that they are not stripped when we replace a tag.
    smi_sgml = re.sub(r'> +<', '>smi2ass_unicode(32)<', smi_sgml)
    smi_sgml = re.sub(r'> +', '>smi2ass_unicode(32)', smi_sgml)
    smi_sgml = re.sub(r' +<', 'smi2ass_unicode(32)<', smi_sgml)
    # but not <rt> tags
    smi_sgml = re.sub(r'< *[Rr][Tt] *>(smi2ass_unicode\([0-9]+\))+', '<rt>', smi_sgml)
    smi_sgml = re.sub(r'(smi2ass_unicode\([0-9]+\))+</ *[Rr][Tt] *>', '</rt>', smi_sgml)

    #Parse lines with BeautifulSoup based on sync tag
    soup = BeautifulSoup(smi_sgml, 'html.parser')
    smi_lines = soup.find_all('sync')
    if not smi_lines:
        diagnostics.append(ConversionDiagnostic(
            code='NO_SYNC_CUES',
            severity='skip',
            line=1,
            message='No SYNC cues were found in the input.',
        ))
        return {}, diagnostics

    mln, longlang = separate_by_lang(
        smi_lines, diagnostic_source, sync_offsets, sync_lines, diagnostics,
    )
    ass_dict = {}
    for lang_idx, lang in enumerate(mln):
        ass_lines = smi2ass_internal(mln[lang], diagnostics)
        if len(ass_lines) > 0:
            asscontents = (script_info+styles+events+''.join(ass_lines)).encode('utf-8')
            ass_dict[longlang[lang_idx]] = asscontents

    return ass_dict, diagnostics

def smi2ass_internal(sln, diagnostics=None):
    diagnostics = diagnostics if diagnostics is not None else []
    ass_lines = []
    for line_idx, entry in enumerate(sln):
        final_text = html.unescape(re.sub(r'smi2ass_unicode\(([0-9]+)\)', r'&#\1;', entry.tag.get_text())).strip()
        if line_idx + 1 == len(sln) and final_text:
            diagnostics.append(ConversionDiagnostic('MISSING_END_TIMESTAMP', 'skip', entry.line,
                                                    'The last text cue has no following timestamp.'))
        if line_idx + 1 < len(sln):
            item = entry.tag
            tcstart = ms2timecode(entry.timestamp)
            tcend = ms2timecode(sln[line_idx+1].timestamp)

            p_tags = item.find('p')# <SYNC Start=41991><P Class=KRCC><SYNC Start=43792><P Class=KRCC>
            if not p_tags:
                continue

            br = p_tags.find_all('br')
            for gg in br:
                gg.replace_with('\\N')

            bold = p_tags.find_all('b')
            for bo in bold:
                if len(bo.text) != 0:
                    boldre = '{\\b1}'+bo.text+'{\\b0}'
                    bo.replace_with(NavigableString(boldre))
                else:
                    bo.extract()

            italics = p_tags.find_all('i')
            for it in italics:
                if len(it.text) != 0:
                    itre = '{\\i1}'+it.text+'{\\i0}'
                    it.replace_with(NavigableString(itre))
                else:
                    it.extract()

            underlines = p_tags.find_all('u')
            for un in underlines:
                if len(un.text) != 0:
                    unre = '{\\u1}'+un.text+'{\\u0}'
                    un.replace_with(NavigableString(unre))
                else:
                    un.extract()

            strikes = p_tags.find_all('s')
            for st in strikes:
                if len(st.text) != 0:
                    stre = '{\\s1}'+st.text+'{\\s0}'
                    st.replace_with(NavigableString(stre))
                else:
                    st.extract()

            ruby_tags = p_tags.find_all('rt')
            for rt in ruby_tags:
                if len(rt.text) != 0:
                    rt_re = '{\\fscx50}{\\fscy50}&nbsp;'+rt.text+'&nbsp;{\\fscx100}{\\fscy100}'
                    rt.replace_with(NavigableString(rt_re))
                else:
                    rt.extract()

            colors = p_tags.find_all('font')
            for color in colors:
                col = color.get('color')
                if col is not None:
                    bgr_color = ass_bgr_color(col)
                    if bgr_color is None:
                        diagnostics.append(ConversionDiagnostic(
                            code='UNKNOWN_COLOR',
                            severity='warning',
                            line=entry.line,
                            message='Kept text with unsupported font color %r.' % col,
                        ))
                        color.replace_with(NavigableString(color.text))
                    else:
                        converted_color = '{\\c&H' + bgr_color + '&}' + color.text + '{\\c}'
                        color.replace_with(NavigableString(converted_color))

            contents = p_tags.text
            contents = re.sub(r'smi2ass_unicode\(([0-9]+)\)', r'&#\1;', contents)
            contents = html.unescape(contents)

            if len(contents.strip()) != 0:
                line = 'Dialogue: 0,%s,%s,Default,,0000,0000,0000,,%s\n' % (tcstart,tcend, contents)
                ass_lines.append(line)

    return ass_lines


def ms2timecode(ms):
    centiseconds = (int(ms) + 5) // 10
    hours, centiseconds = divmod(centiseconds, 360000)
    minutes, centiseconds = divmod(centiseconds, 6000)
    seconds, centiseconds = divmod(centiseconds, 100)
    return '%01d:%02d:%02d.%02d' % (hours, minutes, seconds, centiseconds)


def separate_by_lang(smi_lines, source, sync_offsets, sync_lines, diagnostics):
    #prepare multilanguage dict with languages separated list
    multiLanguageDict = defaultdict(list)
    aliases = {key.upper(): value for key, value in langCode.items()}

    #loop for number of smi subtitle lines
    for line_idx, subtitleLine in enumerate(smi_lines):
        source_line = sync_lines[line_idx] if line_idx < len(sync_lines) else 1
        source_offset = sync_offsets[line_idx] if line_idx < len(sync_offsets) else 0
        timestamp = _parse_timestamp(
            subtitleLine.get('start'), source, source_offset or 0, diagnostics,
        )
        if timestamp is None:
            continue

        for paragraph in subtitleLine.find_all('p'):
            classes = paragraph.get('class', [])
            language_class = classes[0].upper() if classes else 'UNKNOWN'
            language = aliases.get(language_class, language_class)
            if not classes:
                _add_diagnostic(diagnostics, source, 'LANGUAGE_CLASS_MISSING', 'warning',
                                source_offset or 0, 'The cue has no language class; assigning it to the unknown language.')
            container = BeautifulSoup('', 'html.parser').new_tag('sync')
            container.append(deepcopy(paragraph))
            entry = SyncEntry(container, timestamp, source_line)
            multiLanguageDict[language].append(entry)

    separated = defaultdict(list)
    names = []
    used_names = set()
    for language, entries in multiLanguageDict.items():
        # Equal timestamps describe simultaneous text, not zero-length cues.
        for entry in sorted(entries, key=lambda value: value.timestamp):
            previous = separated[language][-1] if separated[language] else None
            if previous is not None and previous.timestamp == entry.timestamp:
                incoming = entry.tag.find('p')
                current = previous.tag.find('p')
                incoming_text = html.unescape(re.sub(r'smi2ass_unicode\(([0-9]+)\)', r'&#\1;', incoming.get_text())).strip()
                current_text = html.unescape(re.sub(r'smi2ass_unicode\(([0-9]+)\)', r'&#\1;', current.get_text())).strip()
                if incoming_text:
                    if current_text:
                        current.append(BeautifulSoup('', 'html.parser').new_tag('br'))
                    else:
                        current.clear()
                    for child in list(incoming.contents):
                        current.append(child.extract())
            else:
                separated[language].append(entry)
        if len(multiLanguageDict) == 1:
            names.append('')
        else:
            base = re.sub(r'[^a-zA-Z0-9_-]', '_', language).strip('_').lower() or 'unknown'
            name = base
            index = 2
            while name.casefold() in used_names:
                name = '%s_%d' % (base, index)
                index += 1
            used_names.add(name.casefold())
            names.append(name)
    return separated, names


def convert_smi_file(smi_path, overwrite=True):
    # Open as binary and detect the encoding.
    with open(smi_path, 'rb') as smi_file:
        smi_bytes = smi_file.read()
    smi_encoding = chardet.detect(smi_bytes)['encoding'] or 'utf-8'

    with open(smi_path, 'r', encoding=smi_encoding, errors='replace') as smi_file:
        smi_sgml = smi_file.read()
    ass_dict, diagnostics = convert_smi(smi_sgml)
    input_path = Path(smi_path)
    output_stem = input_path.stem if input_path.suffix else input_path.name
    output_data = {}
    for lang, contents in ass_dict.items():
        output_language = lang or default_lang_code
        ass_path = input_path.with_name(
            '%s.%s.ass' % (output_stem, output_language),
        )
        output_data[ass_path] = contents

    existing_outputs = tuple(
        path for path in output_data if not overwrite and path.exists()
    )
    pending_outputs = tuple(
        path for path in output_data if overwrite or not path.exists()
    )
    written_outputs = []
    for ass_path in pending_outputs:
        contents = output_data[ass_path]
        try:
            with ass_path.open('wb') as ass_file:
                ass_file.write(contents)
        except OSError as error:
            diagnostics.append(ConversionDiagnostic('OUTPUT_WRITE_FAILED', 'skip', 1,
                                                    'Could not write %s: %s' % (ass_path.name, error)))
        else:
            written_outputs.append(ass_path)

    return FileConversionResult(
        source=input_path,
        outputs=tuple(written_outputs),
        diagnostics=tuple(diagnostics),
        skipped_existing=existing_outputs,
    )


def convert_file(smi_path):
    result = convert_smi_file(smi_path)
    for diagnostic in result.diagnostics:
        print(
            '%s:%d: [%s] %s' % (
                smi_path, diagnostic.line, diagnostic.severity, diagnostic.message,
            ),
            file=sys.stderr,
        )
    repaired_count = sum(item.severity == 'repair' for item in result.diagnostics)
    skipped_count = sum(item.severity == 'skip' for item in result.diagnostics)
    print(
        '%s: repaired %d, skipped %d' % (smi_path, repaired_count, skipped_count),
        file=sys.stderr,
    )
    return skipped_count > 0


def main(argv=None):
    parser = argparse.ArgumentParser(
        description='Convert SAMI subtitle files to SSA/ASS.'
    )
    parser.add_argument('files', nargs='+', metavar='FILE.smi')
    args = parser.parse_args(argv)

    failed = False
    for smi_path in args.files:
        try:
            failed = convert_file(smi_path) or failed
        except OSError as error:
            print('%s: error: %s' % (smi_path, error), file=sys.stderr)
            failed = True
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
