from ftl.ast import *
import ftl.names as names


class ATraversal:
    def run_on(self, nd):
        return self.do_trav(nd)
        # try:
        #     return self.do_trav(nd)
        # except AssertionError as e:
        #     try:
        #         nd_s = PrintTrav().run_on(nd)
        #     except:
        #         # reraise the original exception
        #         raise e
        #     # ok, give an explanation
        #     raise AssertionError('{0}\nin run_on: nd={1}'.format(str(e), nd_s))
    

    def do_trav(self, nd):
        # nd (node) must be one of:
        # - object subclass of Node
        # - list
        # - set
        if nd is None:
            return self.trav_none(nd)
        if isinstance(nd, Node):
            return self.trav_node(nd)
        if type(nd) == list:
            return self.trav_list(nd)
        if type(nd) == tuple:
            return self.trav_tuple(nd)
        if type(nd) == set:
            return self.trav_set(nd)
        if type(nd) == bool:
            return self.trav_bool(nd)
        if type(nd) == int:
            return self.trav_int(nd)
        if type(nd) == str:
            return self.trav_str(nd)
        assert False, 'don\'t know how to traverse an instance of {0}.\nValue= {1}'.format(type(nd), str(nd))
    
    def trav_none(self, nd):
        return nd
    
    def trav_list(self, nd):
        assert type(nd) == list
        rlst = []
        for k in nd:
            q = self.do_trav(k)
            if q is not None:
                rlst.append(q)
        return rlst
    
    def trav_tuple(self, nd):
        assert type(nd) == tuple
        rlst = []
        for k in nd:
            q = self.do_trav(k)
            if q is not None:
                rlst.append(q)
        return tuple(rlst)

    def trav_set(self, nd):
        assert type(nd) == set
        rset = set([])
        for k in nd:
            q = self.do_trav(k)
            if q is not None:
                rset.insert(q)
        return rset
    
    def trav_str(self, nd):         # hmm
        return nd

    def trav_node(self, nd):
        assert isinstance(nd, Node)
        # class name, remove leading 'N', lowercase
        cnm = nd.__class__.__name__.lstrip('N').lower()
        # find method with the appropriate name
        tr = getattr(self, 'trav_{0}'.format(cnm))
        # call it
        return tr(nd)

    def trav_bool(self, nd):
        return nd
    
    def trav_int(self, nd):
        return nd


class DefaultTrav(ATraversal):
    """ Default traversal methods, traverses all sons. """
    
    # def trav_pipeline(self, nd):
    #     nd.items = self.do_trav(nd.items)
    #     nd.action = self.do_trav(nd.action)
    #     return nd
    
    # def trav_cluster(self, nd):
    #     nd.pipelines = self.do_trav(nd.pipelines)
    #     return nd
    
    # def trav_piperef(self, nd):
    #     return nd
    
    # def trav_fragap(self, nd):
    #     return nd
    
    # def trav_ap(self, nd):
    #     return self.do_trav(nd.get_args())
    #     # nd.set_args(self.do_trav(nd.get_args()))
    #     # return nd
    
    def trav_prf(self, nd):
        mn = 'trav_prf_{0}'.format(nd.get_prf())
        if hasattr(self, mn):
            tr = getattr(self, mn)
            return tr(nd)
        else:
            return self.trav_others_prf(nd)

    # def trav_others_prf(self, nd):
    #     # by default traverse all arguments of the prf node
    #     return self.do_trav(nd.get_args())
    #     # nd.set_args(self.do_trav(nd.get_args()))
    #     # return nd

    def trav_others_prf(self, nd):
        return NPrf(nd.get_prf(), self.do_trav(nd.get_args()))

    def trav_ap(self, nd):
        return NAp(nd.get_fun(), self.do_trav(nd.get_args()))

    # def trav_attrcore(self, nd):
    #     # normally do not traverse into attrcore eqdef
    #     return nd

    # def trav_id(self, nd):
    #     return nd
    
    def trav_const(self, nd):
        return nd

    def trav_id(self, nd):
        return nd
    
    # def trav_update(self, nd):
    #     nd.action = self.do_trav(nd.action)
    #     return nd
    
    # def trav_defattr(self, nd):
    #     nd.action = self.do_trav(nd.action)
    #     return nd
    
    
    
    
class APrintTrav(ATraversal):
    INSTR = '  '
    
    def run_on(self, nd):
        self.indent = 0
        return self.do_trav(nd)
    
    def trav_none(self, nd):
        return [self.INSTR*self.indent + '<None>']
    
    def trav_list(self, nd):
        assert type(nd) == list
        rlst = []
        for k in nd:
            q = self.do_trav(k)
            if q is not None:
                rlst.extend(q)
        return rlst
    
    def trav_pipeline(self, nd):
        sl = [self.INSTR*self.indent + 'NPipeline']
        self.indent += 2
        sl.append(self.INSTR*(self.indent-1) + '.action = ')
        sl.extend(self.do_trav(nd.get_action()))
        sl.append(self.INSTR*(self.indent-1) + '.items = [')
        sl.extend(self.do_trav(nd.get_plineitems()))
        sl.append(self.INSTR*(self.indent-1) + ']')
        self.indent -= 2
        return sl
    
    def trav_cluster(self, nd):
        sl = [self.INSTR*self.indent + 'NCluster']
        self.indent += 2
        sl.append(self.INSTR*(self.indent-1) + '.pipelines = [')
        sl.extend(self.do_trav(nd.get_pplines()))
        sl.append(self.INSTR*(self.indent-1) + ']')
        self.indent -= 2
        return sl
    
    #def trav_piperef(self, nd):
        #sl = [self.INSTR*self.indent + 'NPipeRef: .name="{0}", .loc={1}'.format(nd.get_name(), nd.get_loc())]
        #self.indent += 2
        #sl.append(self.INSTR*(self.indent-1) + '.implicit_in = {0}'.format(nd.f_implicit_in))
        #sl.append(self.INSTR*(self.indent-1) + '.implicit_out = {0}'.format(nd.f_implicit_out))
        #self.indent -= 2
        #return sl
    
    #def trav_fragap(self, nd):
        #sl = [self.INSTR*self.indent + 'NFragAp']
        #self.indent += 2
        #sl.append(self.INSTR*(self.indent-1) + '.frag = {0}'.format(nd.get_frag()))
        #self.indent -= 2
        #return sl
    
    def trav_ap(self, nd):
        sl = [self.INSTR*self.indent + 'NAp: .fun = {0}'.format(nd.get_fun())]
        self.indent += 2
        #sl.append(self.INSTR*(self.indent-1) + '.fun = {0}'.format(nd.get_fun()))
        sl.append(self.INSTR*(self.indent-1) + '.args = [')
        sl.extend(self.do_trav(nd.get_args()))
        sl.append(self.INSTR*(self.indent-1) + ']')
        self.indent -= 2
        return sl
    
    def trav_prf(self, nd):
        sl = [self.INSTR*self.indent + 'NPrf: .prf = {0}'.format(nd.get_prf())]
        self.indent += 2
        #sl.append(self.INSTR*(self.indent-1) + '.prf = {0}'.format(nd.get_prf()))
        sl.append(self.INSTR*(self.indent-1) + '.args = [')
        sl.extend(self.do_trav(nd.get_args()))
        sl.append(self.INSTR*(self.indent-1) + ']')
        self.indent -= 2
        return sl
    
    def trav_id(self, nd):
        sl = [self.INSTR*self.indent + 'NId: .name="{0}"'.format(nd.get_name())]
        return sl
    
    def trav_const(self, nd):
        sl = [self.INSTR*self.indent + 'NConst: .val="{0}"'.format(nd.get_val())]
        return sl
    
    #def trav_update(self, nd):
        #sl = [self.INSTR*self.indent + 'NUpdate']
        #self.indent += 2
        #sl.append(self.INSTR*(self.indent-1) + '.action = [')
        #sl.extend(self.do_trav(nd.get_action()))
        #sl.append(self.INSTR*(self.indent-1) + ']')
        #self.indent -= 2
        #return sl
    
    #def trav_defattr(self, nd):
        #sl = [self.INSTR*self.indent + 'NDefAttr: .name="{0}"'.format(nd.get_name())]
        #self.indent += 2
        #sl.append(self.INSTR*(self.indent-1) + '.action = [')
        #sl.extend(self.do_trav(nd.get_action()))
        #sl.append(self.INSTR*(self.indent-1) + ']')
        #self.indent -= 2
        #return sl
    
    def trav_module(self, nd):
        sl = [self.INSTR*self.indent + 'NModule: ']
        self.indent += 2
        #sl.append(self.INSTR*(self.indent-1) + '.prf = {0}'.format(nd.get_prf()))
        sl.append(self.INSTR*(self.indent-1) + '.defs = [')
        sl.extend(self.do_trav(nd.get_defs()))
        sl.append(self.INSTR*(self.indent-1) + ']')
        self.indent -= 2
        return sl
    
    
    def trav_def(self, nd):
        sl = [self.INSTR*self.indent + 'NDef: .name = {0}'.format(nd.get_name().get_str())]
        self.indent += 2
        #sl.append(self.INSTR*(self.indent-1) + '.prf = {0}'.format(nd.get_prf()))
        #sl.append(self.INSTR*(self.indent-1) + '.defs = [')
        #sl.extend(self.do_trav(nd.get_defs()))
        #sl.append(self.INSTR*(self.indent-1) + ']')
        self.indent -= 2
        return sl
    

class PrintTrav(DefaultTrav):
    """ Pretty-print the expression.
        Recursively builds a list of primitive strings, then joins it at the end (should be fastest).
    """
    #op_str = {'&':' and ', '|':' or ', '!':'not ' }
    op_str = {Prf.AND:' & ', Prf.OR:' | ', Prf.NOT:'!', Prf.COND:' ? ', Prf.COMMA:', ', 
            '@@':'@@', Prf.COLON:' : ', '@':'@', Prf.FF: '@@ff', Prf.EQ: '=',
            Prf.GETFLD:'.', Prf.DOWNTO:' @@downto ', Prf.SWISEL:'@@swisel' }
    
    def run_on(self, nd):
        r = self.do_trav(nd)
        return ''.join(r)

    def trav_none(self, nd):
        return ['!NONE!']

    def trav_bool(self, nd):
        return [str(nd)]
    
    def trav_int(self, nd):
        return [str(nd)]

    def trav_const(self, nd):
        return [str(nd.get_val())]

    def trav_id(self, nd):
        return [nd.get_ref().get_name()]

    def trav_list(self, nd):
        r = ['list']
        r.extend( self.generic_trav_n_ary(', ', nd) )
        # r.append(']')
        return r
    
    # def trav_unary(self, eqd):
    #     return self.op_str[eqd[0]] + self.do_trav(eqd[1])
    #     #return self.op_str[eqd[0]] + '(' + self.do_trav(eqd[1]) + ')'
    #     assert False
    
    def generic_trav_n_ary(self, op, eqd):
        # op = self.op_str[eqd[0]]
        r = ['(']
        for i in range(0, len(eqd)):    # skip first
            if i > 0:
                r.append(op)
            r.extend(self.do_trav(eqd[i]))
            if len(r) > 1024*4:
                return ''.join(r) + ' ...string too long...)'
        r.append(')')
        return r
    
    def trav_others_prf(self, nd):
        if nd.get_prf() in [Prf.OR, Prf.AND, Prf.COND, Prf.COMMA, Prf.COLON, Prf.EQ, Prf.DOWNTO]:
            return self.generic_trav_n_ary(self.op_str[nd.get_prf()], nd.get_args())

        if nd.get_prf() == Prf.NOT:
            r = ['!']
            r.extend( self.do_trav(nd.get_args()[0]) )
            return r

        if nd.get_prf() in [Prf.FF, Prf.MPX, Prf.ZERO_CONST_TP, Prf.NOFOLLOW, Prf.GETFLD, Prf.SWISEL]:
            r = ['@@', str(nd.get_prf()), '(']
            ar = nd.get_args()
            for i in range(0, len(ar)):
                if i > 0:
                    r.append(', ')
                r.extend(self.do_trav(ar[i]))
            r.append(')')
            return r

        assert False, 'Unknown prf: {0}'.format(nd.get_prf())

    # def trav_prf_downto(self, nd):
    #     args = nd.get_args()
    #     r = []
    #     r.extend(self.do_trav(args[0]))
    #     r.append(' @@downto ')
    #     r.extend(self.do_trav(args[1]))
    #     return r

    def trav_ap(self, nd):
        # r = ['@', str(nd.get_fun()), '(']
        r = ['@']
        r.extend(self.do_trav(nd.get_fun()))
        r.append('(')
        ar = nd.get_args()
        for i in range(0, len(ar)):    # skip first
            if i > 0:
                r.append(', ')
            r.extend(self.do_trav(ar[i]))
        r.append(')')
        return r


class ConvStdLogicTrav(DefaultTrav):
    """ Convert Prf.EQ to produce std_ulogic. """
    def trav_prf_eq(self, nd):
        return NAp('to_stdulogic', [nd])


class ComputeHashesTrav(DefaultTrav):
    """ Compute hashes and rewrite them in the nodes. """
    def trav_id(self, nd):
        # hash of a node is the reference it stores
        nd.set_hash(id(nd.get_ref()))
        return nd.get_hash()

    def trav_str(self, nd):         # hmm
        return hash(nd)

    def hash_args(self, args):
        # hash arguments
        arg_hashes = self.do_trav(args)
        # combine
        h = 0
        for ah in arg_hashes:
            h = h ^ ah
        return h

    def trav_prf(self, nd):
        # FIXME HACK!!!
        if nd.get_prf() == Prf.GETFLD:
            h = self.hash_args(nd.args()[0:2])     # skip type info tuple at args()[2]
        else:
            h = self.hash_args(nd.args())
        # hash the prf type
        h = (h << 3) ^ hash('@@'+nd.get_prf())
        nd.set_hash(h)
        return nd.get_hash()

    def trav_ap(self, nd):
        h = self.hash_args(nd.get_args())
        # hash the prf type
        h = (h << 3) ^ hash(nd.get_fun())
        nd.set_hash(h)
        return nd.get_hash()


class CompareTrav(DefaultTrav):
    """ Compare two trees (nd1, nd2).
        Requires hashes to be up-to-date.
    """
    def run_on(self, nd1, nd2):
        self.nd2 = nd2
        return self.do_trav(nd1)

    def trav_id(self, nd):
        if isinstance(self.nd2, NId):
            return self.nd2.get_ref() == nd.get_ref()
        else:
            return False

    def trav_bool(self, nd):
        if isinstance(self.nd2, bool):
            return self.nd2 == nd
        else:
            return False

    def trav_int(self, nd):
        if isinstance(self.nd2, int):
            return self.nd2 == nd
        else:
            return False

    def myhash(x):
        if isinstance(x, Node):
            return x.get_hash()
        else:
            return hash(x)

    def match_args(self, nd, commut):
        if len(nd.get_args()) != len(self.nd2.get_args()):
            return False
        nd2 = self.nd2
        if commut:
            # sort according to the hash
            args1 = sorted(nd.get_args(), key=CompareTrav.myhash)   #lambda x: x.get_hash()
            args2 = sorted(nd2.get_args(), key=CompareTrav.myhash)
        else:
            args1 = nd.get_args()
            args2 = nd2.get_args()
        # iterate over ther (sorted) argument lists
        for k in range(0, len(args1)):
            a1 = args1[k]
            a2 = args2[k]
            self.nd2 = a2
            if not self.do_trav(a1):
                return False
        self.nd2 = nd2
        return True

    # def match_args_inorder(self, nd):
    #     if len(nd.get_args()) != len(self.nd2.get_args()):
    #         return False
    #     nd2 = self.nd2
    #     for k in range(0, len(nd.get_args())):
    #         a1 = nd.get_args()[k]
    #         a2 = nd2.get_args()[k]
    #         self.nd2 = a2
    #         if not self.do_trav(a1):
    #             return False
    #     self.nd2 = nd2
    #     return True

    def trav_others_prf(self, nd):
        if not isinstance(self.nd2, NPrf):
            return False
        if nd.get_hash() != self.nd2.get_hash():
            return False
        # both are NPrf, and the hashes are identical
        if (nd.get_prf() != self.nd2.get_prf()):
            return False
        # prf type matches; compare args
        return self.match_args(nd, nd.is_commutative())

    def trav_ap(self, nd):
        if not isinstance(self.nd2, NAp):
            return False
        if nd.get_hash() != self.nd2.get_hash():
            return False
        # both are NAp, and the hashes are identical
        if (nd.get_fun() != self.nd2.get_fun()):
            return False
        # prf type matches; compare args
        return self.match_args(nd, False)

