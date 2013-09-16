from ftl.ast import *
import ftl.types as types

AttrKind = enum(
    Present = 'P',
    Ready = 'R',
    Data = 'D',
    Other = 'O',
    Flows = 'F',
    Const = 'C'
)


class AttrCore(Node):
    """ The core for a set of attributes. """
    
    def __init__(self, first, actype, ackind):
        self.attrs = [first]    # list of Attrib
        self.eq_def = None     # expr
        self.ackind = ackind
        self.f_is_necessary = False         # flag, 
        self.actype = actype     # type
        self.allow_subst = True        # flag
        self.companions = dict()
        self.merged_to = None
        self.clear_deps()
    
    def get_attrs(self): return self.attrs
    
    def merge(self, other_c):
        """ Merge the other core with this one. The other_c is considered a proxy. """
        if isinstance(other_c.get_eqdef(), NPrf) and other_c.get_eqdef().get_prf()==Prf.AND \
                and len(other_c.get_eqdef().get_args())==0:
            other_c.replace_eqdef(None)

        assert other_c.eq_def is None, 'Merge to {2}: core {0} has non-empty eq_def={1}'.format(
            other_c.get_name(), atrav.PrintTrav().run_on(other_c.get_eqdef()), self.get_name())
        assert other_c != self, 'Cannot merge {0} to itself.'.format(self.get_name())

        # redirect the other's core Attribs to me
        for a in other_c.get_attrs():
            assert a.get_core() == other_c
            # assert a.get_core().is_reverse() == self.is_reverse()
            a.set_core(self)
        # add the other's Attrib to mine
        self.attrs.extend(other_c.get_attrs())
        self.companions.update(other_c.companions)
        # propagate the Necessary flag
        if other_c.is_necessary():
            self.mark_as_necessary()
        # the other core is hollow
        other_c.attrs = None
        other_c.merged_to = self


    def fwd(self):
        if self.merged_to is not None:
            return self.merged_to.fwd()
        else:
            return self
    
    def set_eqdef(self, eqdef, origin=None):
        assert self.eq_def is None, 'The AttrCode has already a definition!'
        self.eq_def = eqdef
        if (origin is not None) and (self.attrs[0] is not origin):
            # reshuffle the attrs list: put origin at the beginning
            for i in range(1, len(self.attrs)):
                if self.attrs[i] is origin:
                    self.attrs[i] = self.attrs[0]
                    self.attrs[0] = origin
                    break
            else:
                assert False, "Could not find origin in the attrs list!"

    
    def replace_eqdef(self, eqdef):
        self.eq_def = eqdef
    
    def get_eqdef(self):
        return self.eq_def
    
    def get_name(self):
        if self.merged_to is not None:
            return '*'+self.fwd().get_name()
        return self.attrs[0].get_name()
    
    def __str__(self):
        return self.get_name()
    
    def __repr__(self):
        return self.get_name()
        #return '%s := %s;' % (self.get_name(), self.eq_def)
    
    def resolve_type_locally(self):
        for at in self.attrs:
            self.actype = types.resolve_types(self.actype, at.get_atype())
    
    def get_actype(self):
        return self.actype
    
    def set_actype(self, tp):
        self.actype = tp
    
    def set_allow_subst(self, f):
        self.allow_subst = f
    
    def is_subst_allowed(self):
        return self.allow_subst
    
    def mark_as_necessary(self):
        self.f_is_necessary = True

    def is_necessary(self):
        return self.f_is_necessary

    def get_ackind(self):
        return self.ackind

    def set_companion(self, c_ackind, c_attr):
        self.companions[c_ackind] = c_attr
    
    def get_companion(self, c_ackind):
        return self.companions[c_ackind]
    

    def clear_deps(self):
        """ Clear dependency data, prepare for tarjan SCC. """
        self.d_succ = set()
        self.d_pred = set()
        self.tarjan_index = None
        self.tarjan_lowlink = None

    def reset_pred(self, prd):
        """ Change current pred() into the new one. """
        # go over the old pred and remove us from the succ over there
        for p in self.d_pred:
            p.d_succ.discard(self)  # do not check for existance
        # change old to new
        self.d_pred = prd
        # go over the new and add us to succ.
        for p in self.d_pred:
            p.d_succ.add(self)

    # Predecessors = USES: the wand nodes that we depend on.
    def pred(self): return self.d_pred
    # Successors = USED BY: the wand nodes that depend on this.
    def succ(self): return self.d_succ


    def wand_add(self, x):
        """ Add x to the wand expression. """
        assert self.ackind == AttrKind.Flows
        # assert self.eq_def.get_prf() == Prf.AND, 'wand_add: self {0} := {1}'.format(
            # self.get_name(), atrav.PrintTrav().run_on(self.get_eqdef()))
        # normalize to WAND
        if not isinstance(self.eq_def, NPrf) or self.eq_def.get_prf() != Prf.AND:
            # convert
            self.replace_eqdef( NPrf(Prf.AND, [self.eq_def]) )
        #
        if type(x) == list or type(x) == tuple:
            self.replace_eqdef( NPrf(Prf.AND, self.eq_def.get_args() + tuple(x)) )
        else:
            assert x is not None, 'Adding None to wand {0}'.format(self.get_name())
            self.replace_eqdef( NPrf(Prf.AND, self.eq_def.get_args() + (x, )) )

    def wand_edges(self):
        """ Return the list of incomming edges in the WAND expression. """
        assert self.ackind == AttrKind.Flows, "Cannot get wand_edges in {0}, it is the kind {1}".format(self.get_name(), self.ackind)
        assert self.eq_def is not None, "Cannot get wand_edges in {0}, the eqdef is None!".format(self.get_name())
        if self.eq_def.get_prf() == Prf.AND:
            return self.eq_def.get_args()
        else:
            return (self.eq_def, )

    def wand_replace_edge(self, p, edg):
        """ Replace edge at the pos p with edg """
        assert self.ackind == AttrKind.Flows
        assert self.eq_def.get_prf() == Prf.AND
        ag = list(self.eq_def.get_args())
        ag[p] = edg
        self.replace_eqdef( NPrf(Prf.AND, ag) )

    def wand_remove_edges(self, lp, v=True):
        """ Remove edges listed in lp (a list of indices), replace them with v """
        assert self.ackind == AttrKind.Flows
        # assert self.eq_def.get_prf() == Prf.AND, 'wand_remove_edges: {0} has not Prf.AND at top level'.format(self)
        # normalize to WAND
        if not isinstance(self.eq_def, NPrf) or self.eq_def.get_prf() != Prf.AND:
            # convert
            self.replace_eqdef( NPrf(Prf.AND, [self.eq_def]) )
        ag = list(self.eq_def.get_args())
        for p in lp:
            ag[p] = v
        self.replace_eqdef( NPrf(Prf.AND, ag) )


class Attrib(Node):
    """
    Attribute frontend. Several attribute fronts may in fact represent
    a signle attribute 'core'.
    TODO: remove, use NId or NNamedId instead.
    """
    
    def __init__(self, nm, tp, ackind=AttrKind.Other, eqd=None):
        self.core = AttrCore(self, tp, ackind)
        self.name = nm
        self.atype = tp
        if eqd:
            self.set_eqdef(eqd)
    
    def get_core(self): return self.core
    def set_core(self, c):
        self.core = c
    def get_name(self): return self.name
    def get_atype(self): return self.atype
    
    def set_eqdef(self, eqdef):
        return self.core.set_eqdef(eqdef, self)

    def merge(self, other_a):
        if self.core is not other_a.get_core():
            # the cores are different, hence we may merge them
            other_a.get_core().merge(self.core)

    def rename(self, new_name):
        self.name = new_name

    def __str__(self):
        return 'Attrib({0})'.format(str(self.core))

    def __repr__(self):
        return 'Attrib({0})'.format(str(self.core))
