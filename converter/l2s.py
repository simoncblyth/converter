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

 



class Inputs(Matcher):
    def __call__(self, note=""):
        return "(%-3d) %-10s " % ( len(self), note ) + "+".join(self)

    def __init__(self, *args):
        super(self.__class__,self).__init__(*args)
        self.skeleton = {}

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
        chap = None
        sect = None
        inpf = None
        _inputs = []
 
        path = self.resolve(name)
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
                        inode = Inpf(name=inpf,chap=chap,sect=sect,parent=name)
                        self.skeleton[path].append(inode)
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







    inp = Inputs()
    toc = []

    unrecognized = []
    for i,ch,se in inp.walk_(base):
        #print i 
        tex = inp.resolve(i[-1])
        assert tex, "convert_doctree failed to resolve input %r " % i
        if not tex.endswith('.tex'):continue

        toc.append(tex[:-4])
        print "converting %s   ch %s se %s " % ( tex, ch, se )
        if dry_run:continue

        unrec = convert_doc( tex , extlinks=extlinks , fakechapter=ch, fakesection=se ) 
        for _ in unrec:
            if _ not in unrecognized:
                unrecognized.append( _ )

    if verbose:
        print "skeleton structure of the doctree, non-leaf nodes "
        for k,v in inp.skeleton.items():
            if len(v)>0:
                #print repr(v)
                print index(k,v)
                 
        #print "incorporate the below into the toctree ... "
        #print "\n".join(["   %s" % _ for _ in toc])   

        print "unrecognized commands : "  + " ".join(["   " + _ for _ in unrecognized]) 



