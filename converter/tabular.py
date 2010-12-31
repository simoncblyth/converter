
from .restwriter import RestWriter
from .docnodes import TabularNode, RootNode, NodeList, TextNode
from cStringIO import StringIO

class TabularData(list):
   """
       A simple way to create a reStructuredText table string 
       from a list of dicts 
   """
   def __init__(self):
       super(self.__class__,self).__init__() 

   def append_(self, **kwa):
       self.append(kwa)
       
   def rows(self, cols ):
       data = []
       for d in self: 
           row = [ TextNode(str(d[k])) for k in cols ]
           data.append(row)
       return data

   def _headings(self):
       keys = []
       for _ in self:
          for k in _.keys():
              if k not in keys:keys.append(k)
       return keys 
   headings = property(_headings)

   def as_node(self, cols=None):
       cols = cols if cols else self.headings
       rows = self.rows(cols)
       cols = map(TextNode,cols) 
       return TabularNode( len(cols), cols, rows ) 

   def as_rst(self, cols=None):
       tn = self.as_node(cols)
       nl = NodeList( [tn] )
       rn = RootNode("tabulardata",nl)

       st = StringIO()
       rw = RestWriter(st)
       rw.write_document( rn )
       return st.getvalue()

   def __str__(self):
       return self.as_rst()



if __name__ == '__main__':

   td = TabularData()
   td.append( {"color":"red",   "number":1 }) 
   td.append( {"color":"green", "number":2 }) 
   td.append( {"color":"blue",  "number":3 }) 
   td.append(color="cyan",number=4 ) 
   print td
   print repr(td)



