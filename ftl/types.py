from ftl.ast import *
from ftl.atrav import DefaultTrav, PrintTrav

True_Bool_t = '\'1\''
False_Bool_t = '\'0\''

# Bool_t = NAp('std_ulogic', [])
# Integer_t = NAp('integer', [])
Bool_t = 'std_ulogic'
Integer_t = 'integer'


def resolve_types(t1, t2):
    if t1 is None:
        return t2
    if t2 is None:
        return t1
    # FIXME: this is awfull :(
    ts1 = PrintTrav().run_on(t1)
    ts2 = PrintTrav().run_on(t2)
    assert ts1 == ts2, "Types '{0}' and '{1}' are not compatible!".format(ts1, ts2)
    return t1


class InferTypesTrav(DefaultTrav):
    """ Infer types of variable in the expression tree. """
    def trav_bool(self, nd):
        return Bool_t
    
    def trav_const(self, nd):
        # if nd.get_val() in [True, False]:
            # return self.trav_bool(nd)
        assert False, 'unknown const type of value {0}'.format(nd.get_val())

    def trav_int(self, nd):
        return Integer_t

    def trav_id(self, nd):
        return nd.get_ref().get_actype()
    
    def trav_prf_cond(self, nd):
        # NPrf(Prf.COND, [_cond_, NPrf(Prf.COLON, _alts_) ] )
        t1 = self.do_trav(nd.get_args()[0])
        resolve_types(t1, Bool_t)
        t2 = self.do_trav(nd.get_args()[1])
        return t2
    
    def trav_prf_ff(self, nd):
        # NPrf(Prf.FF, [_new_value_, _en_])
        t_en = self.do_trav(nd.get_args()[1])
        resolve_types(t_en, Bool_t)
        t_val = self.do_trav(nd.get_args()[0])
        return t_val
    
    def trav_prf_comma(self, nd):
        # hmm, each position can be different type
        return None

    def trav_prf_eq(self, nd):
        # the positions should be equal types, the result is bool
        t0 = self.do_trav(nd.get_args()[0])
        t1 = self.do_trav(nd.get_args()[1])
        resolve_types(t0, t1)
        return Bool_t

    def trav_prf_mpx(self, nd):
        # the first is integer, the other are the same
        t0 = self.do_trav(nd.get_args()[0])
        resolve_types(t0, Integer_t)
        tp = None
        for i in range(1, len(nd.get_args())):
            t = self.do_trav(nd.get_args()[i])
            tp = resolve_types(tp, t)
        return tp

    def trav_prf_getfld(self, nd):
        # the first is a value, the second is a field name; the third is an optional type of the result
        assert len(nd.args()) == 3
        return nd.args()[2]

    def trav_others_prf(self, nd):
        # by default, all elements should be of the same type
        # print('trav_others_prf: nd={0}'.format(nd.get_prf()))
        tp = None
        for i in range(0, len(nd.get_args())):
            t = self.do_trav(nd.get_args()[i])
            tp = resolve_types(tp, t)
        return tp

    def trav_ap(self, nd):
        # hmm, each parameter position can be of different type,
        # and the function is user-defined
        return None

    def trav_prf_swisel(self, nd):
        # @@swisel(NConst(Element), int, NId(wand), NId(wand), ...)
        tp = None
        for i in range(2, len(nd.get_args())):
            t = self.do_trav(nd.get_args()[i])
            tp = resolve_types(tp, t)
        return tp

