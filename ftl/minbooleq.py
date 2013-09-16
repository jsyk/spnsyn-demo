from ftl.ast import *
from ftl.atrav import DefaultTrav, ComputeHashesTrav
from ftl.atrav_eq import HoistTrav, ReplaceVariableTrav, GatherUsedVarsTrav, SimplifyExprTrav

from subprocess import Popen, PIPE


class MinBoolEq:
    def __init__(self, use_espresso = True):
        self.ivars = []
        # truth table: list of lines. Each line is a list
        # of ivars's values, then the output (should be True)
        self.tt = []
        self.use_espresso = use_espresso
    

    def run_on(self, nd):
        ComputeHashesTrav().run_on(nd)
        h_nd, h_vars = HoistTrav().run_on(nd, prf_to_hoist=set([Prf.EQ, Prf.MPX]), recurse=False)
        self.make_tt(h_nd)
        mh_nd = self.from_tt_to_eqd()
        
        # now, minimize the h_vars also...
        # new_hvars = dict()
        for hv in h_vars:
            hv_eqd = hv.get_eqdef()
            if hv_eqd.get_prf() != Prf.MPX:
                # new_hvars[hv] = hv_eqd
                continue
            # over the args of the MPX/EQ Prf
            n_hv_args = [hv_eqd.get_args()[0]]
            for k in range(1, len(hv_eqd.get_args())):
                n_hva = MinBoolEq().run_on( hv_eqd.get_args()[k] )
                n_hv_args.append(n_hva)
            
            hv.replace_eqdef( NPrf(hv_eqd.get_prf(), n_hv_args) )
            h_vars[hv] = hv.get_eqdef()
            # new_hvars[hv] = 

        m_nd = ReplaceVariableTrav().run_on(mh_nd, h_vars)
        return m_nd
    
    def _is_p0(self, s):
        lines = s.split("\n")
        for L in lines:
            if L == ".p 0":
                #print "is_p0 True"
                return True
        return False
    
    def to_eqn_str(self, eqd, eqname):
        # input variables, in the order they appear in the table
        self.ivars = list(GatherUsedVarsTrav().run_on(eqd))
        # check that all ivars are booleans
        for v in self.ivars:
            if v.get_actype() != Bool_t:
                raise NameError('variable %s is not bool' % (v.get_name()))
        #eqstr = self.get_eqnstr(atc.get_eqdef())
        eqstr = ConstructEqnStrTrav().run_on(eqd)
        iv_str = [iv.get_name() for iv in self.ivars]
        res = ''
        if len(iv_str) > 0:
            res += "INORDER = %s;\n" % (" ".join(iv_str))
        res += eqname + ' = ' + eqstr + ";\n"
        return res
    
    
    def make_tt(self, eqd, eqname = '__result'):
        if type(eqd) == bool:
            # special: having the bool alone makes espresso unhappy
            if not eqd:
                # it is False, the table is empty
                self.tt = []
                return self
        #if (type(atc.get_eqdef()) != bool) and (type(atc.get_eqdef()) != tuple):
            ## a variable alone makes espresso unhappy
            #self.tt = [ ['1'], ['1'] ]
            #return self
        
        # the following may raise an exception if the expression is
        # not palatable for eqntott because of unsupported operators
        estr = self.to_eqn_str(eqd, eqname)
        
        p1 = Popen(['eqntott'], stdin=PIPE, stdout=PIPE)
        #print 'make_tt: input=%s' % (estr)
        stdoutdata1, stderrdata1 = p1.communicate(estr.encode('utf-8'))
        stdoutdata1 = stdoutdata1.decode('utf-8')
        stdoutdata1 = ".type f\n" + stdoutdata1
        #print 'make_tt: output1=%s' % stdoutdata1
        if self.use_espresso and not self._is_p0(stdoutdata1):
            # _is_p0: checks that there is non-zero number of equtions in the stdoutdata1
            # otherwise espresso will be unhappy
            p2 = Popen(['espresso'], stdin=PIPE, stdout=PIPE)
            stdoutdata2, stderrdata2 = p2.communicate(stdoutdata1.encode('utf-8'))
            stdoutdata2 = stdoutdata2.decode('utf-8')
        else:
            stdoutdata2, stderrdata2 = stdoutdata1, None
        # print error
        if stderrdata1 is not None:
            print( 'errors from eqntott: %s' % stderrdata1.decode('utf-8'))
        if stderrdata2 is not None:
            print( 'errors from espresso: %s' % stderrdata2.decode('utf-8'))
        # convert to table
        #print 'make_tt: output2=%s' % stdoutdata2
        self.from_str_to_tt(stdoutdata2)
        return self
        
    def from_str_to_tt(self, s):
        lines = s.split("\n")
        self.tt = []
        for L in lines:
            if len(L) == 0 or L[0] == '.' or L[0] == '#':
                continue
            tl = []
            for ch in L:
                if ch == '0' or ch == '1':
                    tl.append(ch)
                if (ch == '-') or (ch == 'X'):
                    tl.append('-')
                
            self.tt.append(tl)
            #print tl
        return self
    
    def from_tt_to_eqd(self):
        # eqd = ('|', False)
        or_args = [False]
        for tl in self.tt:
            term_args = []
            assert tl[-1] == '1', 'tl=%s' % str(tl)
            for k in range(0, len(self.ivars)):
                if tl[k] == '1':
                    term_args.append(NId(self.ivars[k]))
                if tl[k] == '0':
                    term_args.append(NPrf(Prf.NOT, [NId(self.ivars[k])]))
            term = NPrf(Prf.AND, term_args)
            or_args.append(term)
        return NPrf(Prf.OR, or_args)


# #####################################################################################
class ConstructEqnStrTrav(DefaultTrav):
    """ Construct string out of the expression tree, suitable for eqntott
        and espresso programs.
    """
    eqn_ops = { Prf.OR : '|', Prf.AND : '&' }

    def run_on(self, nd):
        # auxiliary bool vars after subexpression extr.
        # self.hoisted_ex = []            # subexpr:node
        # used variables, after hoisting
        # self.ivars = set()
        return self.do_trav(nd)

    def trav_bool(self, eqd):
        if eqd:
            return '1'
        else:
            return '0'
    
    def trav_const(self, eqd):
        # if eqd.get_val() in [True, False]:
        #     return self.trav_bool(eqd.get_val())
        raise NameError('unsupported const for eqntott "{0}"'.format(eqd.get_val()))

    def trav_ap(self, nd):
        raise NameError('unsupported ap for eqntott "{0}"'.format(eqd.get_val()))

    def trav_prf_not(self, nd):
        # assert nd[0] == '!'
        return '(!' + self.do_trav(nd.get_args()[0]) + ')'
    
    # def trav_prf_eq(self, nd):
    #     # the comparison cannot be printed for eqntott/espresso, hoist.
    #     s = '__{0}'.format(len(self.hoisted_ex))
    #     self.hoisted_ex.append(nd)
    #     return s

    def trav_others_prf(self, nd):
        # check the operator: only & and | can be directly
        # transleted into eqntott string
        # if nd.get_prf() == Prf.NOT:
        #     return self.trav_prf_not(nd)

        if nd.get_prf() in [Prf.OR, Prf.AND]:
            oper = self.eqn_ops[nd.get_prf()]

            res = '('
            for i in range(0, len(nd.get_args())):    # skip first
                if (i > 0):
                    res += oper
                res += self.do_trav(nd.get_args()[i])
            return res + ')'
        else:
            # unsupported operator
            raise NameError('unsupported operator for eqntott "{0}"'.format(nd.get_prf()))
    
    def trav_id(self, nd):
        return nd.get_ref().get_name()


# #####################################################################################
class MinimizeExprTrav(DefaultTrav):
    """ Minimize the expression using esspresso. """

    def run_on(self, eqd):
        self.num_minim = 0
        return self.do_trav(eqd)

    def trav_prf(self, nd):
        # me = MinBoolEq().make_tt(eqd)
        try:
            # try to minimize the whole expression eqd
            me = MinBoolEq().run_on(nd)
        except NameError:
            # cannot be minimized en-block, dive in
            nargs = self.do_trav(nd.get_args())
            # neqd = (eqd[0], )
            # nargs = []
            # for i in range(0, len(nd.get_args())):
            #     # neqd += (self.do_trav(eqd[i]), )
            #     nargs.append(self.do_trav(nd.get_args()[i]))
            nnd = NPrf(nd.get_prf(), nargs)
            return nnd
        else:
            # minimization worked!
            new_eqd = SimplifyExprTrav().run_on(me)
            self.num_minim += 1
            return new_eqd

    def trav_ap(self, nd):
        # cannot minimize an ap()
        return nd
