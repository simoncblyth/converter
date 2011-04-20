# -*- coding: utf-8 -*-
"""

    converter.sphinxext.tabledoc
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Based on the simplest sphinx directive: :py:mod:`sphinx.ext.ifconfig`

    Usage::

        .. tabledoc:: dcs SAB_TEMP 

    The arguments for ``tabledoc`` are a :file:`~/.my.cnf` section name
    identifying a DB server and database and connection credentials
    and a table name contained in the database

"""
import os
from docutils import nodes
from sphinx.util.compat import Directive
from converter.tabular import TabularData
from ConfigParser import SafeConfigParser as ConfigParser
import MySQLdb 
import MySQLdb.cursors

class tabledoc(nodes.Element): pass

class TableDoc(Directive):

    has_content = False
    required_arguments = 2
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        node = tabledoc()
        node.document = self.state.document
        node.line = self.lineno
        node['db_sect'] = self.arguments[0]
        node['db_table'] = self.arguments[1]
        self.state.nested_parse(self.content, self.content_offset,
                                node, match_titles=1)
        return [node]


class MyCnf(dict):
    """
    annoyingly needed due to mysql vs mysql-python configfile key incompatibility preventing
        con = MySQLdb.connect( read_default_group=node['db_sect'] )
    """ 
    def __init__(self, sect):
        cfp = ConfigParser()
        cfp.read(os.path.expanduser("~/.my.cnf"))
        self.update( dict( cfp.items(sect) ))

class MyDB(object):
    def __init__(self, cnf ):
        if type(cnf) == str:
            cnf = MyCnf(cnf)
        con = MySQLdb.connect( host=cnf['host'], db=cnf['database'], user=cnf['user'], passwd=cnf['password'], cursorclass=MySQLdb.cursors.DictCursor )
        cur = con.cursor() 
        self.con = con
        self.cur = cur
    def __call__(self, sql ):
        self.cur.execute(sql)
        return self.cur.fetchall()  
    def _tables(self):
         return map(lambda _:_.values()[0], self("show tables"))
    tables = property( _tables )



def describe( sect , table ):
    db = MyDB( sect )
    return [d for d in db("describe %s" % table)] 

def process_tabledoc_nodes(app, doctree, docname):

    for node in doctree.traverse(tabledoc):
        try:
            desc = describe( node['db_sect'], node['db_table'] )             
        except Exception, err:
            # handle exceptions in a clean fashion
            from traceback import format_exception_only
            msg = ''.join(format_exception_only(err.__class__, err))
            newnode = doctree.reporter.error('Exception occured in '
                                             'tabledoc: \n%s' %
                                             msg, base_node=node)
            node.replace_self(newnode)
        else:
            node.replace_self(node.children)


def setup(app):
    app.add_node(tabledoc)
    app.add_directive('tabledoc', TableDoc)
    app.connect('doctree-resolved', process_tabledoc_nodes)


if __name__=='__main__':

    db = MyDB('dcs')
    for t in db.tables:
        td = TabularData( db("describe %s" % t ))
        print td 

