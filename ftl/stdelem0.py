from ftl.ast import *
from collections import deque
# from ftl.attrs import Attrib, AttrKind
# from ftl.basics import Element, PipeOutflow, PipeInflow

# FOR TEST PROGS:
from ftl.basics import *
from ftl.attrs import *

# 
# Common std. elements for alg. v1 and v2
# 

class Fork(Element):
    """ Synchronous fork of a single input pipe into multiple output pipes. """
    def __init__(self, nm, n_outs = 2, dtype = None):
        Element.__init__(self, nm)
        self.ports = [PipeInflow(self, 0, dtype=dtype)]
        for i in range(0, n_outs):
            self.ports.append(PipeOutflow(self, i+1, dtype=dtype))
    
    def constr_eqs(self):
        # pipe 0 input, 1-n outputs
        eqs = []
        
        for i in range(0, len(self.ports)):
            for k in range(0, len(self.ports)):
                if i != k:
                    self.ports[i].get_F_core().wand_add(
                        NId(self.ports[k].get_F_core()) )
            #
            eqs.append( self.ports[i].get_F_core() )

        # output Di <= D0
        for i in range(1, len(self.ports)):
            self.ports[i].get_aD().set_eqdef( NId(self.ports[0].get_D_core()) )
            eqs.append( self.ports[i].get_D_core())
        
        return eqs


class Join(Element):
    """ Synchronous join of several inputs to a single output. """
    def __init__(self, nm, n_ins = 2, dtype = None, fun = None):
        Element.__init__(self, nm)
        self.fun = fun
        self.ports = [PipeOutflow(self, 0, dtype=dtype)]
        for i in range(0, n_ins):
            self.ports.append(PipeInflow(self, i+1))
    
    def constr_eqs(self):
        # pipe 0 output, 1-n inputs
        eqs = []
        
        for i in range(0, len(self.ports)):
            for k in range(0, len(self.ports)):
                if i != k:
                    self.ports[i].get_F_core().wand_add(
                        NId(self.ports[k].get_F_core()) )
            #
            eqs.append( self.ports[i].get_F_core() )

        # data path
        if self.fun == '@take_first':       # hack
            self.ports[0].get_aD().set_eqdef( NId(self.ports[1].get_D_core()) )
            eqs.append(self.ports[0].get_D_core())
        else:
            args = []
            for i in range(1, len(self.ports)):
                args.append( NId(self.ports[i].get_D_core()) )
            # do not follow F-core reference inside the fun.
            args.append( NPrf(Prf.NOFOLLOW, [NId(self.ports[0].get_F_core())]) )
            self.ports[0].get_aD().set_eqdef( NAp(self.fun, args) )
            self.ports[0].get_D_core().set_allow_subst(False)
            eqs.append(self.ports[0].get_D_core())

        return eqs


class DICell(Element):
    """ A multi-level Cell. """

    def __init__(self, nm, ndelay, isol, dtype = None):
        Element.__init__(self, nm)
        assert ndelay > 0, 'DICell {0}: ndelay must be > 0'.format(nm)
        self.ports = [PipeInflow(self, 0), PipeOutflow(self, 1)]
        self.ndelay = ndelay
        self.isolate = isol
        self.P_stor = [None] * ndelay
        self.D_stor = [None] * ndelay
        self.P_ini_st = [False] * ndelay
        self.D_ini_st = [None] * ndelay
        for i in range(0, ndelay):
            self.P_stor[i] = Attrib('P{0}st{1}'.format(nm, i), types.Bool_t, AttrKind.Present)
            self.P_stor[i].get_core().set_allow_subst(False)
            self.D_stor[i] = Attrib('D{0}st{1}'.format(nm, i), dtype, AttrKind.Data)
            self.D_stor[i].get_core().set_allow_subst(False)
            self.D_stor[i].get_core().set_companion(AttrKind.Present, self.P_stor[i])
    
    def get_fsm_stor(self):
        stcores = [None] * self.ndelay
        for i in range(0, len(self.P_stor)):
            stcores[i] = self.P_stor[i].get_core()
        return stcores

    def set_init_st(self, pst, dst, level=-1):
        """ Set Cell initial state. """
        self.P_ini_st[level] = pst
        self.D_ini_st[level] = dst

    def rename(self, newname):
        """ Rename the Cell, including the attribs. Required for Macros. """
        Element.rename(self, newname)
        for i in range(0, self.ndelay):
            self.P_stor[i].rename('P{0}st{1}'.format(newname, i))
            self.D_stor[i].rename('D{0}st{1}'.format(newname, i))

    def is_full_body(self):
        # eq = ('|', False, )
        args = []
        for i in range(0, self.ndelay-1):    # not the last reg
            args.append( NId(self.P_stor[i].get_core()) )
        return NPrf(Prf.OR, args)

    def is_full_tail(self):
        return NId(self.P_stor[-1].get_core())      # check the last reg only

    def data_tail(self):
        return NId(self.D_stor[-1].get_core())

    def prop_stages(self):
        """ Propagate stages. However, cells are boundary elements
        wrt. stages, hence register their ports as boundaries of the stages. """
        # the cell input port is the o-bound of that Stage
        self.ports[0].get_stage().add_o_bound(self.ports[0])
        # the cell output port is the i-bounf of its stage
        self.ports[1].get_stage().add_i_bound(self.ports[1])
        # Note that even if both ports belong to the same Stage
        # (now or in the future), they still constitute a boundary
        # of the stage. Boundaries are meant to track timing dependency.
    
    # def __init__(self, nm, nlev, dtype = None):
    #     _CellBase.__init__(self, nm, dtype)

    def enabled(self):
        """ The Enable signal for all regs. """
        # return ('|', self.ports[1].get_aR(), ('!', self.P_stor[-1]))
        return NPrf(Prf.OR, [ NId(self.ports[1].get_F_core()), 
                                NPrf(Prf.NOT, [NId(self.P_stor[-1].get_core())])
                            ])

    def constr_eqs(self):
        # pipe 0 input, pipe 1 output

        if self.isolate:
            # A &= not(v)
            self.ports[0].get_F_core().wand_add(
                NPrf(Prf.NOT, [NId(self.P_stor[-1].get_core())]) )
        else:
            # A &= not(v) | B
            self.ports[0].get_F_core().wand_add(
                NPrf(Prf.OR, [ NId(self.ports[1].get_F_core()),
                    NPrf(Prf.NOT, [NId(self.P_stor[-1].get_core())]) ])
            )

        # B &= v
        self.ports[1].get_F_core().wand_add( NId(self.P_stor[-1].get_core()) )
        
        # The Enable signal for all regs.
        # Independent of the "isolate" flag.
        en = self.enabled()

        # the set of defined equations
        # eqs = [self.ports[0].get_R_core(), self.ports[1].get_P_core(),
        #        self.ports[1].get_D_core() ]
        eqs = [self.ports[0].get_F_core(), self.ports[1].get_F_core(),
                self.ports[1].get_D_core()]

        # The first reg [0] reads from the port X
        prev_Pstor = self.ports[0].get_F_core()
        prev_Dstor = self.ports[0].get_D_core()

        for i in range(0, self.ndelay):
            # cell initial values
            if self.D_ini_st[i] is None:
                self.D_ini_st[i] = NPrf(Prf.ZERO_CONST_TP, [])

            self.P_stor[i].get_core().set_eqdef(
                    NPrf(Prf.FF, [NId(prev_Pstor), en, self.P_ini_st[i]]) )
            
            self.D_stor[i].get_core().set_eqdef(
                    NPrf(Prf.FF, [NId(prev_Dstor), en, self.D_ini_st[i]]) )

            prev_Pstor = self.P_stor[i].get_core()
            prev_Dstor = self.D_stor[i].get_core()
            eqs.extend([self.P_stor[i].get_core(), self.D_stor[i].get_core()])

        # the last register drives the output pipe
        # self.ports[1].get_aP().set_eqdef(self.P_stor[-1].get_core())
        self.ports[1].get_aD().set_eqdef( NId(self.D_stor[-1].get_core()) )

        return eqs


    def verify_consistency(self, pf_values, aa_values):
        """ Verify that the input/output pipes, whose state is in
            pf_values, are consistent with the FTL rules of the element. """
        # not isolated: Port 0 (input) can be excited iff the last reg is empty or the Port 1 (output) is excited.
        # isolated: Port 0 (input) can be excited iff the last reg is empty.
        if pf_values[self.ports[0]]:
            # port 0 is excited.
            if self.isolate:
                # the last reg must be empty.
                if aa_values[self.get_fsm_stor()[-1]]:
                    # but it is full, error.
                    return False
            else:
                # not isolated (normal):
                if not( pf_values[self.ports[1]] or not(aa_values[self.get_fsm_stor()[-1]]) ):
                    return False
        # Port 1 can be excited only if the last reg is not empty.
        if pf_values[self.ports[1]]:
            # port 1 is excited
            if not(aa_values[self.get_fsm_stor()[-1]]):
                return False
        # ok
        return True

    def get_latmat(self, prti):
        """ Return latency matrix relative to the port index prti. """
        lm = len(self.ports) * [None]
        prti_inf = self.ports[prti].is_inflow()
        for pi in range(0, len(self.ports)):
            if self.ports[pi].is_inflow() != prti_inf:
                # input-to-output or output-to-input
                if prti_inf:
                    lm[pi] = self.ndelay    # input-to-output
                else:
                    lm[pi] = -self.ndelay   # output-to-input -> negative latency :)
        return lm


class Cell(DICell):
    """ A storage element. """
    
    def __init__(self, nm, dtype = None, ndelay=1, isol=False):
        DICell.__init__(self, nm, ndelay, isol, dtype)

    def is_full(self):
        return self.is_full_tail()


class DCell(DICell):
    """ A storage element. """
    
    def __init__(self, nm, ndelay, dtype=None, isol=False):
        DICell.__init__(self, nm, ndelay, isol, dtype)

    # def is_full(self):
    #     return self.is_full_tail()


class ICell(DICell):
    """ A storage element. """
    
    def __init__(self, nm, dtype=None, ndelay=1, isol=True):
        DICell.__init__(self, nm, ndelay, isol, dtype)

    def is_full(self):
        return self.is_full_tail()


class Drain(Element):
    """ Drains any input out. """
    def __init__(self, nm):
        Element.__init__(self, nm)
        self.ports = [PipeInflow(self, 0)]
    
    def constr_eqs(self):
        # pipe 0 input, always ready
        # self.ports[0].get_aR().set_eqdef(True)
        # eqs = [self.ports[0].get_R_core()]
        eqs = [self.ports[0].get_F_core()]
        return eqs


class Stopper(Element):
    """ Drains any input out. """
    def __init__(self, nm):
        Element.__init__(self, nm)
        self.ports = [PipeInflow(self, 0)]
    
    def constr_eqs(self):
        # pipe 0 input, always ready
        # self.ports[0].get_aR().set_eqdef(False)
        # eqs = [self.ports[0].get_R_core()]
        self.ports[0].get_F_core().wand_add(False)
        eqs = [self.ports[0].get_F_core()]
        return eqs

    def verify_consistency(self, pf_values, aa_values):
        """ Verify that the input/output pipes, whose state is in
            pf_values, are consistent with the FTL rules of the element. """
        # Stopper's pipe is never excited
        return (not(pf_values[self.ports[0]]))


class Source(Element):
    """ Sources P. """
    def __init__(self, nm, dtype = None, fun = None):
        Element.__init__(self, nm)
        self.ports = [PipeOutflow(self, 0, dtype=dtype)]
        self.fun = fun
    
    def constr_eqs(self):
        # pipe 0 output, always present
        # self.ports[0].get_aP().set_eqdef(True)
        # omg:
        if type(self.fun) is str:
            self.ports[0].get_aD().set_eqdef(
                NAp(self.fun, [] ) )
        else:
            self.ports[0].get_aD().set_eqdef( self.fun )
        eqs = [self.ports[0].get_F_core(), self.ports[0].get_D_core()]
        return eqs


class Drought(Element):
    """ Sources P. """
    def __init__(self, nm, dtype = None):
        Element.__init__(self, nm)
        self.ports = [PipeOutflow(self, 0)]
    
    def constr_eqs(self):
        # pipe 0 output, always present
        self.ports[0].get_F_core().wand_add(False)
        eqs = [self.ports[0].get_F_core()]
        return eqs

    def verify_consistency(self, pf_values, aa_values):
        """ Verify that the input/output pipes, whose state is in
            pf_values, are consistent with the FTL rules of the element. """
        # Drought's pipe is never excited
        return (not(pf_values[self.ports[0]]))


class Let_Raw(Element):
    def __init__(self, nm, dtype, d_eq):
        Element.__init__(self, nm)
        self.ports = [PipeInflow(self, 0), PipeOutflow(self, 1, dtype=dtype)]
        self.d_eq = d_eq

    def set_d_eq(self, d_eq):
        self.d_eq = d_eq

    def constr_eqs(self):
        # pipe 0 input, pipe 1 output
        self.ports[1].get_aD().set_eqdef( self.d_eq );
        self.ports[1].get_D_core().set_allow_subst(False)
        self.ports[1].get_F_core().wand_add( NId(self.ports[0].get_F_core()) )
        self.ports[0].get_F_core().wand_add( NId(self.ports[1].get_F_core()) )
        return [self.ports[1].get_D_core(), self.ports[1].get_F_core(),
                self.ports[0].get_F_core()]

class Let(Let_Raw):
    def __init__(self, nm, dtype, fun, funf=True):
        Let_Raw.__init__(self, nm, dtype, None)
        if funf:
            self.set_d_eq( NAp(fun, [NId(self.ports[0].get_D_core()),
                                 NPrf(Prf.NOFOLLOW, [NId(self.ports[0].get_F_core())] ) ] ) )
        else:
            self.set_d_eq( NAp(fun, [NId(self.ports[0].get_D_core())] ) )

    
def full(cell):
    return cell.is_full()

def full_body(mlcell):
    return mlcell.is_full_body()


class Gate(Element):
    """ A pipe with a gating wire input. """
    def __init__(self, nm, gt=True, dtype=None):
        Element.__init__(self, nm)
        self.ports = [PipeInflow(self, 0, dtype=dtype), PipeOutflow(self, 1, dtype=dtype)]
        self.ports[0].merge_stages(self.ports[1])
        self.gt_eq = gt

    def set_gate_eq(self, gt):
        self.gt_eq = gt

    def constr_eqs(self):
        # pipe 0 input, pipe 1 output
        self.ports[0].get_F_core().wand_add( NId(self.ports[1].get_F_core()) )
        self.ports[1].get_F_core().wand_add( [NId(self.ports[0].get_F_core()), self.gt_eq] )
        self.ports[1].get_aD().set_eqdef( NId(self.ports[0].get_D_core()) )
        return [self.ports[0].get_F_core(),
                self.ports[1].get_F_core(),
                self.ports[1].get_D_core()]


class BufJoin(Element):
    """ Auto-Buffered Join """
    def __init__(self, nm, n_ins = 2, dtype = None, fun = None, dls = None):
        # Join.__init__(self, nm, n_ins, dtype, fun)
        Element.__init__(self, nm)
        self.delays = n_ins * [None]
        self.ipipes = n_ins * [None]
        self.join = Join('{0}_join'.format(nm), n_ins, dtype, fun)
        self.ports = [self.join.ports[0]]   # output
        for i in range(0, n_ins):
            self.ipipes[i] = Pipe('{0}_ip{1}'.format(nm, i))
            self.ports.append(self.ipipes[i].ports[0])  # inports
        if dls:
            self.set_delays(dls)

    # def get_latmat(self, prti):
    #     """ Return latency matrix relative to the port index prti. """
    #     lm = len(self.ports) * [None]
    #     prti_inf = self.ports[prti].is_inflow()
    #     for pi in range(0, len(self.ports)):
    #         if self.ports[pi].is_inflow() != prti_inf:
    #             # input-to-output or output-to-input
    #             if prti_inf:
    #                 lm[pi] = self.delays[prti_inf]    # input-to-output
    #             else:
    #                 lm[pi] = -self.delays[pi]   # output-to-input -> negative latency :)
    #     return lm

    def expand(self):
        """ Expand the element into sub-elements, if needed. """
        # has the delays been set?
        if None in self.delays:
            self.balance_to_common(self.find_common())
        # expand
        ee = [self.join]
        ee.extend(self.ipipes)
        # iterate over input pipe indexes
        for i in range(0, len(self.ports)-1):
            # the delay requested for the input pipe ip
            d = self.delays[i]
            ip = self.ipipes[i]
            # add delay 'd' to the input port p at i
            if (d is not None) and (d > 0):
                DC = DCell(self.get_name()+'_dcell{0}'.format(i), d)
                ee.append(DC)
                DC << ip/1
                self.join << DC/1
            else:
                # no delay for the pipe
                self.join << ip/1
        return ee

    def set_delays(self, dls):
        assert len(dls) == len(self.ports)-1, "Required {0} delay values, given {1}".format(
            len(self.ports)-1, len(dls))
        self.delays = dls

    def give_latency_to_com(self, p, com):
        """ Recursively compute latency pro PipeInflow p to an element com. """
        # p should be PipeInflow
        assert p.is_inflow()
        p = p.get_outp()        # to the output port
        assert p.is_outflow()
        # get the element and port index the output pipe is connected to.
        elm, prt_idx = p.get_elmport()
        if elm == com:
            return 0
        lmat = elm.get_latmat(prt_idx)
        print('    elm={0}, prt_idx={1}: lm={2}'.format(elm, prt_idx, lmat))
        max_lat = 0
        for i in range(0, len(lmat)):
            if lmat[i] is None: continue
            lat = self.give_latency_to_com(elm.get_port(i), com)
            max_lat = max(max_lat, lat+(-lmat[i]))
        return max_lat


    def balance_to_common(self, com):
        """ Balance delays to the common ancestor element com. """
        # find a path from self.ipipes[i] to com
        nlats = []
        print('BufJoin {0}: Balancing to {1}'.format(self, com))
        for ip in self.ipipes:
            # find a path from ip to com, determine its latency.
            p = ip/0
            print('  Computing latency from {0} to {1}'.format(p, com))
            lat = self.give_latency_to_com(p, com)
            print('  is {0}'.format(lat))
            nlats.append(lat)

        max_lat = max(nlats)
        dls = []
        for nl in nlats:
            dls.append(max_lat - nl)
        print('BufJoin {0} balanced: nlats={1} => dls={2}'.format(self, nlats, dls))
        self.set_delays(dls)


    def find_common(self):
        """ Find the nearest common upstream Element.
            Uses Breadth-First Search of the FTL graph, starts at the BufJoin's input pipes
            and goes upstream. Marks the visited nodes with a set of ints that indicate which
            of the original BufJoin's input pipes can reach the node. Stops when a node
            with a full marking is found.
        """
        # visited elements
        vis_elms = dict()       # dict Element -> (set() of int)
        # insert our input pipes
        for i in range(0, len(self.ipipes)):
            vis_elms[self.ipipes[i]] = frozenset([i])
        # target marking:
        full_house = frozenset(range(0, len(self.ipipes)))
        # FIFO of the current elements; insert our input pipes
        act_elms = deque(self.ipipes)
        print('BufJoin {0}: Finding common element; vis_elms={1}, act_elms={2}'.format(self, vis_elms, act_elms))

        while act_elms:
            # get an element from the FIFO
            e = act_elms.popleft()
            ve = vis_elms[e]
            assert ve is not None
            # for all its input ports of the element:
            for ein_p in e.get_in_ports():
                # the output port accross the input
                eout_p = ein_p.get_outp()
                if eout_p is None: continue
                # e2 is the Element the output port belongs to.
                e2, e2_p = eout_p.get_elmport()
                # has e2 been visited?
                if e2 not in vis_elms:
                    # totally new element -> inherit the current marking and push on the queue
                    vis_elms[e2] = ve
                    act_elms.append(e2)
                else:
                    # already known elem. Merge the markings.
                    ve2_old = vis_elms[e2]
                    ve2 = ve2_old | ve
                    # has the marking converged?
                    if ve2 == full_house:
                        # found the common!
                        print('  Found: {0}'.format(e2))
                        return e2
                    if ve2 != ve2_old:
                        # marking for the Element e2 has changes; update and re-queue the elem.
                        vis_elms[e2] = ve2
                        act_elms.append(e2)

        assert False, 'Could not find a common upstream element!'
        return None
