Table of Contents
=================

 -  [Overview](#overview)
 -  [Requirements](#requirements)
 -  [Installation](#installation)
 -  [Documentation](#documentation)
 -  [License](#license)

Overview
========

If you are anything like me, your latex documents compile from files
hierarchically nested in directories. For example, your latex project
might looks something like:

    bib/
        references.bib
    ms/
        ms-discussion.tex
        ms-figures.tex
        ms-intro.tex
        ms-results.tex
        ms-tables.tex
        ms.tex
    utils/
        macros.tex
        preamble.tex
    images/
        fig1.pdf
        fig2.pdf

It's nice to keep things organized! However, when it comes time to submit your
manuscript to a journal, you can't submit your whole directory structure.  If
you have a lot of files, it becomes a real pain to update all the paths in the
files so that the document will compile from all its constituents piled into
one flat directory.

That was my motivation for `subtex.py`. It's a simple Python script that will,
given the main latex file path, recursively work through all the files it
depends on, copy them into a `submit` directory and update all the paths.

For example, if, in the example above, `ms.tex` is the main latex file. Using
`subtex.py` will give you:

    bib/
        references.bib
    ms/
        ms-discussion.tex
        ms-figures.tex
        ms-intro.tex
        ms-results.tex
        ms-tables.tex
        ms.tex
        submit/
            fig1.pdf
            fig2.pdf
            macros.tex
            ms-discussion.tex
            ms-figures.tex
            ms-intro.tex
            ms-results.tex
            ms-tables.tex
            ms.tex
            preamble.tex
            references.bib
    utils/
        macros.tex
        preamble.tex
    images/
        fig1.pdf
        fig2.pdf

All of your original files are untouched, and `submit` is a self-contained
subdirectory with all the necessary files with updated paths to build your
document.

That is the basic idea. I wrote the script for my latex-submission needs in
mind, and the script might not work "out of the box" for you. However, it
should be relatively easy to tweak if it does not.

Requirements
============

Python is the only requirement. The script has only been tested version version
2.7 of Python.

Installation
============

Open a terminal window and navigate to where you would like to put the `subtex`
repository. Then, use `git` to clone the repository:

    git clone https://github.com/joaks1/subtex.git

Move into the `subtex` directory:
    
    cd subtex

Call up the `subtex.py` help menu:

    ./subtex.py -h

If you wish, you can copy `subtex.py` to a location in your PATH.

Documentation
=============

The basic usage is

    subtex.py manuscript.tex

where `manuscript.tex` is the main latex file used to compile the document.

Acknowledgements
================

This software benefited from funding provided to Jamie Oaks from the National
Science Foundation (DEB 1011423 and DBI 1308885).

License
=======

Copyright (C) 2013 Jamie Oaks

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation; either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License along
with this program. If not, see <http://www.gnu.org/licenses/>.

See "LICENSE.txt" for full terms and conditions of usage.

