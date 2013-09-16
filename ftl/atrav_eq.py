from ftl.ast import *
from ftl.atrav import DefaultTrav, PrintTrav

class SimplifyExprTrav(DefaultTrav):
    """ Simplify an expression by applying a set of trivial transformations.
        Basically, we just do constant folding from bottom up.
        The traversal preserves DNF.
    """
    def trav_prf_not(self, eqd):
        assert eqd.get_prf() == Prf.NOT
        eqd1 = self.do_trav(eqd.get_args()[0])
        if eqd1 == True:
            return False
        if eqd1 == False:
            return True
        # if isinstance(eqd1, NConst):
        #     if eqd1.get_val() == True:
        #         return NConst(False, eqd1.get_loc())
        #     else:
        #         if eqd1.get_val() == False:
        #             return NConst(True, eqd1.get_loc())
        if isinstance(eqd1, NPrf) and eqd1.get_prf() == Prf.NOT:
            # two negations, skip the two levels
            return eqd1.get_args()[0]
        else:
            # REPACK
            return NPrf(Prf.NOT, [eqd1], loc=eqd.get_loc())
            # eqd.get_args()[0] = eqd1
            # return eqd

    
    def simpl_variadic(self, args):
        """ Traverse (simplify) the sub-trees in args[0..n].
            Count the number of Falses and Trues in the resulting list.
        """
        ns_args = []
        num_false = 0
        num_true = 0
        for i in range(0, len(args)):
            v = self.do_trav(args[i])
            if v == False:
                num_false += 1
            else:
                if v == True:
                    num_true += 1
                else:
                    ns_args.append(v)
        return (ns_args, num_false, num_true)
    
    def level_prf_args(self, prf, args):
        """ Try to level a nested prf of the same kind, eg.
            (a & b) & c  =>>  a & b & c
        """
        n_args = []
        for a in args:
            if a.get_prf() == prf:
                # the prfs are identical, skip the level
                n_args.extend(a.get_args())
            else:
                n_args.append(a)
        return n_args

    def trav_prf_and(self, eqd):
        """ Traverses the & operator.
        """
        ns_eqd, num_false, num_true = self.simpl_variadic(eqd.get_args())
        
        if (num_false > 0):
            # any false in &
            return False
        if (num_true == len(eqd.get_args())):
            # all true in &
            return True
        
        if len(ns_eqd) == 1:
            # only one component
            return ns_eqd[0]
        else:
            # REPACK
            return NPrf(eqd.get_prf(),
                self.level_prf_args(eqd.get_prf(), ns_eqd) )
            # return (eqd[0],) + tuple(ns_eqd)
        
    def trav_prf_or(self, eqd):
        """ Traverses the | operator.
        """
        ns_eqd, num_false, num_true = self.simpl_variadic(eqd.get_args())
        
        if (num_true > 0):
            # any true in |
            return True
        if (num_false == len(eqd.get_args())):
            # all false in |
            return False
        
        if len(ns_eqd) == 1:
            # only one component
            return ns_eqd[0]
        else:
            # REPACK
            return NPrf(eqd.get_prf(),
                self.level_prf_args(eqd.get_prf(), ns_eqd) )
            # return (eqd[0],) + tuple(ns_eqd)

    def trav_prf_cond(self, nd):
        # NPrf(Prf.COND, [_cond_, NPrf(Prf.COLON, _alts_) ] )
        assert len(nd.get_args()) == 2
        assert nd.get_args()[1].get_prf() == Prf.COLON
        assert len(nd.get_args()[1].get_args()) == 2

        cnd = self.do_trav(nd.get_args()[0])
        if_true = nd.get_args()[1].get_args()[0]
        if_false = nd.get_args()[1].get_args()[1]

        if cnd == True:
            return self.do_trav(if_true)
        else:
            if cnd == False:
                return self.do_trav(if_false)
            else:
                return NPrf(Prf.COND, [cnd,
                    self.do_trav(nd.get_args()[1])])
        # return NPrf(nd.get_prf(), self.do_trav(nd.get_args()))


class SimplifyWithSubstTrav(SimplifyExprTrav):
    """ Simplify the expression while substituing variables for other
        expressions according to dict 'substs'.
        Unknown but defined vars are travered into their eq_defs!
        If keep_intermed is True, then also remember (cache) intermediate
        values when traversing to other eq_defs.
    """
    def run_on(self, eqd, substs, keep_intermed=True):
        self.substs = substs
        self.keep_intermed = keep_intermed
        self.visiting = []      # stack of eqs being visited in the call graph. Prevents infinite recursion.
        return self.do_trav(eqd)

    def trav_id(self, eqd):
        rf = eqd.get_ref()
        if rf in self.substs:
            return self.substs[rf]
        else:
            if rf.get_eqdef() is not None:
                # dive in
                # print('SimplifyWithSubstTrav: into {0}'.format(str(eqd.get_ref())))
                if rf.get_eqdef() in self.visiting:
                    # the node is being visited in the call graph; visiting it again would
                    # trigger infinite recursion.
                    return eqd
                self.visiting.append(rf.get_eqdef())
                v = self.do_trav(rf.get_eqdef())
                xx = self.visiting.pop()
                assert xx == rf.get_eqdef()
                if self.keep_intermed:
                    self.substs[rf] = v
                return v
            else:
                return eqd


class GatherUnsubstPhisTrav(DefaultTrav):
    """ Find PHI prfs, create an aux variable and replace the prfs
        with the variables.
        phis_map is dict() from (v1, v2) to v3,
        v3 := phi(v1, v2)
    """
    def run_on(self, eqd, phis_map):
        self.phis_map = phis_map
        return self.do_trav(eqd)

    def trav_prf_phi(self, nd):
        # the arguments to the prf should be two NId's
        assert len(nd.get_args()) == 2

        v1 = nd.get_args()[0].get_ref()
        v2 = nd.get_args()[1].get_ref()
        k = (v1, v2)
        if k in self.phis_map:
            return NId(self.phis_map[k])
        else:
            # this phi kind never seen before, create a new variable
            # and add it into the phis_map dict
            nm = 'phi_{0}_{1}'.format(str(v1), str(v2))
            a = Attrib(nm, Bool_t, ackind=AttrKind.Other)
            a.get_core().set_allow_subst(False)
            self.phis_map[k] = a.get_core()
            return NId(a.get_core())


class GatherUsedVarsTrav(DefaultTrav):
    """ Retrieves the set of variables used in the expression tree.
    """
    def run_on(self, nd, inner=True, leaf=False):
        self.add_inner = inner
        self.add_leaf = leaf
        return self.do_trav(nd)

    def trav_bool(self, eqd):
        return set([])
    
    def trav_int(self, eqd):
        return set([])

    def trav_const(self, eqd):
        return set([])

    def trav_str(self, eqd):
        return set([])

    def generic_trav_args(self, args):
        used = set([])
        for i in range(0, len(args)):
            used |= self.do_trav(args[i])
        return used
    
    def trav_id(self, eqd):
        if self.add_inner:
            # add the referenced id to the set.
            r = set([eqd.get_ref()])
        else:
            r = set()
        if self.add_leaf:
            if eqd.get_ref().get_eqdef() is not None and eqd.get_ref().is_subst_allowed():
                # print('GatherUsedVarsTrav: into {0}'.format(str(eqd.get_ref())))
                r |= self.do_trav(eqd.get_ref().get_eqdef())
            else:
                r |= set([eqd.get_ref()])
        return r
    
    def trav_ap(self, nd):
        if nd.get_fun():
            f = self.do_trav(nd.get_fun())
        else:
            f = set([])
        return f | self.generic_trav_args(nd.get_args())
        # return (self.do_trav(nd.get_args()))
    
    def trav_others_prf(self, nd):
        # skip the function name
        return self.generic_trav_args(nd.get_args())
        # return (self.do_trav(nd.get_args()))

    def trav_prf_getfld(self, nd):
        # only the value
        return self.do_trav(nd.args()[0])


class GatherDepVars_NoFF_Trav(GatherUsedVarsTrav):
    """ Retrieves the set of variables that the expression depends on,
        BUT NOT ACROSS THE FF AND NOFOLLOW PRF."""

    def trav_prf_ff(self, nd):
        # do not traverse ff
        return set([])

    def trav_prf_nofo(self, nd):
        # do not traverse nofo
        return set([])



class MarkNecessaryVarsTrav(GatherUsedVarsTrav):
    """ Mark all the used variables as necessary, and
        recursively mark also their trees. """
    def trav_id(self, eqd):
        if not eqd.get_ref().is_necessary():
            # so far not encoutered; mark it
            eqd.get_ref().mark_as_necessary()
            # traverse recursively
            if eqd.get_ref().get_eqdef() is not None:
                # print('traversing into {0}'.format(eqd.get_ref()))
                r = self.do_trav(eqd.get_ref().get_eqdef())
                assert r is not None, 'got None from {0} := {1}'.format(
                    eqd.get_ref().get_name(),
                    PrintTrav().run_on(eqd.get_ref().get_eqdef()))
                return set([eqd.get_ref()]) | r
        return set([eqd.get_ref()])


class AbsorpLawTrav(DefaultTrav):
    """ Distributive law:
        a & (... a ...)     ->  a & (... True ...)
        !a & (... a ...)    ->  !a & (... False ...)
        a | (... a ...)     ->  a | (... False ...)
        !a | (... a ...)    ->  !a | (... True ...)
    """
    def run_on(self, nd, bmap=dict()):
        # a map of vars bound to a value
        self.bound_map = bmap     # dict: attrcore -> bool
        self.count_elims = 0
        return self.do_trav(nd)

    def trav_prf_and(self, nd):
        return self.distribute(nd, False)

    def trav_prf_or(self, nd):
        return self.distribute(nd, True)

    def trav_prf_not(self, nd):
        # optimization: try to propagate constants
        assert len(nd.get_args()) == 1
        nd2 = self.do_trav(nd.get_args()[0])
        if isinstance(nd2, bool):
            return not nd2
        else:
            return NPrf(Prf.NOT, [nd2])

    def distribute(self, nd, DOMINATING):
        NEUTRAL = not DOMINATING
        parent_bmap = self.bound_map     # store parent bound_map
        self.bound_map = dict(self.bound_map)   # a new local copy
        vr_args = []    # NId, Not(Nid)
        oth_args = []   # other
        for ar in nd.get_args():
            if isinstance(ar, NId):
                # traverse the Id, get the new argument (nar)
                nar = self.do_trav(ar)
                # three possibilities for nar:
                # 1. bool
                # 2. NId
                # 3. other
                if isinstance(nar, bool):
                    if nar == DOMINATING:
                        # False in AND, True in OR
                        self.bound_map = parent_bmap
                        return DOMINATING
                    # otherwise devour the NEUTRAL value.
                    continue # with next argument
                if isinstance(nar, NId):
                    # a new variable: the next finds behave like neutral values
                    # with respect to the *this* AND/OR
                    vr_args.append(nar)
                    self.bound_map[nar.get_ref()] = NEUTRAL
                    continue # with next argument
                # some other expr after all
                oth_args.append(nar)
                continue # with next argument

            if isinstance(ar, NPrf) and ar.get_prf()==Prf.NOT and isinstance(ar.get_args()[0], NId):
                # ar1, nar are within NOT, hence the logic is negated
                ar1 = ar.get_args()[0]      # NId in Not
                nar = self.do_trav(ar1)
                # three possibilities for nar:
                # 1. bool
                # 2. NId
                # 3. other
                if isinstance(nar, bool):
                    if (not nar) == DOMINATING:  # nar is NEUTRAL
                        # after the negation: False in AND, True in OR
                        self.bound_map = parent_bmap
                        return DOMINATING  # skipping the Not level
                    # otherwise devour the not DOMINATING == NEUTRAL value.
                    continue # with next argument
                if isinstance(nar, NId):
                    # a new variable: the next finds behave like neutral values
                    # with respect to the *this* AND/OR
                    vr_args.append(NPrf(Prf.NOT, [nar]))
                    self.bound_map[nar.get_ref()] = not NEUTRAL    # == DOMINATING
                    continue # with next argument
                # some other expr after all
                oth_args.append(NPrf(Prf.NOT, [nar]))
                continue # with next argument
                
            # something other
            oth_args.append(ar)

        # traverse other args, using the new bound_map 
        for ar in oth_args:
            n_ar = self.do_trav(ar)
            if isinstance(n_ar, bool):
                if n_ar == DOMINATING:
                    # False in AND, True in OR
                    self.bound_map = parent_bmap
                    return DOMINATING
                else:
                    # True in AND, False in OR: do nothing
                    pass
            else:
                # general non-const expr
                vr_args.append(n_ar)
        # n_oth_args = self.do_trav(oth_args)
        # restore old bound_map
        self.bound_map = parent_bmap
        if len(vr_args) == 0:
            # no argument to AND/OR -> there must have been a DOMINATING arg. which
            # we have optimized out.
            return NEUTRAL
        else:
            if len(vr_args) == 1:
                # skip one level of Prf
                return vr_args[0]
            else:
                # general case
                return NPrf(nd.get_prf(), vr_args)
        
    def trav_id(self, nd):
        if nd.get_ref() in self.bound_map:
            val = self.bound_map[nd.get_ref()]
            self.count_elims += 1
            return val
        else:
            return nd


# class SubstTrav(DefaultTrav):
class SubstTrav(AbsorpLawTrav):
    """ Substitute variables by their definitions, unless the variable
        is an input (all_undefs) or a singularity (used).
        Uses AbsorpLawTrav to directly optimize usesless refferences.
    """
    def run_on(self, eqd, all_undefs, used=set(), bmap=dict()):
        #print '{starting on %s, used=%s}' % (str(eqd), used)
        self.used = used
        self.all_undefs = all_undefs
        self.count_substs = 0
        self.bound_map = bmap   # in the distributive law
        self.count_elims = 0
        return self.do_trav(eqd)
    
    def trav_id(self, nd):
        # known to the distributive law?
        if nd.get_ref() in self.bound_map:
            val = self.bound_map[nd.get_ref()]
            self.count_elims += 1
            return val
        # perform substitution
        ac = nd.get_ref()
        if ac in self.used:
            # substitution already performed, hence a cycle we have.
            return nd
        else:
            if (ac not in self.all_undefs) and (ac.is_subst_allowed()):
                lower = SubstTrav()
                #print '{subst %s -> %s}' % (nd.get_name(), str(nd.get_eqdef()))
                nnd = lower.run_on(ac.get_eqdef(), self.all_undefs, 
                        used=self.used | set([ac]),
                        bmap=dict(self.bound_map))
                #print '{subst %s done}' % (nd.get_name())
                self.count_substs += lower.count_substs + 1
                self.count_elims += lower.count_elims
                return nnd
            else:
                return nd
    
    def trav_ap(self, nd):
        # hmmm, for now, do not substitute inside generic ap
        return nd
    
    def trav_prf_ff(self, nd):
        # do not subst inside ff prf args
        return nd
        # return self.generic_trav_tuple(nd)


class ReplaceVariableTrav(DefaultTrav):
    """ Replace variable in the expression tree.
        If a replacement with a variable is needed, the variable
        should be already wrapped in NId() in the mapping.
        Param. 'mapping' is dict(): AttrCore -> node
    """
    def run_on(self, eqd, mapping):
        self.mapping = mapping
        self.count = 0;         # number of replacements performed
        return self.do_trav(eqd)
    
    def trav_id(self, eqd):
        if eqd.get_ref() in self.mapping:
            self.count += 1
            return self.mapping[eqd.get_ref()]
        else:
            return eqd


class SimplifyWithReplaceTrav(SimplifyExprTrav):
    """ Replace variable in the expression tree.
        If a replacement with a variable is needed, the variable
        should be already wrapped in NId() in the mapping.
        Param. 'mapping' is dict(): AttrCore -> node
    """
    def run_on(self, eqd, mapping):
        self.mapping = mapping
        self.count = 0;         # number of replacements performed
        return self.do_trav(eqd)
    
    def trav_id(self, eqd):
        if eqd.get_ref() in self.mapping:
            self.count += 1
            return self.mapping[eqd.get_ref()]
        else:
            return eqd


class HoistTrav(DefaultTrav):
    """ Hoist the given expression types out of the expr tree, 
        creating an aux variable for them. """
    def run_on(self, nd, prf_to_hoist=set([Prf.EQ, Prf.MPX]), recurse=False):
        self.hoisted_eq = dict()        # AttrCore -> nd expr tree
        self.prf_to_hoist = prf_to_hoist
        self.recurse = recurse
        return self.do_trav(nd), self.hoisted_eq

    def do_hoist_prf(self, nd):
        # The nd should be hoisted out. Check if the expression is already
        # known, in that case we may just insert a reference to the first one.
        for a2 in self.hoisted_eq:
            nd2 = self.hoisted_eq[a2]
            if CompareTrav().run_on(nd, nd2):
                # match!
                print('HoistTrav: matched {0}'.format(str(a2)))
                return NId(a2)

        tp = InferTypesTrav().run_on(nd)
        a = Attrib(names.give('hoisted'), tp)
        if not self.recurse:
            # only one level (sufficient for espresso)
            a.get_core().set_eqdef( nd )
            self.hoisted_eq[a.get_core()] = nd
        else:
            # recurse over nd args
            n_args = self.do_trav(nd.get_args())
            n_nd = NPrf(nd.get_prf(), n_args)
            a.get_core().set_eqdef( n_nd )
            self.hoisted_eq[a.get_core()] = n_nd
        return NId(a.get_core())

    def trav_others_prf(self, nd):
        if nd.get_prf() in self.prf_to_hoist:
            return self.do_hoist_prf(nd)
        else:
            return NPrf(nd.get_prf(), self.do_trav(nd.get_args()))


class IsInvertedTrav(DefaultTrav):
    """ Determine if the variable is used inverted. """
    def run_on(self, nd, var):
        self.var = var
        self.count = 0
        self.in_not = False
        self.do_trav(nd)
        return self.count

    def trav_prf_not(self, nd):
        self.in_not = not self.in_not
        self.do_trav(nd.get_args())
        self.in_not = not self.in_not

    def trav_id(self, nd):
        if (nd.get_ref() == self.var) and self.in_not:
            self.count += 1

    def trav_others_prf(self, nd):
        self.do_trav(nd.get_args())

    def trav_ap(self, nd):
        self.do_trav(nd.get_args())


class CorifyTrav(DefaultTrav):
    """ Replace each attribute by its core.
    """
    def trav_id(self, eqd):
        return NId( eqd.get_ref().get_core() )


class OptimizeFFCondTrav(DefaultTrav):
    """ Optimize conditions in flip-flop prfs. Replace by a constant
        if the condition variable is constant. """
    def run_on(self, nd):
        # self.in_ff = False
        return self.do_trav(nd)

    def trav_prf_ff(self, nd):
        #       0         1
        # ff(new_value, cond)
        args = nd.get_args()
        c = self.do_trav(args[1])
        if isinstance(c, NId):
            v = SimplifyExprTrav().run_on(c.get_ref().get_eqdef())
        else:
            v = c
        if type(v) == bool:
            # the condition is constant, replace it
            return NPrf(Prf.FF, [args[0], v])
            # return ('@@', 'ff', (',', args[1], v))
        # nothing
        return nd



