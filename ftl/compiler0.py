from ftl.ast import *
from ftl.basics import ModWirePort, CgInstance
from ftl.atrav import PrintTrav, ComputeHashesTrav, CompareTrav, ConvStdLogicTrav
from ftl.atrav_eq import SimplifyExprTrav, GatherUsedVarsTrav, SimplifyWithReplaceTrav, \
    AbsorpLawTrav, GatherDepVars_NoFF_Trav, ReplaceVariableTrav, OptimizeFFCondTrav, \
    MarkNecessaryVarsTrav, SimplifyWithSubstTrav
from ftl.atrav_cg import PrintAsVhdlTrav
from ftl.minbooleq import MinimizeExprTrav
from ftl.verifyrtl import VerifyRTL
from ftl.tarjan import TarjanSCC, TopoSort
from ftl.types import InferTypesTrav
from ftl.attrs import Attrib, AttrCore, AttrKind

import ftl.names as names
import ftl.dbgtim as dbgtim
import ftl.types as types

import sys, os, functools, argparse, random, socket


class CompilerBase:
    """
    Compiles FTL into VHDL.
    """
    
    def __init__(self, do_argv_parse=True):
        # a list of all elements in the design
        self.all_elems = []
        self.all_eqs = []           # list of AttrCore
        self.all_undefs = set([])
        self.all_ffs = []
        self.all_modports = []
        self.all_modwireports = []
        self.all_cgi = []       # list([CgInstance])
        self.all_stages = set([])              # list of all Stages in the design
        self.skip_print_tabulate = False
        self.skip_verify = False
        # v2 only:
        self.all_swisels = []
        #
        if do_argv_parse:
            parser = self.create_argv_parser()
            self.take_argv_options(parser.parse_args())

    def create_argv_parser(self):
        # get command line arguments
        parser = argparse.ArgumentParser(description='FTL compiler.')
        parser.add_argument('-r', nargs=1, type=int, help='Randomize')
        parser.add_argument('--tabulate', nargs=1, type=int, help='Tabulate FSM states. (0/1)')
        parser.add_argument('--verify', nargs=1, type=int, help='Verify FTL states. (0/1)')
        return parser

    def take_argv_options(self, parsed_args):
        self.argv_options = parsed_args
        self.randomize = (self.argv_options.r is not None) and (self.argv_options.r[0] >= 0)
        if self.randomize:
            random.seed(self.argv_options.r[0])
        if self.argv_options.tabulate is not None:
            self.skip_print_tabulate = (self.argv_options.tabulate[0] == 0)
        if self.argv_options.verify is not None:
            self.skip_verify = (self.argv_options.verify[0] == 0)
        msg = 'Hostname={0}, seed={1}'.format(socket.gethostname(), self.argv_options.r)
        print(msg)


    def create_add_fcore(self, name, expr):
        """ For unit tests. Create a new F-core (wand node) and adds it to the compiler's
            equations. """
        FA_attr = Attrib(name, types.Bool_t, AttrKind.Flows)
        FA = FA_attr.get_core()
        if expr is not None:
            FA.set_eqdef(expr)
            self.all_eqs.append(FA)
        else:
            self.all_undefs.add(FA)
            self.add_module_iwire_port(name, FA_attr)
        return FA

    
    def analyze_elems(self, elms):
        """ Analyze all elements in the list. """
        for e in elms:
            self.analyze_elem(e)
    
    
    def add_module_port(self, p):
        self.all_modports.append(p)

    
    def add_module_owire_port(self, name, eqd):
        """ Add the specified eqd as an output wire port of the module. """
        a = Attrib(names.give('ow_{0}'.format(name)), None)
        a.set_eqdef(eqd)
        self.add_eqs([a])
        wp = ModWirePort(ModWirePort.OUT, name, NId(a.get_core()))
        self.all_modwireports.append(wp)


    def add_module_iwire_port(self, name, at):
        """ Add the specified attribute at as an input wire port
            of the module. """
        wp = ModWirePort(ModWirePort.IN, name, NId(at.get_core()))
        self.all_modwireports.append(wp)

    def new_cginst(self, iname, cname):
        """ Create and return a new CgInstance (codegen component instance)
            with instance name iname and component name cname. """
        I = CgInstance(self, iname, cname)
        self.all_cgi.append(I)
        return I


    def analyze_elem(self, xelm):
        """ Analyze the given element. Construct its partial equations
            and resolve local types. """
        ee = xelm.expand()
        # TODO: expand recursively until a fixpoint is reached.
        for elm in ee:
            self.all_elems.append(elm)
            print ('Element {0} : {1}'.format(elm.get_name(), elm.__class__.__name__))
            eqs = elm.constr_eqs()   # gives a list of cores defined in the elem
            if elm.is_swisel():
                self.all_swisels.append(elm)
            
            self.all_eqs.extend(eqs)
            # simplify and print
            for eq in eqs:
                print ('    {0}...'.format(eq.get_name()))
                eq.resolve_type_locally()
                # eq.replace_eqdef(OldToNewTrav().run_on(eq.get_eqdef()))
                eq.replace_eqdef(SimplifyExprTrav().run_on(eq.get_eqdef()))
                # print
                if eq.get_actype() is None:
                    tpvhd = '??'
                else:
                    tpvhd = PrintAsVhdlTrav().run_on(eq.get_actype())
                print ('    {0} : {1} :{3}= {2};'.format(eq.get_name(), tpvhd,
                    PrintTrav().run_on(eq.get_eqdef()), eq.get_ackind()))
    
    
    def add_eqs(self, eqs):
        """ Add extra user-defined equations to the compiler system. """
        print ('Extra attributes:')
        for eq in eqs:
            eq = eq.get_core()
            eq.mark_as_necessary()             # user-defs are always non-dead
            eq.resolve_type_locally()
            if eq.get_eqdef() is not None:
                # eq.replace_eqdef(OldToNewTrav().run_on(eq.get_eqdef()))
                # eq.replace_eqdef(CorifyTrav().run_on(eq.get_eqdef()))
                eq.replace_eqdef(SimplifyExprTrav().run_on(eq.get_eqdef()))
            self.all_eqs.extend([eq])
            # print
            if eq.get_actype() is not None:
                tpvhd = PrintAsVhdlTrav().run_on(eq.get_actype())
            else:
                tpvhd = None
            print ('    {0} : {1} := {2};'.format(eq.get_name(), tpvhd, PrintTrav().run_on(eq.get_eqdef())))
    

    def dedup_eq_refs(self):
        """ Deduplicate references to the same equations in the set. """
        new_eqs = []
        seen = set([])
        for eq in self.all_eqs:
            ef = eq.fwd()  # follow forwardings!
            if ef not in seen:
                seen.add(ef)
                new_eqs.append(ef)
        self.all_eqs = new_eqs


    def partition_stages(self):
        """ Partition elements and pipes into stages """
        # propagate stages; merge them across all ports, except in Cell
        for elm in self.all_elems:
            elm.prop_stages()
        
        # create a set of all (remaining) stages
        for elm in self.all_elems:
            self.all_stages |= elm.get_stages()

        # add module inputs/outputs as stage bounds
        for mp in self.all_modports:
            if mp.is_inflow():
                # in-pipe is added as an i-bound
                mp.get_stage().add_i_bound(mp)
            if mp.is_outflow():
                # out-pipe is added as an o-bound
                mp.get_stage().add_o_bound(mp)

        # print stages
        for st in self.all_stages:
            print('Stage {0}:'.format(st.id))
            str_ib = functools.reduce(lambda x,y: (x+', '+str(y)), st.ibound, '')
            print('    i-bounds: {0}'.format(str_ib))
            str_ob = functools.reduce(lambda x,y: (x+', '+str(y)), st.obound, '')
            print( '    o-bounds: {0}'.format(str_ob))
            str_intra = functools.reduce(lambda x,y: (x+', '+str(y)), st.pipes, '')
            print( '    intra: {0}'.format(str_intra))


    def check_all_stages_acyclic(self):
        """ Check that all stages are acyclic. """
        for st in self.all_stages:
            st.check_stage_acyclic()


    def extract_undefs(self):
        """ Find undefined attributes (variables) in the system of equations. """
        print( 'Extracting undefined attribs (assuming primary inputs):')
        used = set([])
        # from eqs
        for eq in self.all_eqs: 
            assert eq.get_eqdef() is not None, 'Equation {0} has no RHS (None)'.format(eq)
            used |= GatherUsedVarsTrav().run_on(eq.get_eqdef())
        # from module ports (assumed to be present to simplify codegen)
        for mp in self.all_modports:
            fi = mp.get_FI_core()
            used.add(fi)
        self.all_undefs = used - set(self.all_eqs)
        print( '    {0}'.format(self.all_undefs))
        return self.all_undefs


    def normalize_wand(self, eq):
        """ Update the equation into a normalized WAND form. """
        if type(eq.get_eqdef()) == bool:
            # leave constant as is
            return True
        else:
            if not isinstance(eq.get_eqdef(), NPrf) or eq.get_eqdef().get_prf() != Prf.AND:
                # normalize to WAND
                eq.replace_eqdef(NPrf(Prf.AND, [eq.get_eqdef()]))
            return False

        # if eq.get_eqdef().get_prf() != Prf.AND:
        #     # normalize to WAND 
        #     eq.replace_eqdef(NPrf(Prf.AND, [eq.get_eqdef()]))

    def simplify_wands(self, eqs):
        """ Simplify WAND equations. """
        _tim = dbgtim.Timing('simplify_wands')
        # TODO: constant propagation, but must not subst IO port wands.
        #   But may always subst those statically False.

        # constant propagation: determine the constant variables
        prop = dict()
        for eq in eqs:
            if eq.get_ackind() != AttrKind.Flows:
                continue
            if type(eq.get_eqdef()) == bool:
                prop[eq] = eq.get_eqdef()

        restart = True
        while restart:
            restart = False
            print('  simplify_wands: prop={0}'.format(prop))

            for eq in eqs:
                if eq.get_ackind() != AttrKind.Flows:
                    continue
                if eq in prop:
                    # it is already a constant, further simplification not possible
                    continue

                _tim_1 = dbgtim.Timing('simplify_wands/{0}'.format(eq))
                # eq.replace_eqdef( SimplifyExprTrav().run_on(eq.get_eqdef()) )
                eq.replace_eqdef( SimplifyWithReplaceTrav().run_on(eq.get_eqdef(), prop) )
                eq.replace_eqdef( AbsorpLawTrav().run_on(eq.get_eqdef()) )

                if self.normalize_wand(eq):
                    # and a new constant! Repeat.
                    prop[eq] = eq.get_eqdef()
                    restart = True

                # if type(eq.get_eqdef()) == bool:
                #     # a new constant! Repeat.
                #     prop[eq] = eq.get_eqdef()
                #     restart = True
                # else:
                #     if not isinstance(eq.get_eqdef(), NPrf) or eq.get_eqdef().get_prf() != Prf.AND:
                #         # normalize to WAND
                #         eq.replace_eqdef(NPrf(Prf.AND, [eq.get_eqdef()]))
                _tim_1.fin()
        _tim.fin()


    def find_direct_edges(self, f, t):
        """ Test if there is a direct edge from f to t.
            Return [] if not, or the list of indices in the t WAND args.
        """
        r = []
        eds = t.wand_edges()
        for i in range(0, len(eds)):        # over edges incomming to t
            if isinstance(eds[i], NId) and eds[i].get_ref() == f:
                r.append(i)
        return r

    def gather_direct_deps(self, nd):
        """ Returns the set of direct dependency nodes. """
        r = set()
        eds = nd.wand_edges()
        for i in range(0, len(eds)):        # over edges incomming to t
            if isinstance(eds[i], NId):
                r.add(eds[i].get_ref())
        return r


    # def find_inv_direct_edges(self, f, t):
    #     """ Test if there is an inverted direct edge from f to t.
    #         Return [] if not, or the list of indices in the t WAND args.
    #     """
    #     r = []
    #     eds = t.wand_edges()
    #     for i in range(0, len(eds)):        # over edges incomming to t
    #         if isinstance(eds[i], NPrf) and eds[i].get_prf() == Prf.NOT:
    #             n = eds[i].get_args()[0]
    #             if isinstance(n, NId) and n.get_ref() == f:
    #                 r.append(i)
    #     return r

    def merge_wand_nodes(self, a, b):
        # merge edges
        a.wand_add(b.wand_edges())
        b.replace_eqdef(None)

        # Fixup deps:
        # In all predecessors of b, exchange b for a in the successor lists.
        for x in b.pred():
            x.succ().remove(b)
            x.succ().add(a)
            print('    b.pred: x={0}, succ={1}'.format(x, x.succ()))

        # In all successors of b, exchange b for a in the predecessor lists.
        for x in b.succ():
            x.pred().remove(b)
            x.pred().add(a)
            print('    b.succ: y={0}, pred={1}'.format(x, x.pred()))

        print('    direct; a.succ={0}, a.pred={1}, b.succ={2}, b.pred={3}'.format(
            a.succ(), a.pred(), b.succ(), b.pred()))

        # 
        a.succ().update(b.succ())

        b.clear_deps()

        print('    direct; a.succ={0}, a.pred={1}, b.succ={2}, b.pred={3}'.format(
            a.succ(), a.pred(), b.succ(), b.pred()))

        a.succ().discard(b)

        # re-initialize a.pred() by recomputing it afresh from the eq.
        # this also updates succ()
        self.recompute_pred_dep(a)

        # Merge cores. All uses of 'b' will be redirected to 'a' in NId.
        a.merge(b)
        # remove b from the list of all eqs
        del self.all_eqs[self.all_eqs.index(b)]

        print('    {0} :F= {1}'.format(a.get_name(), 
            PrintTrav().run_on(a.get_eqdef())))
        print('    a.succ={0}, a.pred={1}'.format(a.succ(), a.pred()))
        # self.print_all(show_deps=True, only_necessary=False)


    def merge_wand_nodes__nodeps(self, a, b):
        """ Merge wand node 'b' into 'a'. Does NOT update dependency info. """
        # merge edges
        a.wand_add(b.wand_edges())
        b.replace_eqdef(None)

        a.clear_deps()      # info destroyed
        b.clear_deps()      # the b has been cleared

        # Merge cores. All uses of 'b' will be redirected to 'a' in NId.
        a.merge(b)
        # remove b from the list of all eqs
        del self.all_eqs[self.all_eqs.index(b)]

        # print('        {0} :F= {1}'.format(a.get_name(), 
        #     PrintTrav().run_on(a.get_eqdef())))



    # TODO: rename to recompute_dep
    def recompute_pred_dep(self, eq):
        """ Recompute the pred() dependency in the eq """
        _tim = dbgtim.Timing('recompute_pred_dep/{0}'.format(eq))
        pred = GatherDepVars_NoFF_Trav().run_on(eq.get_eqdef())
        print('  new pred={0}'.format(pred))
        eq.reset_pred(pred)
        _tim.fin()


    def compute_deps(self):
        """ Compute equation dependencies: the pred() and succ() values. """
        _tim = dbgtim.Timing('compute_deps')

        for eq in self.all_eqs:
            # Init Tarjan info in the eq node
            eq.clear_deps()

        # init also undefined eqs, though they won't have much of an effect on SCCs
        for eq in self.all_undefs:
            eq.clear_deps()

        # init also phis
        # for eq in self.all_phis_map.values():
        #     eq.clear_deps()

        for eq in self.all_eqs:
            # Determine the set of variables this equation depends on (the predecessors).
            # Do not traverse across Prf.FF  XXX ???
            pred = GatherDepVars_NoFF_Trav().run_on(eq.get_eqdef())  # OR GatherUsedVarsTrav ???
            eq.reset_pred(pred)

        _tim.fin()


    def infer_types(self):
        """ Infer data types of all equations. """
        print( 'Infering types:')
        k = 1
        while k > 0:
            k = 0
            for eq in self.all_eqs:
                # print('Before {0} := {1}'.format(eq.get_name(), PrintTrav().run_on(eq.get_eqdef())))
                
                tp = InferTypesTrav().run_on(eq.get_eqdef())
                
                # print('After  {0} := {1}'.format(eq.get_name(), PrintTrav().run_on(eq.get_eqdef())))
                # if eq.get_actype() is None:
                #     tpvhd = '??'
                # else:
                #     tpvhd = PrintAsVhdlTrav().run_on(eq.get_actype())
                # print('After  {0} : {1} := {2};'.format(eq.get_name(), tpvhd, PrintTrav().run_on(eq.get_eqdef())))

                if (tp is not None) and (eq.get_actype() is None):
                    eq.set_actype(tp)
                    k += 1
                    #print '    %s : %s := %s;' % (eq.get_name(), eq.get_actype(), PrintTrav().run_on(eq.get_eqdef()))
        # Printing
        for eq in self.all_eqs:
            if eq.get_actype() is None:
                tpvhd = '??'
            else:
                tpvhd = PrintAsVhdlTrav().run_on(eq.get_actype())
            print( '    {0} : {1} := {2};'.format(eq.get_name(), tpvhd, PrintTrav().run_on(eq.get_eqdef())))
        

    def minimize_all_eq(self, do_print_eqs=True):
        """ Minimize bool equations using espresso. """
        print( 'Minimizing equations (espresso):')
        for eq in self.all_eqs:
            self.minimize_eq(eq, do_print_eq=do_print_eqs)
    
    
    def minimize_eq(self, eq, do_print_eq=True):
        """ Minimize the equation by espresso. """
        print('  {0}...'.format(eq.get_name()))
        eqd_dlaw = AbsorpLawTrav().run_on(eq.get_eqdef())
        eq.replace_eqdef( SimplifyExprTrav().run_on(eqd_dlaw) )
        t = MinimizeExprTrav()
        new_eqd = t.run_on(eq.get_eqdef())
        if t.num_minim > 0:
            if do_print_eq:
                print( '    {0} := {1};'.format(eq.get_name(), PrintTrav().run_on(new_eqd)))
            eq.replace_eqdef(new_eqd)


    def minimize_eqs(self, eqs, do_print_eqs=True):
        """ Minimize the given expressions in espresso """
        if do_print_eqs: print( 'Minimizing selected equations (espresso):')
        for eq in eqs:
            self.minimize_eq(eq, do_print_eq=do_print_eqs)
        
    
    def mark_necessary_eqs(self):
        """ Mark unused/unnecessary equations and attribs. """
        for mp in self.all_modports:
            mp.mark_attribs_necessary()
        
        for eq in self.all_eqs:
            if eq.is_necessary():
                deps = MarkNecessaryVarsTrav().run_on(eq.get_eqdef())
    
    
    def optimize_ff_cond(self):
        """ Run the OptimizeFFCondTrav traversal over over all eqs """
        for eq in self.all_eqs:
            eq.replace_eqdef( OptimizeFFCondTrav().run_on(eq.get_eqdef()) )
        
        
    def print_all(self, only_necessary=True, show_hash=False, show_deps=False):
        """ Print all equations to the screen. """
        if only_necessary:
            which = 'only non-dead'
        else:
            which = 'all'
        print( 'All equations ({0}):'.format(which))
        for eq in self.all_eqs:
            if not only_necessary or eq.is_necessary():
                # print(eq.get_name(), eq.get_actype())
                if eq.get_actype() is not None:
                    tpvhd = PrintAsVhdlTrav().run_on(eq.get_actype())
                else:
                    tpvhd = '??'
                if eq.is_necessary():
                    ndead = '*'
                else:
                    ndead = ' '
                hstr = ''
                if show_hash:
                    h = nhash(eq.get_eqdef())
                    if h:
                        hstr = '({0}) '.format(hex(h))
                    else:
                        hstr = '(None) '
                print( '  {0} {4}{1} : {2} := {3};'.format(ndead, eq.get_name(), tpvhd,
                    PrintTrav().run_on(eq.get_eqdef()), hstr))
                if show_deps:
                    print('      pred: {0}'.format(eq.pred()))
                    print('      succ: {0}'.format(eq.succ()))

    
    
    def separate_ffs(self):
        """ Separate the flip-flops from the rest of the combinatorial equations. """
        new_all_eqs = []
        self.all_ffs = []
        for eq in self.all_eqs:
            eqd = eq.get_eqdef()
            # if type(eqd) == tuple and eqd[0] == '@@' and eqd[1] == 'ff':
            if isinstance(eqd, NPrf)  and eqd.get_prf() == Prf.FF:
                # flip-flop
                self.all_ffs.append(eq)
            else:
                new_all_eqs.append(eq)
        self.all_eqs = new_all_eqs
    

    def no_more_cycles(self):
        sccl = TarjanSCC().run_on(self.all_eqs)
        print('SCCL: {0}'.format(sccl))
        cnt = 0
        for sc in sccl:
            if len(sc) != 1:
                print('ERROR: found strong component larger than one node: {0}'.format(sc))
                cnt += 1
        assert cnt == 0, 'FATAL: Cycles not eliminated?! ({0} large SCs)'.format(cnt)


    def explicit_port_drivers(self):
        """ Drivers for the module ports:
        At the beginning each port's WAND serves as both an input and output
        for external logic. During cycle elimination however the edges may be 
        moved around. Thus at the end the input edge (external driver)
        will be disambiguated in mp.attr_FI
        """
        for mp in self.all_modports:
            a = mp.get_F_core()
            dr_attr = Attrib(names.give(a.get_name()), a.get_actype(), a.get_ackind())
            dr = dr_attr.get_core()
            # self.all_undefs.add(dr)   overwriten in extract_undefs()
            dr.mark_as_necessary()
            mp.attr_FI = dr_attr
            mp.get_F_core().wand_add(NId(dr))



        
    def tabulate_states(self, only_necessary = True):
        """ Print a table of all FSM states.
            Requires that attr dependency info is computed.
        """
        print( "Tabulating all states of the RTL circuit:")
        prim_inputs = dict()       # str:name -> AttrCore:eq
        for mp in self.all_modports:
            # eq = mp.get_F_core()
            # eq = self.modp_drivers[mp].get_core()
            eq = mp.get_FI_core()
            assert eq is not None
            prim_inputs[eq.get_name()] = eq 

        for mwp in self.all_modwireports:
            eq = mwp.get_eq()
            if eq.get_actype() is types.Bool_t:
                prim_inputs[eq.get_name()] = eq

        # internal regs
        ff_states = dict()
        for elm in self.all_elems:
            for eq in elm.get_fsm_stor():
                ff_states[eq.get_name()] = eq

        # dependent vars
        deps = dict()
        for eq in self.all_eqs:
            # FIXME: better test if the var is system
            # if eq.get_ackind() in [AttrKind.Present, AttrKind.Ready]:
            if eq.get_actype() is types.Bool_t:
                if not only_necessary or eq.is_necessary():
                    deps[eq.get_name()] = eq

        # print table header
        h_indep = []
        for nm in sorted(prim_inputs.keys()):
            h_indep.append(prim_inputs[nm])
        for nm in sorted(ff_states.keys()):
            h_indep.append(ff_states[nm])

        # topologically sort the eqs according to their dependencies
        # so that we need only one pass to compute values.
        ts_deps = TopoSort().run_on(deps.values())
        # print('Topo sorted deps={0}'.format(ts_deps))

        h_dep = []
        for nm in sorted(deps.keys()):
            h_dep.append(deps[nm])

        s_header = ''
        for eq in h_indep:
            s_nm = '| {0} '.format(eq.get_name())
            s_header = s_header + s_nm
        s_header = s_header + '|'
        for eq in h_dep:
            s_nm = '| {0} '.format(eq.get_name())
            s_header = s_header + s_nm

        print( s_header)

        for cc in range(0, 2**len(h_indep)):
            k = len(h_indep) - 1
            v_indep = []
            cc_subst = dict()
            s_ln = ''
            for hi in h_indep:
                b = (cc >> k) & 1
                pre = post = (len(hi.get_name()) - 1) // 2
                if (pre+post+1) < len(hi.get_name()):
                    post += 1
                s_ln = '{0}| {1}{2}{3} '.format(s_ln, ' '*pre, b, ' '*post)
                k -= 1
                b = (b and True) or False   # convert 0/1 to False/True
                v_indep.append( b )
                cc_subst[hi] = b
            s_ln += '|'

            # compute values according to the topo sort order
            for hd in ts_deps:   # in the order of the topological deps.
                if hd in deps.values():
                    b = SimplifyWithSubstTrav().run_on(hd.get_eqdef(), cc_subst)
                    cc_subst[hd] = b

            # display in the alphabetical order
            for hd in h_dep:
                # b = SimplifyWithSubstTrav().run_on(hd.get_eqdef(), cc_subst)
                b = cc_subst[hd]
                if b is True:
                    b = 1
                else:
                    if b is False:
                        b = 0
                    else:
                        b = '+'
                        # b = PrintTrav().run_on(b)
                pre = post = (len(hd.get_name()) - 1) // 2
                if (pre+post+1) < len(hd.get_name()):
                    post += len(hd.get_name()) - (pre+post+1)
                s_ln = '{0}| {1}{2}{3} '.format(s_ln, ' '*pre, b, ' '*post)
            print( s_ln)


    def verify(self):
        """ Verify the final equations, check that they produce consistent
            results wrt FTL """
        print( "Verifying RTL equations:")
        ver = VerifyRTL()
        ver.verify(self.all_elems)
        if ver.stat_count_elems == 0:
            ver.stat_count_elems = 1 # avoid division by zero...
        print( 'Verify done: elements: {0}, states: {1}, avg {2} states/elem'.format(
                    ver.stat_count_elems, ver.stat_count_states, ver.stat_count_states//ver.stat_count_elems))


    def hoist_mpx(self, only_necessary=False):
        """ Hoist Prf.MPX, Prf.COND out of expressions into independent vars. """
        more_eqs = []
        for eq in self.all_eqs:
            if only_necessary and not eq.is_necessary():
                continue
            # hoist MPX out of the eq
            n_eqd, h_vars = HoistTrav().run_on(eq.get_eqdef(), set([Prf.MPX, Prf.COND]), recurse=True)
            eq.replace_eqdef(n_eqd)
            if only_necessary:
                for hv in h_vars:
                    hv.mark_as_necessary()
            more_eqs.extend(h_vars.keys())
        self.all_eqs.extend(more_eqs)

    def conv_std_ulogic(self):
        """ Wrap equivalence tests (a=b) in to_stdulogic """
        for eq in self.all_eqs:
            if eq.is_necessary():
                eq.replace_eqdef( ConvStdLogicTrav().run_on(eq.get_eqdef()) )

    def rehash(self):
        """ Recompute equation hashes. """
        for eq in self.all_eqs:
            ComputeHashesTrav().run_on(eq.get_eqdef())

    def elim_dup_eqs(self, only_necessary=False):
        print("Eliminating duplicate equations:")
        hash2eq = dict()        # hash -> eq
        replacing = dict()      # AttrCore -> eq2
        for eq in self.all_eqs:
            if only_necessary and not eq.is_necessary():
                continue
            # get eq's hash and look it up in the dict
            h = nhash(eq.get_eqdef())
            if h in hash2eq:
                # candidate list of eqs with the same hash
                hl = hash2eq[h]
                # try each
                for eq2 in hl:
                    if CompareTrav().run_on(eq.get_eqdef(), eq2.get_eqdef()):
                        # match! eq and eq2 are identical.
                        # eq is duplicate of eq2
                        eq.replace_eqdef( NId(eq2) )
                        replacing[eq] = NId(eq2)
                        print('    Dup: {0} <-- {1}, necessary: ({2})'.format(
                            str(eq), str(eq2), (eq.is_necessary(), eq2.is_necessary()) ))
                        break
                else:
                    # no match. Add the eq to the hash list
                    hl.append(eq)
                    hash2eq[h] = hl
            else:
                hash2eq[h] = [eq]

        if replacing:
            # replace all found to be equal
            for eq in self.all_eqs:
                # GatherUsedVarsTrav()
                eq.replace_eqdef( ReplaceVariableTrav().run_on(eq.get_eqdef(), replacing) )
        # return the number of unified eqs
        return len(replacing)
