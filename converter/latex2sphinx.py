import os, sys, re
from converter import DocParser, Tokenizer, RestWriter 
from converter import restwriter


class envvars(list):
    """ workaround as jinja2 departs from django in dict iteration """
    def __init__(self, prefix ):
        for k,v in os.environ.items():
            if k.startswith(prefix):
                self.append(dict(key=k,val=v)) 
   
def _convert_file(inf, outf, doraise=True, splitchap=False,
                 toctree=None, deflang=None, labelprefix='', fakechapter=None, fakesection=None, extlinks={}, verbose=False, dry_run=False ):
    """
         *fakechapter* and *fakesection* preprend the chapter or section definition to 
         the content read from the source latex file, allowing the converted reST to 
         incorporate the chapter/section title without needing to change the latex source 
 
    """
    content = inf.read()
    if fakechapter:
        content = "\chapter{%s}\n" % fakechapter + content 
    if fakesection:
        content = "\section{%s}\n" % fakesection + content 

    p = DocParser(Tokenizer(content).tokenize(), inf, extlinks=extlinks)
    r = RestWriter(outf, splitchap, toctree, deflang, labelprefix)
    r.write_document(p.parse())
    if p.unrecognized:
        outf.write(".. warning:: latexparser did not recognize : " + " ".join(p.unrecognized))
    return p.unrecognized




class Matcher(list):
    se_patn = re.compile(r"^\\section{(.*)}")
    ch_patn = re.compile(r"^\\chapter{(.*)}")
    in_patn = re.compile(r"^\\input{(.*)}")

    def resolve(self, name):
        if os.path.exists(name):
           return name
        elif os.path.exists(name+'.tex'): 
           return name+'.tex'
        else:
           return None 

class INode(Matcher):
    INDEX_BASENAME = 'index'
    def __init__(self, name , parent=None, chap=None, sect=None ):
        self.name = name 
        self.parent = parent
        self.sect = sect
        self.chap = chap
        self.depth = ( 0 if parent == None else self.parent.depth + 1 )

        path = self.resolve(name)
        self.curchap = None
        self.cursect = None
        self.parse(path) 
        self.path = path
        self.unrec = None

    def _root(self):
        return self if not self.parent else self.parent._root()
    root = property(_root)

    def parse_line(self, line):
        c = self.ch_patn.match(line)
        if c:
            chap = c.group(1)
            self.curchap = chap
        s = self.se_patn.match(line)
        if s:
            sect = s.group(1)
            self.cursect = sect

        i = self.in_patn.match(line)
        if i:
            inam = i.group(1) 
            child = INode(inam, parent=self, chap=self.curchap,sect=self.cursect ) 
            self.append(child)

    def parse(self, path):    
        for line in open(path, "r").readlines():
            self.parse_line(line)

    def _fold(self):
        ele = self.sname.split("/")
        return "/".join(ele[:-1]) if len(ele)>0 else ""
    fold = property(_fold)

    is_index = property(lambda self:len(self)>0)
    
    def _basename(self):
        """ nodes with children have basename index ... CLOBBER POTENTIAL   """
        ele = self.sname.split("/")
        return self.INDEX_BASENAME if self.is_index else ele[-1]
    basename = property(_basename)

    def _drv(self):
        fold = self.fold
        return "%s/%s" % ( fold, self.basename ) if fold != "" else self.basename 
    drv = property(_drv)

    unrecs = property(lambda self:" ".join(self.unrec))
    sname = property(lambda self:self.name[:-4] if self.name.endswith(".tex") else self.name)
    pname = property(lambda self:self.parent.name if self.parent else None)
    heading = property(lambda self:self.sect or self.chap)
    tex = property(lambda self:self.sname + ".tex" )
    rst = property(lambda self:self.drv + ".rst" )

    def tex2rst(self, **kwa ):
        if kwa.get('verbose',None):
            print "tex2rst %r " % self  

        envvars = kwa.get('envvars',[])
        kwa.update( fakechapter=self.chap , fakesection=self.sect )

        if not self.is_index: 
            unrec = convert_doc( self.tex , self.rst, **kwa ) 
            self.unrec = unrec
        else:
            tmpl = "%s.tmpl" % self.rst 
            if os.path.exists(tmpl):
                idx = self.idx_from_template( tmpl , envvars=envvars )
            else:
                idx = self.idx()

            rst = open( self.rst,"w")
            rst.write( idx )
            rst.close()

        if kwa.get('recurse',None):
            for _ in self:
                _.tex2rst(**kwa)

    def _ctx(self):
        return dict(root=self.root, node=self )
    ctx = property(_ctx)

    def idx_from_template(self, tmpl, **kwa ):
        from jinja2 import FileSystemLoader, Environment
        env = Environment(loader=FileSystemLoader(os.path.dirname(tmpl)))
        template = env.get_template(os.path.basename(tmpl))
        ctx = self.ctx
        ctx.update( **kwa )
        return template.render( ctx )

    def __repr__(self):
        return "%s<INode [%d,%d] %s (%s;%s) \"%s\"  >" % ( "   " * self.depth, len(self), self.depth , self.name , self.fold, self.basename , self.heading ) 

    def title( self, t ):
        if not t:return ""
        bar = "*" * len(t)
        return "\n".join( [bar,t,bar] ) + "\n"
    def tocline( self, child ):
        return "   %s </%s>" % ( child.heading , child.sname )  
    def toctree( self ):
        return ".. toctree::\n\n" + "\n".join([ self.tocline(_) for _ in self ]) + "\n"
    def comment( self , t ):
        return ".. % " + t + "\n" 
    def idx( self ):
        return "\n".join([self.comment(self.sname),self.title( self.heading ),self.toctree()])
    def _ancestors(self):
        """ think directory traversal to understand this """
        for _ in self:
            if len(_):
                for __ in _._ancestors():
                    yield __
            else:
                yield _
    ancestors = property(_ancestors)



def convert_doc( tex , rst=None, **kwa ):
    if not rst:
        rst = tex[:-4]+'.rst'
    tex = open(tex,"r")
    rst = open(rst,"w")
    kwa.pop('recurse')
    kwa.pop('dry_run')
    unrec = _convert_file( tex , rst , **kwa )
    rst.close()
    return unrec

def convert_doctree( base , dry_run=False, extlinks={} , verbose=False, envvars=[] ):
    root = INode(base)
    print "convert_doctree from %r " % root
    print "primaries... "
    predicate = lambda _:1
    #predicate = lambda _:_.is_index
    for pri in filter(predicate,root):
        pri.tex2rst(recurse=True,dry_run=dry_run,extlinks=extlinks,verbose=verbose) 
    print "root... "  ## last to facilitate error reporting
    root.tex2rst(recurse=False,verbose=verbose,envvars=envvars)

 
from nose.tools import make_decorator
def CNV(dummy=True):
    def _decorate(func):
        def _wrapper(*args, **kargs):
            unrec = convert_tex(func.__doc__, **kargs)
            assert len(unrec) == 0
        _wrapper = make_decorator(func)(_wrapper)
        return _wrapper
    return _decorate


from cStringIO import StringIO
def convert_tex( tex ):
    return  _convert_file( StringIO(tex) , sys.stdout )


if __name__=='__main__':
    base = sys.argv[1] 
    convert_doctree(base) 
