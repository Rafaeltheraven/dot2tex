# -*- coding: utf-8 -*-
"""Convert graphviz graphs to LaTeX-friendly formats

Various tools for converting graphs generated by the graphviz library
to formats for use with LaTeX.

Copyright (c) 2006-2019, Kjell Magne Fauske

"""

# Copyright (c) 2006-2019, Kjell Magne Fauske
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to
# deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or
# sell copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS
# IN THE SOFTWARE.
from .base import DEFAULT_TEXTENCODING, DEFAULT_OUTPUT_FORMAT
from .pgfformat import Dot2PGFConv, Dot2TikZConv, PositionsDotConv
from .pstricksformat import Dot2PSTricksConv, Dot2PSTricksNConv

__author__ = 'Kjell Magne Fauske'
__version__ = '2.12.dev'
__license__ = 'MIT'

import argparse
import os.path as path
import sys, os, re
import logging

from . import dotparsing

# initialize logging module
log = logging.getLogger("dot2tex")

# label margins in inches

# Todo: set papersize based on bb

# Todo: Support linewidth in draw string
# Todo: Support linestyle in draw string
# Todo: Need to reconsider edge draw order.
# See for instance html2.xdot

# Examples of draw strings
# c 5 -black F 14.000000 11 -Times-Roman T 99 159 0 44 8 -a_1 test



helpmsg = """Failed to parse the input data. Is it a valid dot file?
Try to input xdot data directly. Example:
    dot -Txdot file.dot | dot2tex > file.tex

If this does not work, check that you have an updated version of PyParsing and
Graphviz. Users have reported problems with old versions. You can also run
dot2tex in debug mode using the --debug option:
    dot2tex --debug file.dot
A file dot2tex.log will be written to the current directory with detailed
information useful for debugging."""


def create_options_parser():
    """Create and and return an options parser."""
    description = 'Convert dot files to PGF/TikZ graphics' + \
                  ' for inclusion in LaTeX.'
    parser = argparse.ArgumentParser(prog='dot2tex', description=description)

    parser.add_argument(
        '-f', '--format', action='store', dest='format',
        choices=('pstricks', 'pgf', 'pst', 'tikz', 'psn'),
        help="Set output format to 'v' (pstricks, pgf, pst, tikz, psn) ",
        metavar="v"
    )
    parser.add_argument(
        '-t', '--texmode', dest='texmode', default='verbatim',
        choices=('math', 'verbatim', 'raw'),
        help='Set text mode (verbatim, math, raw).'
    )
    parser.add_argument(
        '-d', '--duplicate', dest='duplicate', action='store_true',
        default=False, help='Try to duplicate Graphviz graphics'
    )
    parser.add_argument(
        '-s', '--straightedges', dest='straightedges', action='store_true',
        default=False, help='Force straight edges'
    )
    parser.add_argument(
        '--template', dest='templatefile', action='store',
        metavar='FILE'
    )
    parser.add_argument(
        '-o', '--output', dest='outputfile', action='store',
        metavar='FILE', default=None, help='Write output to FILE'
    )
    parser.add_argument(
        '--force', dest='force', action='store_true', default=False,
        help='Force recompilation, even if output file is newer than input file'
    )
    parser.add_argument(
        '-e', '--encoding', dest='encoding', action='store',
        choices=('utf8', 'latin1'), default=DEFAULT_TEXTENCODING,
        help='Set text encoding to utf8 or latin1'
    )
    parser.add_argument(
        '-V', '--version', dest='printversion', action='store_true',
        help='Print version information and exit', default=False
    )
    parser.add_argument(
        '-w', '--switchdraworder', dest='switchdraworder',
        action='store_true', help='Switch draw order', default=False
    ),
    parser.add_argument(
        '-p', '-c', '--preview', '--crop', dest='crop', action='store_true',
        help='Use preview.sty to crop graph', default=False
    )
    parser.add_argument(
        '--margin', dest='margin', action='store',
        help='Set preview margin', default='0pt'
    )
    parser.add_argument(
        '--docpreamble', dest='docpreamble', action='store',
        help='Insert TeX code in document preamble', metavar='TEXCODE'
    )
    parser.add_argument(
        '--figpreamble', dest='figpreamble', action='store',
        help='Insert TeX code in figure preamble', metavar='TEXCODE'
    )
    parser.add_argument(
        '--figpostamble', dest='figpostamble', action='store',
        help='Insert TeX code in figure postamble', metavar='TEXCODE'
    )
    parser.add_argument(
        '--graphstyle', dest='graphstyle', action='store',
        help='Insert graph style', metavar='STYLE'
    )
    parser.add_argument(
        '--gvcols', dest='gvcols', action='store_true',
        default=False, help='Include gvcols.tex'
    )
    parser.add_argument(
        '--figonly', dest='figonly', action='store_true',
        help='Output graph with no preamble', default=False
    )
    parser.add_argument(
        '--codeonly', dest='codeonly', action='store_true',
        help='Output only drawing commands', default=False
    )
    parser.add_argument(
        '--styleonly', dest='styleonly', action='store_true',
        help='Use style parameter only', default=False)
    parser.add_argument(
        '--debug', dest='debug', action='store_true',
        help='Show additional debugging information', default=False
    )
    parser.add_argument(
        '--preproc', dest='texpreproc', action='store_true',
        help='Preprocess graph through TeX', default=False
    )
    parser.add_argument('--alignstr', dest='alignstr', action='store')
    parser.add_argument(
        '--valignmode', dest='valignmode', default='center',
        choices=('center', 'dot'),
        help='Set vertical alginment mode  (center, dot).'
    )
    parser.add_argument(
        '--nominsize', dest='nominsize', action='store_true',
        help='No minimum node sizes', default=False
    )
    parser.add_argument(
        '--usepdflatex', dest='usepdflatex', action='store_true',
        help='Use PDFLaTeX for preprocessing', default=False
    )
    parser.add_argument(
        '--tikzedgelabels', dest='tikzedgelabels', action='store_true',
        help='Let TikZ place edge labels', default=False
    )
    parser.add_argument(
        '--nodeoptions', dest='nodeoptions', action='store',
        help='Set options for nodes', metavar='OPTIONS'
    )
    parser.add_argument(
        '--edgeoptions', dest='edgeoptions', action='store',
        help='Set options for edges', metavar='OPTIONS'
    )
    parser.add_argument(
        '--runtests', dest='runtests',
        help="Run tests", action="store_true", default=False
    )
    parser.add_argument(
        "--prog", action="store", dest="prog", default='dot',
        choices=('dot', 'neato', 'circo', 'fdp', 'twopi'),
        help='Use v to process the graph', metavar='v'
    )
    parser.add_argument(
        '--progoptions', action='store', dest='progoptions',
        default='', help='Pass options to graph layout engine',
        metavar='OPTIONS'
    )
    parser.add_argument(
        '--autosize', dest='autosize',
        help='Preprocess graph and then run Graphviz',
        action='store_true', default=False
    )
    parser.add_argument(
        '--cache', dest='cache', action='store_true', default=False
    )
    parser.add_argument(
        '--pgf118', dest='pgf118', action='store_true',
        help='Generate code compatible with PGF 1.18', default=False
    )
    parser.add_argument(
        '--pgf210', dest='pgf210', action='store_true',
        help='Generate code compatible with PGF 2.10', default=False
    )
    parser.add_argument(
        'inputfile', action='store',
        nargs='?', default=None, help='Input dot file'
    )
    return parser


def process_cmd_line():
    """Set up and parse command line options"""

    parser = create_options_parser()
    options = parser.parse_args()

    return options, parser


def _runtests():
    import doctest

    doctest.testmod()


def print_version_info():
    print("Dot2tex version % s" % __version__)


def load_dot_file(filename):
    with open(filename, 'r') as f:
        dotdata = f.readlines()
    log.info('Data read from %s' % filename)
    return dotdata


def main(run_as_module=False, dotdata=None, options=None):
    """Run dot2tex and convert graph

    """
    import platform

    global log
    if not run_as_module:
        options, parser = process_cmd_line()
        # configure console logger
        console = logging.StreamHandler()
        console.setLevel(logging.WARNING)
        # set a format which is simpler for console use
        formatter = logging.Formatter('%(levelname)-8s %(message)s')
        # tell the handler to use this format
        console.setFormatter(formatter)
        log.addHandler(console)
    if options.runtests:
        log.warning('running tests')
        _runtests()
        sys.exit(0)

    if options.debug:
        # initalize log handler
        if run_as_module:
            pass
        else:
            hdlr = logging.FileHandler('dot2tex_run.log')
            log.addHandler(hdlr)
            formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
            hdlr.setFormatter(formatter)
        log.setLevel(logging.DEBUG)
        nodebug = False
    else:
        nodebug = True

    log.info('------- Start of run -------')
    log.info("Dot2tex version % s" % __version__)
    log.info("System information:\n"
             "  Python: %s \n"
             "  Platform: %s\n"
             "  Pyparsing: %s",
             sys.version_info, platform.platform(),
             dotparsing.pyparsing_version)
    log.info('dot2tex called with: %s' % sys.argv)
    log.info('Program started in %s' % os.getcwd())
    if not run_as_module:
        if options.printversion:
            print_version_info()
            sys.exit(0)

        if options.inputfile is None:
            log.info('Data read from standard input')
            dotdata = sys.stdin.readlines()
        else:
            # exit if target file newer than dot source
            inputfile = options.inputfile
            outputfile = options.outputfile

            if outputfile is not None and options.force is False:
                input_exists = os.access(inputfile, os.F_OK)
                output_exists = os.access(outputfile, os.F_OK)

                if input_exists and output_exists:
                    input_modified_time = os.stat(inputfile)[8]
                    output_modified_time = os.stat(outputfile)[8]

                    if input_modified_time < output_modified_time:
                        print('skip: input file older than output file.')
                        sys.exit(0)
            try:
                log.debug('Attempting to read data from %s', options.inputfile)
                dotdata = load_dot_file(options.inputfile)
            except:
                if options.debug:
                    log.exception('Failed to load file %s', options.inputfile)
                else:
                    log.error('Failed to load file %s', options.inputfile)
                sys.exit(1)
    else:
        # Make sure dotdata is compatitle with the readlines data
        dotdata = dotdata.splitlines(True)

    s = ""
    # look for a line containing an \input
    m = re.search(r"^\s*\\input\{(?P<filename>.+?)\}",
                  "".join(dotdata), re.MULTILINE)
    if m:
        filename = m.group(1)
        log.info('Found \\input{%s}', filename)
        try:
            dotdata = load_dot_file(filename)
        except:
            if options.debug:
                log.exception('Failed to load \\input{%s}', filename)
            else:
                log.error('Failed to load \\input{%s}', filename)
            if run_as_module:
                raise
            else:
                sys.exit(1)

    # I'm not quite sure why this is necessary, but some files
    # produces data with line endings that confuses pydot/pyparser.
    # Note: Whitespace at end of line is sometimes significant
    log.debug('Input data:\n' + "".join(dotdata))
    lines = [line for line in dotdata if line.strip()]
    dotdata = "".join(lines)

    if options.cache and not run_as_module:
        import hashlib, pickle

        if options.inputfile is not None and options.outputfile:
            log.info('Caching enabled')
            inputfilename = options.inputfile
            # calculate hash from command line options and dotdata
            m = hashlib.md5()
            m.update((dotdata + "".join(sys.argv)).encode('utf-8'))
            inputhash = m.digest()
            log.debug('Hash for %s and command line : %s', inputfilename, inputhash)
            # now look for a hash file
            hashfilename = path.join(path.dirname(inputfilename), 'dot2tex.cache')
            key = path.basename(inputfilename)
            hashes = {}
            if path.exists(hashfilename):
                log.info('Loading hash file %s', hashfilename)
                with open(hashfilename, 'rb') as f:
                    try:
                        hashes = pickle.load(f)
                    except:
                        log.exception('Failed to load hashfile')
            if hashes.get(key) == inputhash and path.exists(options.outputfile):
                log.info('Input has not changed. Will not convert input file')
                sys.exit(0)
            else:
                log.info('Hash or output file not found. Converting file')
                hashes[key] = inputhash
                with open(hashfilename, 'wb') as f:
                    try:
                        pickle.dump(hashes, f)
                    except:
                        log.warning('Failed to write hashfile')
        else:
            log.warning('You need to specify an input and output file for caching to work')

        pass

    # check for output format attribute
    fmtattr = re.findall(r'd2toutputformat=([a-z]*)', dotdata)
    extraoptions = re.findall(r'^\s*d2toptions\s*=\s*"(.*?)"\s*;?', dotdata, re.MULTILINE)
    if fmtattr:
        log.info('Found outputformat attribute: %s', fmtattr[0])
        gfmt = fmtattr[0]
    else:
        gfmt = None
    if extraoptions:
        log.debug('Found d2toptions attribute in graph: %s', extraoptions[0])
        if run_as_module:
            parser = create_options_parser()
        options = parser.parse_args(extraoptions[0].split(), options)
        if options.debug and nodebug:
            # initalize log handler
            if not run_as_module:
                hdlr = logging.FileHandler('dot2tex_run.log')
                log.addHandler(hdlr)
                formatter = logging.Formatter('%(asctime)s %(name)s %(levelname)s %(message)s')
                hdlr.setFormatter(formatter)
            log.setLevel(logging.DEBUG)
            nodebug = False

    output_format = options.format or gfmt or DEFAULT_OUTPUT_FORMAT
    options.format = output_format

    if output_format in ('pstricks', 'pst'):
        conv = Dot2PSTricksConv(options.__dict__)
    elif output_format == 'psn':
        conv = Dot2PSTricksNConv(options.__dict__)
    elif output_format == 'pgf':
        conv = Dot2PGFConv(options.__dict__)
    elif output_format == 'tikz':
        conv = Dot2TikZConv(options.__dict__)
    elif output_format == 'positions':
        conv = PositionsDotConv(options.__dict__)
    else:
        log.error("Unknown output format %s" % options.format)
        sys.exit(1)
    try:
        s = conv.convert(dotdata)
        log.debug('Output:\n%s', s)
        if options.autosize:
            conv.dopreproc = False
            s = conv.convert(s)
            log.debug('Output after preprocessing:\n%s', s)
        if options.outputfile:
            with open(options.outputfile, 'w') as f:
                f.write(s)
        else:
            if not run_as_module:
                print(s)
    except dotparsing.ParseException as err:
        errmsg = "Parse error:\n%s\n" % err.line + " " * (err.column - 1) + "^\n" + str(err)
        log.error(errmsg)
        if options.debug:
            log.exception('Failed to parse graph')
        if run_as_module:
            raise
        else:
            log.error(helpmsg)
    except SystemExit:
        if run_as_module:
            raise
    except:
        # log.error("Could not convert the xdot input.")
        log.exception('Failed to process input')
        if run_as_module:
            raise

    log.info('------- End of run -------')
    if run_as_module:
        return s


def convert_graph(dotsource, **kwargs):
    """Process dotsource and return LaTeX code

    Conversion options can be specified as keyword options. Example:
        convert_graph(data,format='tikz',crop=True)

    """
    parser = create_options_parser()

    options = parser.parse_args([])
    if kwargs.get('preproc', None):
        kwargs['texpreproc'] = kwargs['preproc']
        del kwargs['preproc']

    options.__dict__.update(kwargs)
    tex = main(True, dotsource, options)
    return tex

