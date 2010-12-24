import os, sys, re
#import codecs
from converter import DocParser, Tokenizer, RestWriter 
from converter import restwriter

class IncludeRewrite:
    """
          rewriting dict access 

          directory depth issues with inclusions into docs in subdirs 
          such as database/database_tables.{tex,rst}
          due to different relative path behavior           

             latex 
                   \input{../../../Database/DybDbi/genDbi/GCalibFeeSpec}

                  inputs into an input document still use paths from the "main"
                  ... ie broken relative behaviour

             and reStructuredText  (extra ../ needed) 
                   .. include:: ../../../../Database/DybDbi/genDbi/GCalibPmtSpec.rst

                  The directive argument is the path to the file to be included, 
                  relative to the document containing the directive.
                     http://docutils.sourceforge.net/docs/ref/rst/directives.html#id45  


    """

    def resolve(self, name, default=None):
        if name.endswith('.tex'):
            name = name[:-4]
        if os.path.exists( name ):
            return name
        elif os.path.exists( name + '.rst' ):
            return name + '.rst'
        else:
            return default

    def get(self, a, b=None):

        path = self.resolve(a,b)
        if path:
            return '../' + path
        else:
            print "ir : failed to resolve %s " % a 
        return None
restwriter.includes_mapping = IncludeRewrite()

    

def _convert_file(inf, outf, doraise=True, splitchap=False,
                 toctree=None, deflang=None, labelprefix='', fakechapter=None, fakesection=None ):
    
    content = inf.read()
    if fakechapter:
        content = "\chapter{%s}\n" % fakechapter + content 
    if fakesection:
        content = "\section{%s}\n" % fakesection + content 

    p = DocParser(Tokenizer(content).tokenize(), inf)
    r = RestWriter(outf, splitchap, toctree, deflang, labelprefix)
    r.write_document(p.parse())
    #outf.close()
    #p.finish()  # print warnings about unrecognized commands
    if p.unrecognized:
        outf.write(".. warning:: latexparser did not recognize : " + " ".join(p.unrecognized))
    return p.unrecognized


class Inputs(list):
    se_patn = re.compile(r"^\\section{(.*)}")
    ch_patn = re.compile(r"^\\chapter{(.*)}")
    in_patn = re.compile(r"^\\input{(.*)}")
    def __call__(self, note=""):
        return "(%-3d) %-10s " % ( len(self), note ) + "+".join(self)

    def __init__(self, *args):
        super(self.__class__,self).__init__(*args)
        self.skeleton = {}

    def resolve(self, name):
        if os.path.exists(name):
           return name
        elif os.path.exists(name+'.tex'): 
           return name+'.tex'
        else:
           return None 

    def list_inputs(self, name):
        """
           Return a list of all latex input command arguments
           parsed from name, 
           eg for a file containing :
              \input{name1} 
              \input{name2}
              \input{name2.tex}

           A list ['name1','name2','name2.tex'] is returned 
 
        """
        _inputs = []
        path = self.resolve(name)
        chap = None
        sect = None
        self.skeleton[path] = []
        if path:
            for line in open(path, "r").readlines():
                c = self.ch_patn.match(line)
                if c:
                    chap = c.group(1)

                s = self.se_patn.match(line)
                if s:
                    sect = s.group(1)

                i = self.in_patn.match(line)
                if i:
                    inpf = i.group(1)
                    if inpf not in _inputs:
                        _inputs.append((inpf, chap, sect,))
                        self.skeleton[path].append(inpf)
        else:
            print "failed to resolve %s " % name
        return _inputs    
    
    def walk_(self, base):
        """
             Recursively find all input documents, returning for 
             each a list of its ancestry. Ordering is arranged to return 
             children before their parents.
        """
        inps = self.list_inputs(base)

        for name, chap, sect in inps:
            self.append(name)   
            for _ in self.walk_(name):
                yield _
            yield self, chap, sect
            self.pop()

    
def convert_doctree( base , dry_run=False  ):
    inp = Inputs()
    toc = []


    unrecognized = []
    for i,ch,se in inp.walk_(base):
        #print i 
        tex = inp.resolve(i[-1])
        if not tex.endswith('.tex'):continue

        rst = tex[:-4]+'.rst'
        toc.append(rst[:-4])
        
        print "convert %s to %s  ch %s se %s " % ( tex, rst, ch, se )
        if dry_run:continue

        tex = open(tex,"r")
        rst = open(rst,"w")
        unrec = _convert_file( tex , rst , fakechapter=ch )
        for _ in unrec:
            if _ not in unrecognized:
                unrecognized.append( _ )
        rst.close()
"""
    print "skeleton structure of the doctree, non-leaf nodes "
    for k,v in inp.skeleton.items():
        if len(v)>0:
            print k, repr(v)

    print "incorporate the below into the toctree ... "
    print "\n".join(["   %s" % _ for _ in toc])   

    print "unrecognized commands : " 
    print "\n".join(["   " + _ for _ in unrecognized]) 
"""

if __name__=='__main__':
    base = sys.argv[1] 
    convert_doctree(base) 
