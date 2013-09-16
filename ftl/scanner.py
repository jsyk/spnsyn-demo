from __future__ import print_function
from __future__ import unicode_literals
from __future__ import absolute_import

from sys import stderr
from re import match

# FIXME: this does not correctly handle IDs e.g. "notify" will be lexed as ('not', ), ('ID', 'ify')


class ScanLocation:
    def __init__(self, row, col, fname):
        self.row = row
        self.col = col
        self.fname = fname
    
    def __repr__(self):
        return '{0}:{1}:{2}'.format(self.fname, self.row, self.col)


def tokenize(str, fname = '<stdin>'):
    res = []
    keywords = [
            'record', 'union', 'enum',
            'when', 'array',
            'not', 'and', 'def', 'let',
            'is', 'or',
            'module', 'import', 'use'
        ]
    operators = [
            '>=', '<=', '/=', '=<', '=>', ':=',
            '=', '<', '>', '=', '(', ')', '{', '}', '[', ']', '|', ';', 
            '^', '+', '-', '*', '/', '.', ',', ':'
        ]
    
    colstart_slen = len(str)
    row = 1
    col = 1
    in_block_comment = False;       # /* */
    
    while str:
        if str[0] == "\n":
            # next line
            str = str[1:]
            row += 1
            col = 1
            colstart_slen = len(str)
            continue
        
        if str[0].isspace():
            # eat whitespace
            str = str[1:]
            continue

        col = colstart_slen - len(str) + 1
        
        if str[0:2] == '//':
            # line comment, eat to the end of the line
            eol = str.find("\n")
            if eol == -1:
                print >>stderr, 'At {0} in-line comment at the end of file.'.format(ScanLocation(row, col, fname))
                eol = len(str)
            str = str[eol:];      # do not remove \n
            continue
            
        # look for end of the block comment */
        if str[0:2] == '*/':
            if in_block_comment:
                # end
                in_block_comment = False
                str = str[2:];          # eat
                continue
            else:
                # error
                print >>stderr, 'At {0} not in a block comment.'.format(ScanLocation(row, col, fname))
                raise SystemExit(1); 
        
        # look for the start of the block comment
        if str[0:2] == '/*':
            if in_block_comment:
                # error
                print >>stderr, 'At {0} nesting a block comment.'.format(ScanLocation(row, col, fname))
                raise SystemExit(1)
            else:
                # start
                in_block_comment = True
                str = str[2:];          # eat
                continue
        
        if in_block_comment:
            # in comment, eat char
            str = str[1:]
            continue
        
        
        m = match('[0-9]+', str)
        if m:
            res.append(('NUMBER', ScanLocation(row, col, fname), int(m.group(0)), ))
            str = str[m.end(0):]
            continue

        is_op = False
        for op in operators:
            if str[0:len(op)] == op:
                res.append((op, ScanLocation(row, col, fname), ))
                str = str[len(op):]
                is_op = True
                break
        if is_op:
            continue
        
        m = match('[a-zA-Z_@]+', str)
        if m and (m.group(0) in keywords):
            res.append((m.group(0), ScanLocation(row, col, fname), ))
            str = str[m.end(0):]
            continue
        
        if m:
            res.append(('ID', ScanLocation(row, col, fname), m.group(0)))
            str = str[m.end(0):]
            continue

        print >>stderr, 'At {0} the scanner has not recognized: {1}'.format(ScanLocation(row, col, fname), str[:50])
        raise SystemExit(1)
        #res.append((str[0],))
        #str = str[1:]

    return res

