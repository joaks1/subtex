#! /usr/bin/env python

import os
import sys
import logging
import itertools
import re
import shutil

logging.basicConfig(level=logging.WARNING)
_LOG = logging.getLogger("subtex")
_program_info = {
    'name': os.path.basename(__file__),
    'author': 'Jamie Oaks',
    'version': 'Version 0.1.0',
    'copyright': 'Copyright (C) 2012 Jamie Oaks.',
    'license': (
        'This is free software distributed under the GNU General Public '
        'License in the hope that it will be useful, but WITHOUT ANY '
        'WARRANTY. You are free to change and redistribute it in accord with '
        'the GPL. See the GNU General Public License for more details.'),}


class LatexReference(object):
    def __init__(self,
            caption_setup=None,
            caption='',
            label=None,
            exclude_caption_setup = False):
        self.caption_setup = caption_setup
        self.caption = caption
        self.label = label
        self.exclude_caption_setup = exclude_caption_setup

    def to_string(self, indent='    '):
        s = ''
        if not self.exclude_caption_setup:
            if self.caption_setup:
                s += '{0}\\captionsetup{{{1}}}\n'.format(indent, self.caption_setup)
            s += '{0}\\captionsetup{{list=no,singlelinecheck=off}}\n'.format(indent)
        s += '{0}\\caption{{{1}}}\n'.format(indent, self.caption)
        if self.label:
            s += '{0}\\label{{{1}}}\n'.format(indent, self.label)
        return s
            
class LatexFigureRef(LatexReference):
    def __init__(self, *args, **kwargs):
        LatexReference.__init__(self, *args, **kwargs)

    def __str__(self, indent='    '):
        s = '\\begin{figure}[h!]\n'
        s += self.to_string(indent=indent)
        s += '\\end{figure}\n'
        return s

class LatexTableRef(LatexReference):
    def __init__(self, *args, **kwargs):
        LatexReference.__init__(self, *args, **kwargs)

    def __str__(self, indent='    '):
        s = '\\begin{table}[h!]\n'
        s += self.to_string(indent=indent)
        s += '\\end{table}\n'
        return s

class SubmissionBundler(object):
    custom_fig_path_patterns =  {
                'mfigure': re.compile(r'[^%]*(?<!newcommand{)\\mFigure\{(?P<path>[^}#]*)\}.*'),
                'sifigure': re.compile(r'[^%]*(?<!newcommand{)\\siFigure\{(?P<path>[^}#]*)\}.*'),
                'sisidewaysfigure': re.compile(r'[^%]*(?<!newcommand{)\\siSidewaysFigure\{(?P<path>[^}#]*)\}.*'),
                'sieightfigure': re.compile(r'[^%]*(?<!newcommand{)\\siEightFigure\{(?P<path>[^}#]*)\}.*'),
                'widthfigure': re.compile(r'[^%]*(?<!newcommand{)\\widthFigure\{[0-9.]*\}\{(?P<path>[^}#]*)\}.*'),
                }
    path_patterns = {
                'documentclass': re.compile(r'[^%]*\\documentclass\[?.*\]?\{(?P<path>[^}]*)\}.*'),
                'bib_style': re.compile(r'[^%]*\\bibliographystyle\{(?P<path>[^}]*)\}.*'),
                'input': re.compile(r'[^%]*\\input\{(?P<path>[^}]*)\}.*'),
                'bib': re.compile(r'[^%]*\\bibliography\{(?P<path>[^}]*)\}.*'),
                'graphic': re.compile(r'[^%]*(?<!newcommand{)(?<!def)\\includegraphics.*\{(?P<path>[^}#]*)\}.*'),
                }
    path_patterns.update(custom_fig_path_patterns)
    header_patterns = {
        'table': re.compile(r'[^%]*\\begin\s*\{\s*(\w*table\w*)\s*\}.*',
                re.IGNORECASE),
        'figure': re.compile(r'[^%]*\\begin\s*\{\s*(\w*figure\w*)\s*\}.*',
                re.IGNORECASE),
        'input': re.compile(r'[^%]*\\input.*\{([^}]*)\}.*'),}
    header_patterns.update(custom_fig_path_patterns)
    attribute_patterns = {
        'caption_setup': re.compile(r'\\captionsetup\s*(\{.*)', re.DOTALL),
        'caption': re.compile(r'\\caption\s*\[*\s*\]*\s*(\{.*)', re.DOTALL),
        'label': re.compile(r'\\caption\s*\[*\s*\]*\s*\{.*\\label\s*(\{.*)',
                re.DOTALL),}
    si_pattern = re.compile(r'^\s*[%]+\s*supporting\s+info.*$', re.IGNORECASE)
    caption_setup_pattern = re.compile(r'[^%]*(?<!newcommand{)(?<!def)\\captionsetup.*\{[^}#]*\}.*')

    def __init__(self, latex_path, dest_dir,
            strip_comments = True,
            append_figure_names = False,
            strip_si = False,
            strip_figures = False,
            exclude_caption_setup = False,
            merge = False):
        self.latex_path = expand_path(latex_path)
        self.dest_dir = expand_path(dest_dir)
        if not os.path.exists(self.dest_dir):
            mkdr(self.dest_dir)
        self.out_path = os.path.join(self.dest_dir, os.path.basename(latex_path))
        self.strip_comments = strip_comments
        self.append_figure_names = append_figure_names
        self.strip_si = strip_si
        self.strip_figures = strip_figures
        self.exclude_caption_setup = exclude_caption_setup
        self.figure_index = 0
        self.si_started = False
        self.merge = merge
        self.out_stream = None
        self.paths_copied = []
        self.paths_failed = []

    def _open_stream(self):
        self.out_stream = open(self.out_path, 'w')

    def _close_stream(self):
        if not self.out_stream is None:
            self.out_stream.close()

    def get_figure_prefix(self):
        self.figure_index += 1
        if not self.append_figure_names:
            return ''
        p = ''
        if self.si_started:
            p = 's'
        return 'figure_{0}{1}_'.format(p, self.figure_index)

    def is_graphic_key(self, k):
        if self.custom_fig_path_patterns.has_key(k):
            return True
        if k == 'graphic':
            return True
        return False

    def bundle(self):
        path = self.latex_path
        stream = None
        if self.merge:
            self._open_stream()
        self._bundle(path)
        self._close_stream()
        return self.paths_copied, self.paths_failed

    def _bundle(self, path):
        latex_path = expand_path(path)
        _LOG.info('Bundling latex file {0} to {1}'.format(latex_path, self.dest_dir))
        out = self.out_stream
        if out is None:
            out_path = os.path.join(self.dest_dir, os.path.basename(latex_path))
            out = open(out_path, 'w')
        latex_stream = open(latex_path, 'rU')
        latex_iter = iter(latex_stream)
        project_dir = os.path.dirname(latex_path)
        paths_to_copy = set()
        self.paths_copied.append(latex_path)
        for line_index, line in enumerate(latex_iter):
            if self.si_pattern.match(line):
                self.si_started = True
                self.figure_index = 0
                out.write('\\clearpage\n')
                out.write('\\setcounter{table}{0}\n')
                out.write('\\setcounter{figure}{0}\n')
                if self.strip_si:
                    tables, figs = self.parse_table_and_figure_refs(latex_iter, line_index)
                    if tables:
                        out.write('\\section*{SI Table Captions}\n')
                        for tl in sublist(tables, 18):
                            out.write('{0}\n'.format('\n'.join([str(x) for x in tl])))
                            out.write('\\clearpage\n')
                    if figs:
                        out.write('\\section*{SI Figure Captions}\n')
                        for fl in sublist(figs, 18):
                            out.write('{0}\n'.format('\n'.join([str(x) for x in fl])))
                            out.write('\\clearpage\n')
                    out.write('\\end{document}\n')
                    break
            if self.strip_comments and line.strip().startswith('%'):
                continue
            if self.exclude_caption_setup and self.caption_setup_pattern.match(line):
                continue
            new_line = line
            for k, v in self.path_patterns.iteritems():
                m = v.match(line)
                if m:
                    raw_path =  m.group('path')
                    p = os.path.realpath(os.path.join(project_dir, raw_path))
                    fix_bib_ext = False
                    fix_bst_ext = False
                    fix_cls_ext = False
                    if (k == 'bib') and os.path.splitext(raw_path)[-1] != '.bib':
                        fix_bib_ext = True
                        p += '.bib'
                    elif (k == 'bib_style') and os.path.splitext(raw_path)[-1] != '.bst':
                        fix_bst_ext = True
                        p += '.bst'
                    elif (k == 'documentclass') and os.path.splitext(raw_path)[-1] != '.cls':
                        fix_cls_ext = True
                        p += '.cls'
                    if k == 'input':
                        self._bundle(p)
                        file_name = os.path.basename(p)
                        new_line = new_line.replace(raw_path, file_name)
                        if self.merge:
                            new_line = ''
                    else:
                        write_line = True
                        file_name = os.path.basename(p)
                        if self.is_graphic_key(k):
                            file_name = '{0}{1}'.format(self.get_figure_prefix(),
                                    file_name)
                            if self.strip_figures:
                                if k != 'graphic':
                                    ref = self.finish_parsing_ref(latex_iter,
                                            pattern_key = k,
                                            pattern_line = line,
                                            pattern_match = m,
                                            offset = line_index)
                                    out.write('{0}\n'.format(str(ref)))
                                write_line = False
                        new_tex_path = file_name
                        if fix_bib_ext or fix_bst_ext or fix_cls_ext:
                            new_tex_path = os.path.splitext(new_tex_path)[0]
                        if write_line:
                            new_line = new_line.replace(raw_path, new_tex_path)
                        else:
                            new_line = ''
                        if (k == 'documentclass') and (not os.path.exists(p)):
                            break
                        paths_to_copy.add((p, os.path.join(self.dest_dir, file_name)))
                    break
            out.write(new_line)
        if out != self.out_stream:
            out.close()
        latex_stream.close()
        s, f = self.copy_files(paths_to_copy)
        self.paths_copied.extend(s)
        self.paths_failed.extend(f)

    @classmethod
    def copy_files(cls, list_of_tuples):
        paths_copied = []
        paths_failed = []
        for paths in list_of_tuples:
            if os.path.exists(paths[1]):
                raise Exception('Multiple files with name {0}!'.format(paths[1]))
            try:
                shutil.copyfile(paths[0], paths[1])
            except IOError, e:
                _LOG.error('Could not copy file from path {0!r}'.format(paths[0]))
                paths_failed.append(paths[0])
            else:
                paths_copied.append(paths[0])
        return paths_copied, paths_failed


    def parse_table_and_figure_refs(self, line_iter, offset=0):
        _LOG.info('Parsing ref targets from {0}...'.format(line_iter.name))
        tables = []
        figures = []
        for line_index, line in enumerate(line_iter):
            for h, h_pattern in self.header_patterns.iteritems():
                m = h_pattern.match(line)
                if m:
                    if h == 'input':
                        project_dir = os.path.dirname(line_iter.name)
                        p = os.path.realpath(os.path.join(project_dir,
                                m.groups()[0]))
                        t, f = self.parse_table_and_figure_refs(open(p, 'rU'))
                        tables.extend(t)
                        figures.extend(f)
                        continue
                    ref = self.finish_parsing_ref(line_iter,
                            pattern_key = h,
                            pattern_line = line,
                            pattern_match = m,
                            offset = line_index + offset)
                    if isinstance(ref, LatexTableRef):
                        tables.append(ref)
                    elif isinstance(ref, LatexFigureRef):
                        figures.append(ref)
        return tables, figures
    
    def finish_parsing_ref(self, line_iter, pattern_key, pattern_line,
            pattern_match,
            offset = 0):
        assert((pattern_key in self.header_patterns.keys()) and
                (pattern_key != 'input'))
        search_str = pattern_line
        line_index = 0
        if self.custom_fig_path_patterns.has_key(pattern_key):
            stop = re.compile(r'.*(?<!ref)\{fig[a-zA-Z0-9:-_]+\}.*')
        else:
            stop = re.compile(r'[^%]*\\end\s*\{\s*' + pattern_match.groups()[0] +
                              r'\s*\}.*$')
        while True:
            try:
                next_line = line_iter.next()
                line_index += 1
            except StopIteration:
                _LOG.warning('Could not find end of definition for '
                        '{0} at line {1} of {2}... skipping!'.format(
                            pattern_key, line_index+offset+1, line_iter.name))
                search_str = None
                break
            if next_line.strip().startswith('%'):
                continue
            search_str += next_line
            if stop.match(next_line):
                break
        if search_str:
            if self.custom_fig_path_patterns.has_key(pattern_key):
                fig_info = self.parse_custom_figure(search_str)
                caption_setup = fig_info.get('caption_setup', None)
                if caption_setup is None:
                    if pattern_key.startswith('si'):
                        caption_setup = 'name=Figure S, labelformat=noSpace, listformat=sFigList'
                    else:
                        caption_setup = 'listformat=figList'
                attributes = {'caption_setup': caption_setup,
                              'caption': fig_info.get('caption', ''),
                              'label': fig_info.get('label', None),
                              'exclude_caption_setup': self.exclude_caption_setup}
                return LatexFigureRef(**attributes)
            else:
                attributes = {'caption_setup': None,
                              'caption': '',
                              'label': None,
                              'exclude_caption_setup': self.exclude_caption_setup}
                for a, a_pattern in self.attribute_patterns.iteritems():
                    s = a_pattern.search(search_str)
                    if s:
                        attributes[a] = get_top_level_contents(
                                s.groups()[0])
                if pattern_key == 'table':
                    return LatexTableRef(**attributes)
                elif pattern_key == 'figure':
                    return LatexFigureRef(**attributes)
        raise Exception('Problem parsing {0} at line {1} of {2}'.format(
                pattern_key, line_index+offset+1, line_iter.name))

    @classmethod
    def parse_custom_figure(cls, string):
        fields = list(top_level_content_iter(string))
        if len(fields) == 3:
            return dict(zip(['path', 'caption', 'label'], fields))
        elif len(fields) == 5:
            return dict(zip(['size', 'path', 'caption_setup', 'caption', 'label'], fields))
        else:
            raise Exception('could not parse custom figure string '
                    '{0!r}'.format(string))

    
def mkdr(path):
    """
    Creates directory `path`, but suppresses error if `path` already exists.
    """
    try:
        os.makedirs(path)
    except OSError, e:
        if e.errno == errno.EEXIST:
            pass
        else:
            raise

def expand_path(path):
    return os.path.abspath(os.path.realpath(os.path.expanduser(
            os.path.expandvars(path))))

def copy_latex_file(latex_path, dest_path, over_write = False,
        strip_comments = False):
    latex_path = expand_path(latex_path)
    dest_path = expand_path(dest_path)
    if os.path.isdir(dest_path):
        dest_path = os.path.join(dest_path, os.path.basename(latex_path))
    if os.path.exists(dest_path) and (not over_write):
        raise Exception('Destination path {0!r} already exists'.format(
                dest_path))
    path_patterns = SubmissionBundler.path_patterns
    out = open(dest_path, 'w')
    latex_stream = open(latex_path, 'rU')
    latex_iter = iter(latex_stream)
    project_dir = os.path.dirname(latex_path)
    dest_dir = os.path.dirname(dest_path)
    for line_index, line in enumerate(latex_iter):
        if strip_comments and line.strip().startswith('%'):
            continue
        new_line = line
        for k, v in path_patterns.iteritems():
            m = v.match(line)
            if m:
                raw_path =  m.group('path')
                p = os.path.realpath(os.path.join(project_dir, raw_path))
                new_path = os.path.relpath(p, dest_dir)
                new_line = new_line.replace(raw_path, new_path)
        out.write(new_line)
    out.close()
    latex_stream.close()

def sublist(l, size=10):
    return (l[i: i + size] for i in range(0, len(l), size))

def get_top_level_contents(string, start='{', end='}'):
    content_iter = top_level_content_iter(string = string,
            start = start,
            end = end)
    try:
        return content_iter.next()
    except StopIteration:
        return None

def top_level_content_iter(string, start='{', end='}'):
    delim = re.compile('([' + start + end + '])')
    start_index = string.find(start)
    nested_level = 0
    if start_index == -1:
        return
    search_index = None
    for s in delim.finditer(string[start_index:]):
        d = s.groups()[0]
        delim_index = s.start() + start_index
        if d == start:
            nested_level += 1
            if nested_level == 1:
                search_index = delim_index
        else:
            nested_level -= 1
            if nested_level == 0:
                yield string[search_index + 1: delim_index]

def main():
    from optparse import OptionParser
    description = '{name} {version}'.format(**_program_info)
    usage = "\n  %prog [options] <LATEX_FILE_PATH>"
    parser = OptionParser(usage=usage, description=description,
                          version=_program_info['version'],
                          add_help_option=True)
    parser.add_option("--preserve-comments", dest="preserve_comments",
            default=False,
            action="store_true",
            help=("Preserve comments in Latex files. Default is to strip "
                  "them out."))
    parser.add_option("--append-figure-names", dest="append_figure_names",
            default=False,
            action="store_true",
            help=("Append the names of image files with 'figure_1', "
                  "'figure_2', etc. in the order of their appearance in "
                  "the document."))
    parser.add_option("--strip-si", dest="strip_si", default=False,
            action="store_true",
            help = ("Remove all supplemental material from document; only "
                    "include table and figure captions."))
    parser.add_option("--strip-figures", dest="strip_figures", default=False,
            action="store_true",
            help=("Remove figures from document; only include captions."))
    parser.add_option("--exclude-caption-setup", dest="exclude_caption_setup",
            default=False,
            action="store_true",
            help=("Do not include `captionsetup` calls."))
    parser.add_option("--merge", dest="merge",
            default=False,
            action="store_true",
            help=("Merge all content into a single LaTeX file."))
    parser.add_option("--cp", dest="cp", default=False,
            action="store_true",
            help=("Only copy the latex file and update its paths."))
    parser.add_option("-v", "--verbose", dest="verbose", default=False, 
            action="store_true",
            help="Verbose output.")
    parser.add_option("-d", "--debugging", dest="debugging", default=False, 
            action="store_true",
            help="Run in debugging mode.")
    (options, args) = parser.parse_args()

    if options.debugging:
        _LOG.setLevel(logging.DEBUG)
    elif options.verbose and not options.debugging:
        _LOG.setLevel(logging.INFO)
    else:
        _LOG.setLevel(logging.WARNING)
    
    if options.cp:
        if len(args) != 2:
            _LOG.error("To copy a file, you must specify the source and "
                    "destination path.")
            sys.stderr.write(str(parser.print_help()))
            sys.exit(-1)
        copy_latex_file(args[0], args[1],
                strip_comments = (not options.preserve_comments))
        sys.exit(0)

    if len(args) != 1:
        _LOG.error("Program requires path to main latex file")
        sys.stderr.write(str(parser.print_help()))
        sys.exit(-1)

    latex_path = expand_path(args[0])
    project_dir = os.path.dirname(latex_path)
    submit_dir = os.path.join(project_dir, 'submit')
    bundler = SubmissionBundler(
            latex_path = latex_path,
            dest_dir = submit_dir,
            strip_comments = not options.preserve_comments,
            append_figure_names = options.append_figure_names,
            strip_si = options.strip_si,
            strip_figures = options.strip_figures,
            exclude_caption_setup = options.exclude_caption_setup,
            merge = options.merge)
    paths_copied, paths_failed = bundler.bundle()
    if paths_copied:
        _LOG.info('Files successfully copied:\n\t{0}\n'.format(
                "\n\t".join(paths_copied)))
    if paths_failed:
        _LOG.info('Files that failed to be copied:\n\t{0}\n'.format(
                "\n\t".join(paths_failed)))
        
if __name__ == '__main__':
    main()


