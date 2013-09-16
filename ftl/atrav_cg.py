from ftl.ast import *
from ftl.atrav import DefaultTrav
import ftl.types as types


class PrintAsVhdlTrav(DefaultTrav):
    """ Print the tree as a VHDL code. This can also print types. """
    op_str = {Prf.AND:' and ', Prf.OR:' or ', Prf.NOT:'not ', Prf.COMMA:', ',
            Prf.EQ:'=' }
    
    def trav_bool(self, eqd):
        if eqd:
            return types.True_Bool_t
        else:
            return types.False_Bool_t
    
    # def trav_str(self, eqd):
    #     return eqd
    
    def trav_int(self, eqd):
        return str(eqd)

    def trav_const(self, eqd):
        # if eqd.get_val() in [True, False]:
            # return self.trav_bool(eqd)
        return str(eqd.get_val())

    def trav_id(self, eqd):
        return eqd.get_ref().get_name()
    
    def trav_prf_not(self, eqd):
        return 'not ' + self.do_trav(eqd.get_args()[0])
    
    def trav_prf_colon(self, nd):
        # this returns a LIST of values
        return self.do_trav(nd.get_args())

    def trav_prf_cond(self, nd):
        eqd = nd.get_args()
        # assert type(eqd[2]) == tuple
        # assert eqd[2][0] == ':'
        # assert len(eqd[2]) == 3
        cond = eqd[0]
        whens = self.do_trav(eqd[1])
        assert len(whens) == 2
        when_true = whens[0]
        when_false = whens[1]
        r = ' {0} when to_bool({1}) else {2} '.format(when_true, self.do_trav(cond), when_false)
        return r

    # def trav_prf_mpx(self, nd):
    #     args = nd.get_args()
    #     cond = args[0]
    #     whens = self.do_trav(args[1])
    #     assert len(whens) == 2
    #     when_true = whens[0]
    #     when_false = whens[1]
    #     r = ' {0} when to_bool({1}) else {2} '.format(when_true, self.do_trav(cond), when_false)
    #     return r

    def trav_prf_downto(self, nd):
        # if eqd[1] == 'downto':
            # args = eqd[2]
        args = nd.get_args()
        return self.do_trav(args[0]) + ' downto ' + self.do_trav(args[1])
        # assert False, 'Unexpected prf "%s" when printing VHDL.' % (eqd[1])

    def trav_prf_nofo(self, nd):
        # skip
        return self.do_trav(nd.args()[0])

    def trav_prf_getfld(self, nd):
        return self.do_trav(nd.args()[0]) + '.' + nd.args()[1]

    def trav_others_prf(self, nd):
        op = self.op_str[nd.get_prf()]
        r = ''
        for i in range(0, len(nd.get_args())):    # skip first
            if len(r) > 0:
                r += op
            r += self.do_trav(nd.get_args()[i])
        return '(' + r + ')'
    
    def trav_ap(self, nd):
        r = ''
        a = nd.get_args()
        for i in range(0, len(a)):    # skip first
            if len(r) > 0:
                r += ', '
            r += self.do_trav(a[i])
        return self.do_trav(nd.get_fun()) + '(' + r + ')'
        # return str(nd.get_fun()) + '(' + r + ')'

    def trav_type(self, eqd):
        r = eqd[1]
        if len(eqd) > 2:
            r += self.do_trav(eqd[2])
        return r


class ZeroConstTypeTrav(PrintAsVhdlTrav):
    """ Traverses type definition and constructs the constant zero expression
        for the type in VHDL. """
    def trav_prf_downto(self, nd):
        args = nd.get_args()
        return '{0}, {1}'.format(self.do_trav(args[0]), self.do_trav(args[1]))
