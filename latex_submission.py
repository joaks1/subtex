#! /usr/bin/env python

import os
import sys
import logging
import itertools
import re
import shutil

logging.basicConfig(level=logging.WARNING)
_LOG = logging.getLogger("latex_submission")
_program_info = {
    'name': 'latex_submission',
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
            label=None):
        self.caption_setup = caption_setup
        self.caption = caption
        self.label = label

    def to_string(self, indent='    '):
        s = ''
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

def bundle_for_submission(latex_path, dest_dir,
        strip_comments=True,
        append_figure_names=False,
        strip_si=False):
    _LOG.info('Bundling latex file {0} to {1}'.format(latex_path, dest_dir))
    path_patterns = {
            'bib_style': re.compile(r'[^%]*\\bibliographystyle.*\{([^}]*)\}.*'),
            'input': re.compile(r'[^%]*\\input.*\{([^}]*)\}.*'),
            'bib': re.compile(r'[^%]*\\bibliography.*\{([^}]*)\}.*'),
            'graphic': re.compile(r'[^%]*\\includegraphics.*\{([^}]*)\}.*'),}
    si_pattern = re.compile(r'^\s*[%]+\s*supporting\s+info.*$', re.IGNORECASE)
    out_path = os.path.join(dest_dir, os.path.basename(latex_path))
    if not os.path.exists(dest_dir):
        mkdr(dest_dir)
    out = open(out_path, 'w')
    latex_stream = open(latex_path, 'rU')
    latex_iter = iter(latex_stream)
    project_dir = os.path.dirname(latex_path)
    paths_to_copy = set()
    paths_copied = [latex_path]
    paths_failed = []
    figure_index = 0
    for line_index, line in enumerate(latex_iter):
        if strip_si and si_pattern.match(line):
            tables, figs = parse_table_and_figure_refs(latex_iter, line_index)
            if tables:
                out.write('\\clearpage\n')
                out.write('\\section*{SI Table Captions}\n')
                out.write('\\setcounter{table}{0}\n')
                for tl in sublist(tables, 5):
                    out.write('{0}\n'.format('\n'.join([str(x) for x in tl])))
                    out.write('\\clearpage\n')
            if figs:
                out.write('\\clearpage\n')
                out.write('\\section*{SI Figure Captions}\n')
                out.write('\\setcounter{figure}{0}\n')
                for fl in sublist(figs, 5):
                    out.write('{0}\n'.format('\n'.join([str(x) for x in fl])))
                    out.write('\\clearpage\n')
            out.write('\\end{document}\n')
            break
        if strip_comments and line.strip().startswith('%'):
            continue
        new_line = line
        for k, v in path_patterns.iteritems():
            m = v.match(line)
            if m:
                raw_path =  m.groups()[0]
                p = os.path.realpath(os.path.join(project_dir, raw_path))
                if k == 'input':
                    s, f = bundle_for_submission(p, dest_dir)
                    file_name = os.path.basename(p)
                    new_line = new_line.replace(raw_path, file_name)
                    paths_copied.extend(s)
                    paths_failed.extend(f)
                else:
                    file_name = os.path.basename(p)
                    if append_figure_names and k == 'graphic':
                        figure_index += 1
                        file_name = 'figure_{0}_{1}'.format(figure_index,
                                file_name)
                    new_line = new_line.replace(raw_path, file_name)
                    paths_to_copy.add((p, os.path.join(dest_dir, file_name)))
        out.write(new_line)
    out.close()
    latex_stream.close()
    s, f = copy_files(paths_to_copy)
    return paths_copied + s, paths_failed + f

def sublist(l, size=10):
    return (l[i: i + size] for i in range(0, len(l), size))

def parse_table_and_figure_refs(line_iter, offset=0):
    header_patterns = {
        'table': re.compile(r'[^%]*\\begin\s*\{\s*(\w*table\w*)\s*\}.*',
                re.IGNORECASE),
        'figure': re.compile(r'[^%]*\\begin\s*\{\s*(\w*figure\w*)\s*\}.*',
                re.IGNORECASE),
        'input': re.compile(r'[^%]*\\input.*\{([^}]*)\}.*'),}
    attribute_patterns = {
        # 'caption_setup': re.compile(r'\\captionsetup\s*\{\s*([^}]*)\s*\}'),
        # 'caption': re.compile(r'\\caption\s*\{\s*([^}]*)\s*\}'),
        # 'label': re.compile(r'\\label\s*\{\s*([^}]*)\s*\}'),}
        'caption_setup': re.compile(r'\\captionsetup\s*(\{.*)', re.DOTALL),
        'caption': re.compile(r'\\caption\s*\[*\s*\]*\s*(\{.*)', re.DOTALL),
        'label': re.compile(r'\\caption\s*\[*\s*\]*\s*\{.*\\label\s*(\{.*)',
                re.DOTALL),}
    _LOG.info('Parsing ref targets from {0}...'.format(line_iter.name))
    tables = []
    figures = []
    for line_index, line in enumerate(line_iter):
        for h, h_pattern in header_patterns.iteritems():
            m = h_pattern.match(line)
            if m:
                if h == 'input':
                    project_dir = os.path.dirname(line_iter.name)
                    p = os.path.realpath(os.path.join(project_dir,
                            m.groups()[0]))
                    t, f = parse_table_and_figure_refs(open(p, 'rU'))
                    tables.extend(t)
                    figures.extend(f)
                    continue
                search_str = line
                stop = re.compile(r'[^%]*\\end\s*\{\s*' + m.groups()[0] +
                                  r'\s*\}.*$')
                while True:
                    try:
                        next_line = line_iter.next()
                    except StopIteration:
                        _LOG.warning('Could not find end of definition for '
                                '{0} at line {1} of {2}... skipping!'.format(
                                    h, line_index+offset+1, line_iter.name))
                        search_str = None
                        break
                    if next_line.strip().startswith('%'):
                        continue
                    search_str += next_line
                    if stop.match(next_line):
                        break
                if search_str:
                    attributes = {'caption_setup': None, 'caption': '',
                                  'label': None}
                    for a, a_pattern in attribute_patterns.iteritems():
                        s = a_pattern.search(search_str)
                        if s:
                            attributes[a] = get_top_level_contents(
                                    s.groups()[0])
                    if h == 'table':
                        tables.append(LatexTableRef(**attributes))
                    elif h == 'figure':
                        figures.append(LatexFigureRef(**attributes))
                    else:
                        raise Exception('problem parsing {0}'.format(
                                line.strip()))
    return tables, figures

def get_top_level_contents(string, start='{', end='}'):
    delim = re.compile('([' + start + end + '])')
    start_index = string.find(start)
    nested_level = 0
    if start_index == -1:
        return None
    search_index = start_index + 1
    while True:
        s = delim.search(string[search_index:])
        if not s:
            return None
        d = s.groups()[0]
        delim_index = string.find(d, search_index)
        if d == start:
            nested_level += 1
        else:
            nested_level -= 1
        if nested_level < 0:
            return string[start_index + 1: delim_index]
        search_index = delim_index + 1

def copy_files(list_of_tuples):
    paths_copied = []
    paths_failed = []
    for paths in list_of_tuples:
        try:
            shutil.copyfile(paths[0], paths[1])
        except IOError, e:
            _LOG.error('Could not copy file from path {0!r}'.format(paths[0]))
            paths_failed.append(paths[0])
        else:
            paths_copied.append(paths[0])
    return paths_copied, paths_failed

def main():
    from optparse import OptionParser
    description = '{name} {version}'.format(**_program_info)
    usage = "\n  %prog [options] <LATEX_FILE_PATH>"
    parser = OptionParser(usage=usage, description=description,
                          version=_program_info['version'],
                          add_help_option=True)
    parser.add_option("-v", "--verbose", dest="verbose", default=False, 
            action="store_true",
            help="Verbose output.")
    parser.add_option("-d", "--debugging", dest="debugging", default=False, 
            action="store_true",
            help="Run in debugging mode.")
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
            help=("Remove all supplemental material from document."))
    (options, args) = parser.parse_args()

    if options.debugging:
        _LOG.setLevel(logging.DEBUG)
    elif options.verbose and not options.debugging:
        _LOG.setLevel(logging.INFO)
    else:
        _LOG.setLevel(logging.WARNING)
    
    if len(args) != 1:
        _LOG.error("Program requires path to main latex file")
        sys.stderr.write(str(parser.print_help()))
        sys.exit(-1)

    latex_path = os.path.abspath(os.path.expanduser(os.path.expandvars(args[0])))
    project_dir = os.path.dirname(latex_path)
    submit_dir = os.path.join(project_dir, 'submit')
    paths_copied, paths_failed = bundle_for_submission(
            latex_path = latex_path,
            dest_dir = submit_dir,
            strip_comments = not options.preserve_comments,
            append_figure_names = options.append_figure_names,
            strip_si = options.strip_si)
    if paths_copied:
        _LOG.info('Files successfully copied:\n\t{0}\n'.format(
                "\n\t".join(paths_copied)))
    if paths_failed:
        _LOG.info('Files that failed to be copied:\n\t{0}\n'.format(
                "\n\t".join(paths_failed)))
        
if __name__ == '__main__':
    main()


