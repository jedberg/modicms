modicms
=======

Overview
--------

modicms, pronounced "modicum", is a simple content management system that 
generates static files. File processing is handled with a pipeline metaphor.
modicms will iterate through files in a given directory and its subdirectories
and pass the files through a pipeline.

Example Configuration
---------------------

    from modicms import *

    (Scan('source') >> MatchPath()
        .match('\.md$', Read() >>
                        ParseHeaders() >>
                        InterpretMarkdown() >>
                        WrapInMako('basic.mako') >>
                        WriteTo('/var/www'))
        .match('\.(css|js)$', CopyTo('/var/www'))
    )

The configuration above will scan through files in `source` and its
subdirectories and process each file depending on its extension.
For CSS and JavaScript, the file will be copied directly to its
corresponding location in the output root (so `source/js/test.js`
will become `/var/www/js/test.js`).

Markdown files, on the other hand, will be processed with a more
involved pipeline. Each file's contents will be read in, metadata headers 
will be parsed, markdown will be converted to HTML, which is then wrapped
using a template written in mako, before finally being written out to file.
