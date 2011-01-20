# -*- coding: utf-8 -*-
"""
    Python documentation LaTeX file parser
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    For more documentation, look into the ``restwriter.py`` file.

    :copyright: 2007-2009 by Georg Brandl.
    :license: BSD.
"""

from .docnodes import CommentNode, RootNode, NodeList, ParaSepNode, \
     TextNode, EmptyNode, NbspNode, SimpleCmdNode, BreakNode, CommandNode, \
     DescLineCommandNode, InlineNode, IndexNode, SectioningNode, \
     EnvironmentNode, DescEnvironmentNode, TableNode, TabularNode, VerbatimNode, RstVerbatimNode, \
     ListNode, ItemizeNode, EnumerateNode, DescriptionNode, \
     DefinitionsNode, ProductionListNode, AmpersandNode, ExtLinkNode, ListingNode, FigureNode, MathNode, TOCNode

from .util import umlaut, empty
import sys, re

def walk(node):
    for x in node.walk():
        #print repr(x)
        yield x
        for y in walk(x):
            yield y

def fwalk(node, filter_=lambda:True):
    return filter(filter_, [_ for _ in walk(node)] )

def find_label(node):
    """ walk ahead to find the label """
    nlabel = fwalk(node, lambda _:isinstance(_,CommandNode) and _.cmdname == 'label')
    if len(nlabel) == 0:
        return None
    nlabel = nlabel[0]
    return ( nlabel.args[0].text.lower() if  isinstance(nlabel.args[0], TextNode) else None)

def find_caption_node(node):
    """ walk ahead to find the label """
    ncaption = fwalk(node, lambda _:isinstance(_,CommandNode) and _.cmdname == 'caption')
    if len(ncaption) == 0:
        return None
    return ncaption[0]

def find_subnode(node, type=ListingNode):
    """ walk ahead to look for listing """
    nfound = fwalk(node, lambda _:isinstance(_,type))
    if len(nfound) == 0:
        return None
    return nfound[0]



class ParserError(Exception):
    def __init__(self, msg, lineno):
        Exception.__init__(self, msg, lineno)

    def __str__(self):
        return '%s, line %s' % self.args


def generic_command(name, argspec, nodetype=CommandNode):
    def handle(self):
        args = self.parse_args('\\'+name, argspec)
        return nodetype(name, args)
    return handle

def sectioning_command(name):
    """ Special handling for sectioning commands: move labels directly following
        a sectioning command before it, as required by reST. """
    def handle(self):
        args = self.parse_args('\\'+name, 'M')
        snode = SectioningNode(name, args)
        for l, t, v, r in self.tokens:
            if t == 'command' and v == 'label':
                largs = self.parse_args('\\label', 'T')
                snode.args[0] = NodeList([snode.args[0], CommandNode('label', largs)])
                break
            if t == 'text':
                if not v.strip():
                    # discard whitespace; after a section that's no problem
                    continue
            self.tokens.push((l, t, v, r))
            break
        # no label followed
        return snode
    return handle

def generic_environment(name, argspec, nodetype=EnvironmentNode):
    def handle(self):
        args = self.parse_args(name, argspec)
        return nodetype(name, args, self.parse_until(self.environment_end))
    return handle


class DocParserMeta(type):
    def __init__(cls, name, bases, dict):
        for nodetype, commands in cls.generic_commands.iteritems():
            for cmdname, argspec in commands.iteritems():
                setattr(cls, 'handle_' + cmdname,
                        generic_command(cmdname, argspec, nodetype))

        for cmdname in cls.sectioning_commands:
            setattr(cls, 'handle_' + cmdname, sectioning_command(cmdname))

        for nodetype, envs in cls.generic_envs.iteritems():
            for envname, argspec in envs.iteritems():
                setattr(cls, 'handle_%s_env' % envname,
                        generic_environment(envname, argspec, nodetype))


class DocParser(object):
    """ Parse a Python documentation LaTeX file. """
    __metaclass__ = DocParserMeta

    def __init__(self, tokenstream, filename, extlinks={}):
        self.tokens = tokenstream
        self.filename = filename
        self.unrecognized = set()

        for name, (patn, prefix) in extlinks.items():
            setattr( self.__class__ , 'handle_' + name , generic_command( name, 'M' , ExtLinkNode ))

    def finish(self):
        if len(self.unrecognized) != 0:
            print '\n\n.. warning::\n   The following latex commands are not recognized and are ' \
                'ignored by this script. You may want to extend the DocParser class and ' \
                'define functions such as handle_CMD to handle them. You can also override '\
                'handle_unrecognized.\n'
            for cmd in self.unrecognized:
                print "   ",cmd

    def parse(self):
        self.rootnode = RootNode(self.filename, None)
        self.rootnode.children = self.parse_until(None)
        self.rootnode.transform()
        return self.rootnode

    def parse_until(self, condition=None, endatbrace=False):
        nodelist = NodeList()
        bracelevel = 0
        mathmode = False
        math = ''
        for l, t, v, r in self.tokens:
            #sys.stderr.write("[%s][%s][%s][%s]\n" % ( l,t,v,r ))  ## line, type[command/text/egroup/...] ,  

            if condition and condition(t, v, bracelevel):
                return nodelist.flatten()
            if mathmode:
                if t == 'mathmode':
                    nodelist.append(InlineNode('math', [TextNode(math)]))
                    math = ''
                    mathmode = False
                else:
                    math += r
            elif t == 'command':
                if len(v) == 1 and not v.isalpha():
                    nodelist.append(self.handle_special_command(v))
                    continue
                handler = getattr(self, 'handle_' + v, None)
                if not handler:
                    handler = self.handle_unrecognized(v, l)
                nodelist.append(handler())
            elif t == 'bgroup':
                bracelevel += 1
            elif t == 'egroup':
                if bracelevel == 0 and endatbrace:
                    return nodelist.flatten()
                bracelevel -= 1
            elif t == 'comment':
                nodelist.append(CommentNode(v))
            elif t == 'tilde':
                nodelist.append(NbspNode())
            elif t == 'ampersand':
                nodelist.append(AmpersandNode())
            elif t == 'mathmode':
                mathmode = True
            elif t == 'parasep':
                nodelist.append(ParaSepNode())
            else:
                # includes 'boptional' and 'eoptional' which don't have a
                # special meaning in text
                nodelist.append(TextNode(v))
        return nodelist.flatten()





    def parse_args_raw(self, cmdname ):
        """
    \\begin{longtable}{p{1.6in}llllp{2in}}
     "p{1.6in}llllp{2in}"

        """
        d = 0 
        raw = ""
        for l, t, v, r in self.tokens:
             raw += r 
             if t == "bgroup":d += 1
             if t == "egroup":d -= 1
             #print d,l,t,v,r
             if d == 0:break     
        assert raw[0] == "{" and raw[-1] == "}" 
        return [raw[1:-1]]

    def parse_args(self, cmdname, argspec):
        """ Helper to parse arguments of a command. """
        # argspec: M = mandatory, T = mandatory, check text-only,
        #          O = optional, Q = optional, check text-only
        args = []
        def optional_end(type, value, bracelevel):
            return type == 'eoptional' and bracelevel == 0

        for i, c in enumerate(argspec):
            assert c in 'OMTQ'
            nextl, nextt, nextv, nextr = self.tokens.pop()
            while nextt == 'comment' or (nextt == 'text' and nextv.isspace()):
                nextl, nextt, nextv, nextr = self.tokens.pop()

            if c in 'OQ':
                if nextt == 'boptional':
                    arg = self.parse_until(optional_end)
                    if c == 'Q' and not isinstance(arg, TextNode):
                        raise ParserError('%s: argument %d must be text only' %
                                          (cmdname, i), nextl)
                    args.append(arg)
                else:
                    # not given
                    args.append(EmptyNode())
                    self.tokens.push((nextl, nextt, nextv, nextr))
                continue

            if nextt == 'bgroup':
                arg = self.parse_until(None, endatbrace=True)
                if c == 'T' and not isinstance(arg, TextNode):
                    raise ParserError('%s: argument %d must be text only' %
                                      (cmdname, i), nextl)
                args.append(arg)
            else:
                if nextt != 'text':
                    raise ParserError('%s: non-grouped non-text arguments not '
                                      'supported' % cmdname, nextl)
                args.append(TextNode(nextv[0]))
                self.tokens.push((nextl, nextt, nextv[1:], nextr[1:]))
        return args

    sectioning_commands = [
        'chapter',
        'chapter*',
        'section',
        'subsection',
        'subsubsection',
        'paragraph',
    ]

    generic_commands = {
        CommandNode: {
            'label': 'T',

            'localmoduletable': '',
            'verbatiminput': 'T',
            'input': 'T',
            'caption': 'OM',
            'bibitem': 'OT',
            'fixme': 'M',
            'centerline': 'M',
            'centering': '',
            'par': '',
            'endhead': '',
            'includegraphics':'OM',
            'rowcolor':'OT',
            'rowcolors':'MMM',

            # Pydoc specific commands
            'versionadded': 'OT',
            'versionchanged': 'OT',
            'deprecated': 'TM',
            'XX' 'X': 'M',  # used in dist.tex ;)

            # module-specific
            'declaremodule': 'QTT',
            'platform': 'T',
            'modulesynopsis': 'M',
            'moduleauthor': 'TT',
            'sectionauthor': 'TT',

            # reference lists
            'seelink': 'TMM',
            'seemodule': 'QTM',
            'seepep': 'TMM',
            'seerfc': 'TTM',
            'seetext': 'M',
            'seetitle': 'OMM',
            'seeurl': 'MM',
        },

        DescLineCommandNode: {
            # additional items for ...desc
            'funcline': 'TM',
            'funclineni': 'TM',
            'methodline': 'QTM',
            'methodlineni': 'QTM',
            'memberline': 'QT',
            'memberlineni': 'QT',
            'dataline': 'T',
            'datalineni': 'T',
            'cfuncline': 'MTM',
            'cmemberline': 'TTT',
            'csimplemacroline': 'T',
            'ctypeline': 'QT',
            'cvarline': 'TT',
        },

        InlineNode: {
            # specials
            'cite': 'M',
            'footnote': 'M',
            'frac': 'TT',
            'refmodule': 'QT',
            'citetitle': 'QT',
            'ulink': 'MT',
            'url': 'T',

            'textwidth':'', 
            'textheight':'', 

            # mapped to normal
            'textrm': 'M',
            'b': 'M',
            'email': 'M', # email addresses are recognized by ReST

            # mapped to **strong**
            'textbf': 'M',
            'strong': 'M',

            # mapped to *emphasized*
            'textit': 'M',
            'emph': 'M',

            # mapped to ``code``
            'bfcode': 'M',
            'code': 'M',
            'samp': 'M',
            'character': 'M',
            'texttt': 'M',
            'code': 'M',

            # mapped to `default role`
            'var': 'M',

            # mapped to [brackets]
            'optional': 'M',

            # mapped to :role:`text`
            'cdata': 'M',
            'cfunction': 'M',      # -> :cfunc:
            'class': 'M',
            'command': 'M',
            'constant': 'M',       # -> :const:
            'csimplemacro': 'M',   # -> :cmacro:
            'ctype': 'M',
            'data': 'M',           # NEW
            'dfn': 'M',
            'envvar': 'M',
            'exception': 'M',      # -> :exc:
            'file': 'M',
            'filenq': 'M',
            'filevar': 'M',
            'function': 'M',       # -> :func:
            'grammartoken': 'M',   # -> :token:
            'guilabel': 'M',
            'kbd': 'M',
            'keyword': 'M',
            'mailheader': 'M',
            'makevar': 'M',
            'manpage': 'MM',
            'member': 'M',
            'menuselection': 'M',
            'method': 'M',         # -> :meth:
            'mimetype': 'M',
            'module': 'M',         # -> :mod:
            'newsgroup': 'M',
            'option': 'M',
            'pep': 'M',
            'program': 'M',
            'programopt': 'M',     # -> :option:
            'longprogramopt': 'M', # -> :option:
            'ref': 'T',
            'regexp': 'M',
            'rfc': 'M',
            'token': 'M',

            'NULL': '',
            # these are defined via substitutions
            'shortversion': '',
            'version': '',
            'today': '',
        },

        SimpleCmdNode: {
            # these are directly mapped to text
            'AA': '', # A as in Angstrom
            'ASCII': '',
            'C': '',
            'Cpp': '',
            'EOF': '',
            'LaTeX': '',
            'POSIX': '',
            'UNIX': '',
            'Unix': '',
            'backslash': '',
            'copyright': '',
            'e': '', # backslash
            'geq': '',
            'infinity': '',
            'ldots': '',
            'leq': '',
            'moreargs': '',
            'pi': '',
            'plusminus': '',
            'sub': '', # menu separator
            'textbackslash': '',
            'textunderscore': '',
            'texteuro': '',
            'textasciicircum': '',
            'textasciitilde': '',
            'textgreater': '',
            'textless': '',
            'textbar': '',
            'tilde': '',
            'unspecified': '',
        },

        IndexNode: {
            'bifuncindex': 'T',
            'exindex': 'T',
            'kwindex': 'T',
            'obindex': 'T',
            'opindex': 'T',
            'refmodindex': 'T',
            'refexmodindex': 'T',
            'refbimodindex': 'T',
            'refstmodindex': 'T',
            'stindex': 'T',
            'index': 'M',
            'indexii': 'TT',
            'indexiii': 'TTT',
            'indexiv': 'TTTT',
            'ttindex': 'T',
            'withsubitem': 'TM',
        },

        # These can be safely ignored
        EmptyNode: {
            'setindexsubitem': 'T',
            'tableofcontents': '',
            'makeindex': '',
            'makemodindex': '',
            'maketitle': '',
            'appendix': '',
            'documentclass': 'OM',
            'usepackage': 'OM',
            'noindent': '',
            'protect': '',
            'ifhtml': '',
            'fi': '',
            'pagebreak': '',
            'clearpage': '',
            'footnotesize': '',
            'normalsize': '',
            'huge': '',
            'hline': '',
        },
    }

    generic_envs = {
        EnvironmentNode: {
            # generic LaTeX environments
            'abstract': '',
            'quote': '',
            'quotation': '',
            'center':'',
            'em':'',
            'thebibliography':'T',

            'notice': 'Q',
            'seealso': '',
            'seealso*': '',
        },

        DescEnvironmentNode: {
            # information units
            'datadesc': 'T',
            'datadescni': 'T',
            'excclassdesc': 'TM',
            'excdesc': 'T',
            'funcdesc': 'TM',
            'funcdescni': 'TM',
            'classdesc': 'TM',
            'classdesc*': 'T',
            'memberdesc': 'QT',
            'memberdescni': 'QT',
            'methoddesc': 'QMM',
            'methoddescni': 'QMM',
            'opcodedesc': 'TT',

            'cfuncdesc': 'MTM',
            'cmemberdesc': 'TTT',
            'csimplemacrodesc': 'T',
            'ctypedesc': 'QT',
            'cvardesc': 'TT',
        },
    }

    # ------------------------- special handlers -----------------------------
    def handle_unrecognized(self, name, line):

        killers = ("em",)
        if name in killers:
            assert False , "killer command %s found at line %s " % ( name, line ) 
        def handler():
            self.unrecognized.add(name)
            return EmptyNode()
        return handler

    def handle_special_command(self, cmdname):
        if cmdname in '{}%$^#&_ ':
            # these are just escapes for special LaTeX commands
            return TextNode(cmdname)
        elif cmdname in '\'`~"c':
            # accents and umlauts
            nextl, nextt, nextv, nextr = self.tokens.next()
            if nextt == 'bgroup':
                _, nextt, _, _ = self.tokens.next()
                if nextt != 'egroup':
                    raise ParserError('wrong argtype for \\%s' % cmdname, nextl)
                return TextNode(cmdname)
            if nextt != 'text':
                # not nice, but {\~} = ~
                self.tokens.push((nextl, nextt, nextv, nextr))
                return TextNode(cmdname)
            c = umlaut(cmdname, nextv[0])
            self.tokens.push((nextl, nextt, nextv[1:], nextr[1:]))
            return TextNode(c)
        elif cmdname == '\\':
            return BreakNode()
        raise ParserError('no handler for \\%s command' % cmdname,
                          self.tokens.peek()[0])



    def handle_lstset(self):
        args = self.parse_args('\\lstset', 'M')   # need to parse the args to prevent them being spilled
        #print "handle_lstset %r " % args 
        return EmptyNode()

    def handle_begin(self):
        envname, = self.parse_args('begin', 'T')
        self.envname = envname.text
        handler = getattr(self, 'handle_%s_env' % envname.text, None)
        if not handler:
            raise ParserError('no handler for %s environment' % envname.text,
                              self.tokens.peek()[0])
        return handler()

    # ------------------------- command handlers -----------------------------

    def mk_metadata_handler(self, name, mdname=None):
        if mdname is None:
            mdname = name
        def handler(self):
            data, = self.parse_args('\\'+name, 'M')
            self.rootnode.params[mdname] = data
            return EmptyNode()
        return handler

    handle_title = mk_metadata_handler(None, 'title')
    handle_author = mk_metadata_handler(None, 'author')
    handle_authoraddress = mk_metadata_handler(None, 'authoraddress')
    handle_date = mk_metadata_handler(None, 'date')
    handle_release = mk_metadata_handler(None, 'release')
    handle_setshortversion = mk_metadata_handler(None, 'setshortversion',
                                                 'shortversion')
    handle_setreleaseinfo = mk_metadata_handler(None, 'setreleaseinfo',
                                                'releaseinfo')
    def handle_note(self):
        note = self.parse_args('\\note', 'M')[0]
        return EnvironmentNode('notice', [TextNode('note')], note)

    def handle_rstcontents(self):
        title = self.parse_args('\\rstcontents', 'M')[0]
        return TOCNode(title)


    def handle_warning(self):
        warning = self.parse_args('\\warning', 'M')[0]
        return EnvironmentNode('notice', [TextNode('warning')], warning)

    def handle_ifx(self):
        for l, t, v, r in self.tokens:
            if t == 'command' and v == 'fi':
                break
        return EmptyNode()

    def handle_c(self):
        return self.handle_special_command('c')

    def handle_mbox(self):
        return self.parse_args('\\mbox', 'M')[0]

    def handle_leftline(self):
        return self.parse_args('\\leftline', 'M')[0]

    def handle_Large(self):
        return self.parse_args('\\Large', 'M')[0]

    def handle_pytype(self):
        # \pytype{x} is synonymous to \class{x} now
        return self.handle_class()

    def handle_nodename(self):
        return self.handle_label()

    def handle_verb(self):
        # skip delimiter
        l, t, v, r = self.tokens.next()
        l, t, v, r = self.tokens.next()
        assert t == 'text'
        node = InlineNode('code', [TextNode(r)])
        # skip delimiter
        l, t, v, r = self.tokens.next()
        return node

    def handle_locallinewidth(self):
        return EmptyNode()

    def handle_linewidth(self):
        return EmptyNode()

    def handle_setlength(self):
        self.parse_args('\\setlength', 'MM')
        return EmptyNode()

    def handle_stmodindex(self):
        arg, = self.parse_args('\\stmodindex', 'T')
        return CommandNode('declaremodule', [EmptyNode(),
                                             TextNode(u'standard'),
                                             arg])

    def handle_indexname(self):
        return EmptyNode()

    def handle_renewcommand(self):
        self.parse_args('\\renewcommand', 'MM')
        return EmptyNode()

    # ------------------------- environment handlers -------------------------

    def handle_document_env(self):
        return self.parse_until(self.environment_end)

    handle_sloppypar_env = handle_document_env
    handle_flushleft_env = handle_document_env
    handle_longtable_env = handle_document_env
    handle_sideways_env = handle_document_env


    def handle_verbatim_env(self):
        text = []
        for l, t, v, r in self.tokens:
            if t == 'command' and v == 'end' :
                tok = self.tokens.peekmany(3)
                if tok[0][1] == 'bgroup' and \
                   tok[1][1] == 'text' and \
                   tok[1][2] == 'verbatim' and \
                   tok[2][1] == 'egroup':
                    self.tokens.popmany(3)
                    break
            text.append(r)
        #print "handle_verbatim_env %s " % repr(text)
        return VerbatimNode(TextNode(''.join(text)))

    def handle_rstverbatim_env(self):
        text = []
        for l, t, v, r in self.tokens:
            if t == 'command' and v == 'end' :
                tok = self.tokens.peekmany(3)
                if tok[0][1] == 'bgroup' and \
                   tok[1][1] == 'text' and \
                   tok[1][2] == 'rstverbatim' and \
                   tok[2][1] == 'egroup':
                    self.tokens.popmany(3)
                    break
            text.append(r)
        #print "handle_verbatim_env %s " % repr(text)
        return RstVerbatimNode(TextNode(''.join(text)))
   
    def handle_lstlisting_env(self):
        text = []
        args = self.parse_args('\\lstlisting', 'O')
        #print "args", args   

        for l, t, v, r in self.tokens:
            #print l,t,v,r
            if t == 'command' and v == 'end' :
                tok = self.tokens.peekmany(3)
                if tok[0][1] == 'bgroup' and \
                   tok[1][1] == 'text' and \
                   tok[1][2] == 'lstlisting' and \
                   tok[2][1] == 'egroup':
                    self.tokens.popmany(3)
                    break
            text.append(r)

        lstn = ListingNode(TextNode(''.join(text)), args )
        #print "lstn %s " % repr(lstn)
        return lstn

    # involved math markup must be corrected manually
    def handle_displaymath_env(self):
        envname = self.envname
        raw = "\\begin{%s}" % envname
        for l, t, v, r in self.tokens:
            #print l,t,v,r
            raw += r
            if t == 'command' and v == 'end' :
                 tok = self.tokens.popmany(3)
                 if tok[0][1] == 'bgroup' and \
                    tok[1][1] == 'text' and \
                    tok[2][1] == 'egroup':
                    endenv = tok[1][2]
                 else:
                    endenv = None
                 for _ in tok[2],tok[1],tok[0]:  ## huh need reverse order ... to avoid \end}array{ 
                    self.tokens.push(_)                   
            
                 if endenv == envname:
                     tok = self.tokens.popmany(3)
                     for _ in tok:
                         raw += _[3]
                     break 

        label_ptn = re.compile(r"\\label\{(\S*)\}") 
        label_m = label_ptn.search(raw)
        if label_m:
            label = label_m.group(1)
            #raw = label_ptn.sub("", raw)   ## remove the label from the raw ... avoid duplicate eqn labels 
        else:
            label = "dummy"

        txtl = NodeList(map(TextNode,raw.split("\\n")))
        return MathNode(txtl, raw=raw, label=label)
    handle_equation_env = handle_displaymath_env
    handle_eqnarray_env = handle_displaymath_env
    handle_math_env = handle_displaymath_env

    # alltt is different from verbatim because it allows markup
    def handle_alltt_env(self):
        nodelist = NodeList()
        for l, t, v, r in self.tokens:
            if self.environment_end(t, v):
                break
            if t == 'command':
                if len(v) == 1 and not v.isalpha():
                    nodelist.append(self.handle_special_command(v))
                    continue
                handler = getattr(self, 'handle_' + v, None)
                if not handler:
                    raise ParserError('no handler for \\%s command' % v, l)
                nodelist.append(handler())
            elif t == 'comment':
                nodelist.append(CommentNode(v))
            else:
                # all else is appended raw
                nodelist.append(TextNode(r))
        return VerbatimNode(nodelist.flatten())

    def handle_itemize_env(self, nodetype=ItemizeNode):
        items = []
        # a usecase for nonlocal :)
        running = [False]

        def item_condition(t, v, bracelevel):
            if self.environment_end(t, v):
                del running[:]
                return True
            if t == 'command' and v == 'item':
                return True
            return False

        # the text until the first \item is discarded
        self.parse_until(item_condition)
        while running:
            itemname, = self.parse_args('\\item', 'O')
            itemcontent = self.parse_until(item_condition)
            items.append([itemname, itemcontent])
        return nodetype(items)

    def handle_enumerate_env(self):
        return self.handle_itemize_env(EnumerateNode)

    def handle_description_env(self):
        return self.handle_itemize_env(DescriptionNode)

    def handle_definitions_env(self):
        items = []
        running = [False]

        def item_condition(t, v, bracelevel):
            if self.environment_end(t, v):
                del running[:]
                return True
            if t == 'command' and v == 'term':
                return True
            return False

        # the text until the first \item is discarded
        self.parse_until(item_condition)
        while running:
            itemname, = self.parse_args('\\term', 'M')
            itemcontent = self.parse_until(item_condition)
            items.append([itemname, itemcontent])
        return DefinitionsNode(items)

    def mk_table_handler(self, envname, numcols):
        def handle_table(self):
            args = self.parse_args('table'+envname, 'TT' + 'M'*numcols)
            firstcolformat = args[1].text
            headings = args[2:]
            lines = []
            for l, t, v, r in self.tokens:
                # XXX: everything outside of \linexxx is lost here
                if t == 'command':
                    if v == 'line'+envname:
                        lines.append(self.parse_args('\\line'+envname,
                                                     'M'*numcols))
                    elif v == 'end':
                        arg = self.parse_args('\\end', 'T')
                        assert arg[0].text.endswith('table'+envname), arg[0].text
                        break
            for line in lines:
                if not empty(line[0]):
                    line[0] = InlineNode(firstcolformat, [line[0]])
            return TableNode(numcols, headings, lines)
        return handle_table

    handle_tableii_env = mk_table_handler(None, 'ii', 2)
    handle_longtableii_env = handle_tableii_env
    handle_tableiii_env = mk_table_handler(None, 'iii', 3)
    handle_longtableiii_env = handle_tableiii_env
    handle_tableiv_env = mk_table_handler(None, 'iv', 4)
    handle_longtableiv_env = handle_tableiv_env
    handle_tablev_env = mk_table_handler(None, 'v', 5)
    handle_longtablev_env = handle_tablev_env


    def handle_tabular_env(self):
        envname = self.envname
        args = self.parse_args_raw(envname )
        #print "tabular %s args %r " % (envname , args )
        orig_colspec = args[0]
        colpatn = re.compile("({[^}]*})")   ##  "p{1.6in}llllp{2in}" -->   'pllllp'
        colspec = colpatn.sub("",orig_colspec)
        colspec = colspec.replace('|','')
        numcols = len(colspec)
        #print "handle_tabular_env numcols %s orig_colspec %s colspec %s " % ( numcols , orig_colspec, colspec  )
 
        all = []
        running = [False]

        def endrow_condition(t, v, bracelevel):
            #print "endrow t[%s] v[%s] b[%s] " % ( t, v, bracelevel )
            if self.environment_end(t, v):
                del running[:]
                return True
            if t == 'command' and v == "\\":
                return True
            return False

        while running:
            row = NodeList() 
            row.append( self.parse_until(endrow_condition) )
            row.append( AmpersandNode())

            #print "row %r " % row 

            cols = []
            elem = NodeList()            
            for c in row:
                if isinstance(c, AmpersandNode):
                    cols.append(elem)
                    elem = NodeList()
                else:
                    elem.append(c)

            #print "cols %r " % cols 
            if len(cols) == numcols: 
                all.append( cols )
            else:
                pass
                #print "tail skip ", ( repr(cols) , numcols, len(cols) )

        if len(all) > 0:
            headings = all[0]
            lines = all[1:]
            return TabularNode(numcols, headings, lines , colspec=orig_colspec)
        else:
            assert False, "handle_tabular_env failed to parse any table rows matching the column spec %s %s CHECK TABULAR COLS MATCH THE SPEC " % ( colspec, numcols )
            print "WARNING returning EMPTY"
            return EmptyNode()        

    handle_longtable_env = handle_tabular_env

    def handle_table_env(self): 
        args = self.parse_args('table', 'Q' )
        content = self.parse_until(self.environment_end)
        opts = {}
        opts['label'] = find_label( content )
        opts['caption_node'] = find_caption_node( content )
        tn = TableNode("table", [], content, opts=opts )
        #print "handle_table_env %r " % ( tn ) 
        return tn


    def handle_figure_env(self):
        args = self.parse_args('figure', 'Q')
        content = self.parse_until(self.environment_end)
        opts = {}
        opts['label'] = find_label( content )
        opts['listing'] = find_subnode( content, type=ListingNode )  ## a dummy figure as vehicle for a code listing
        for n in content:
            if isinstance(n, CommandNode) and n.cmdname == 'centering':
                opts['align'] = "center"
        fn = FigureNode("figure", args, content, opts=opts )
        #print "handle_figure_env %r %r " % (args, fn ) 
        return fn

    def handle_productionlist_env(self):
        env_args = self.parse_args('productionlist', 'Q')
        items = []
        for l, t, v, r in self.tokens:
            # XXX: everything outside of \production is lost here
            if t == 'command':
                if v == 'production':
                    items.append(self.parse_args('\\production', 'TM'))
                elif v == 'productioncont':
                    args = self.parse_args('\\productioncont', 'M')
                    args.insert(0, EmptyNode())
                    items.append(args)
                elif v == 'end':
                    arg = self.parse_args('\\end', 'T')
                    assert arg[0].text == 'productionlist'
                    break
        node = ProductionListNode(items)
        # the argument specifies a production group
        node.arg = env_args[0]
        return node

    def environment_end(self, t, v, bracelevel=0):
        if t == 'command' and v == 'end':
            self.parse_args('\\end', 'T')
            return True
        return False
