# -*- coding: utf-8 -*-
"""

    converter.sphinxext.tabledoc
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Based on the simplest sphinx directive: :py:mod:`sphinx.ext.ifconfig`
    and http://sphinx.pocoo.org/ext/tutorial.html#the-directive-classes

    Usage::

        .. tabledoc:: dcs SAB_TEMP 

    The arguments for ``tabledoc`` are a :file:`~/.my.cnf` section name
    identifying a DB server and database and connection credentials
    and a table name contained in the database

"""
import os
from docutils import nodes
from sphinx.util.compat import Directive
from docutils.statemachine import ViewList

from converter.tabular import TabularData
from ConfigParser import SafeConfigParser as ConfigParser

import MySQLdb 
import MySQLdb.cursors

 
class MySQLDocumenter(object):
    def __init__(self, directive, arguments , indent=u''):
        self.directive = directive
        self.arguments = arguments
        self.indent = indent
    def add_line(self, line, source, *lineno):
        """Append one line of generated reST to the output."""
        self.directive.result.append(self.indent + line, source, *lineno)

    def generate(self):
        sect, table = self.arguments                
        db = MyDB(sect)
        desc = db.table_description(table)
        for line in str(desc).split("\n"): 
            self.add_line( self.indent + line , "mysql tabledoc for %s" % table , 0 )


class TableDoc(Directive):
    """
    Follow autodoc pattern
    """
    has_content = False
    required_arguments = 2
    optional_arguments = 0
    final_argument_whitespace = True
    option_spec = {}

    def run(self):
        # generate the output
        self.result = ViewList()  
        documenter = MySQLDocumenter(self, self.arguments )
        documenter.generate()

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)
        return node.children


class MyCnf(dict):
    def __init__(self, sect):
        cfp = ConfigParser()
        cfp.read(os.path.expanduser("~/.my.cnf"))
        self.update( dict( cfp.items(sect) ))

class MyDB(object):
    def __init__(self, sect ):
        cnf = MyCnf(str(sect))
        print cnf
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

    def table_description(self, t ):
        return TabularData( self("describe %s" % t ))


def setup(app):
    app.add_directive('tabledoc', TableDoc)


if __name__=='__main__':
    db = MyDB('dcs')
    for t in db.tables:
        print db.table_description(t) 

