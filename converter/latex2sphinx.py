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
    def get(self, a, b=None):
        print "ir %s " % a 
        if os.path.exists(a+'.rst'):
            return a + '.rst'
        return None
restwriter.includes_mapping = IncludeRewrite()




def _convert_file(inf, outf, doraise=True, splitchap=False,
                 toctree=None, deflang=None, labelprefix=''):
    p = DocParser(Tokenizer(inf.read()).tokenize(), inf)
    r = RestWriter(outf, splitchap, toctree, deflang, labelprefix)
    r.write_document(p.parse())
    #outf.close()
    p.finish()  # print warnings about unrecognized commands


class Inputs(list):
    in_patn = re.compile(r"^\\input{(.*)}")
    def __call__(self, note=""):
        return "(%-3d) %-10s " % ( len(self), note ) + "+".join(self)

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
        if path:
            for line in open(path, "r").readlines():
                m = self.in_patn.match(line)
                if m:
                    inpf = m.group(1)
                    if inpf not in _inputs:
                        _inputs.append(inpf)
        else:
            print "failed to resolve %s " % name
        return _inputs    
    
    def walk_(self, base):
        """
             Recursively find all input documents, returning for 
             each a list of its ancestry. Ordering is arranged to return 
             children before their parents.
        """
        for name in sorted(self.list_inputs(base)):
            self.append(name)   
            for x in self.walk_(name):
                yield x
            yield self
            self.pop()

    
def convert_doctree( base , dry_run=False  ):
    inp = Inputs()
    for i in inp.walk_(base):
        tex = inp.resolve(i[-1])
        if not tex.endswith('.tex'):continue
        rst = tex[:-4]+'.rst'
        print "convert %s to %s " % ( tex, rst )
        if dry_run:continue
        tex = open(tex,"r")
        rst = open(rst,"w")
        _convert_file( tex , rst )
        tex.close()
        rst.close()
        

if __name__=='__main__':
    base = sys.argv[1] 
    convert_doctree(base) 
