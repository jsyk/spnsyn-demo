from ftl.ast import *
from ftl.attrs import Attrib, AttrKind
from ftl.atrav import PrintTrav
from ftl.atrav_cg import PrintAsVhdlTrav
import ftl.types as types
import ftl.names as names
import functools
import sys


class Stage:
    """
    Pipeline stage.
    """
    ## Class variables:
    # this is for assigning unique ids to stages
    __maxid__ = 0
    # enums for Pipe.stage_bound
    INTRA = 0       # the pipe is internal to the stage
    I_BOUND = 1     # the pipe is at the input boundary
    O_BOUND = 2     # the pipe is at the output boundary

    def __init__(self, initial):
        # set of pipes in this stage
        self.pipes = set([initial])
        Stage.__maxid__ += 1
        # a unique id of the Stage
        self.id = Stage.__maxid__
        # input boundary, set of PipeOutflow pipes that come in
        # into the Stage, and of PipeInflow pipes that connect
        # to the external world (module iface)
        self.ibound = set([])
        # output boundary
        self.obound = set([])
        # print 'Created Stage {0} for pipe {1}'.format(self.id, str(initial))

    def add_i_bound(self, p):
        """ Add the port p into the set of input boundary pipes.
            Also set a flag in the pipe. """
        self.ibound.add(p)
        p.set_stage_bound(Stage.I_BOUND)

    def add_o_bound(self, p):
        """ Add the port p into the set of output boundary pipes.
            Also set a flag in the pipe. """
        self.obound.add(p)
        p.set_stage_bound(Stage.O_BOUND)

    def merge(self, o_stage):
        assert self is not o_stage
        # iterate over the pipes in the other stage
        for op in o_stage.pipes:
            # and change their stage to ours
            op.stage = self
        # merge the set of pipes in the other stage into ours
        self.pipes |= o_stage.pipes
        self.ibound |= o_stage.ibound
        self.obound |= o_stage.obound
        o_stage.pipes.clear()
        o_stage.ibound.clear()
        o_stage.obound.clear()


    def check_stage_acyclic(self):
        """ Check that the stage is acyclic, using DFS. """
        for ib in self.ibound:
            self.dfs_acyclic(ib, [])
        print( 'Stage {0} checked to be data-flow acyclic.'.format(self.id))


    def dfs_acyclic(self, current, visited):
        """ Internal DFS traversal to check that the stage is acyclic """
        if current in visited:
            s_visited = functools.reduce(lambda x,y: ('{0}->{1}'.format(x, y)), visited)
            print( 'ERROR: Piping loop in stage {0} going through {1} --> {2}.'.format(
                            self.id, s_visited, current))
            sys.exit(1)
        # must not modify the original 'visited' list
        new_visited = []
        new_visited.extend(visited)
        new_visited.append(current)
        next = current.give_continuations(self)
        for n in next:
            assert n is not None
            self.dfs_acyclic(n, new_visited)


class ModWirePort:
    """ Wire port in module. """
    OUT = 'out'
    IN  = 'in'

    def __init__(self, dire, name, ideq):
        assert isinstance(ideq, NId)
        self.dir = dire
        self.name = name
        self.eq = ideq

    def vhdl_print_wireport(self):
        tp = PrintAsVhdlTrav().run_on(self.eq.get_ref().get_actype())
        sl = [ '{0} : {1} {2}'.format(self.name, self.dir, tp) ]
        return sl

    def vhdl_print_assign_wireport(self):
        if self.dir == ModWirePort.IN:
            sl = ['{0} <= {1};'.format(self.eq.get_ref().get_name(), self.name)]
        else:
            sl = ['{0} <= {1};'.format(self.name, self.eq.get_ref().get_name())]
        return sl

    def vhdl_print_instance_port(self):
        sl = [(' '*4)+'{0} => {1},'.format(self.name, PrintAsVhdlTrav().run_on(self.eq))]
        return sl

    def get_eq(self):
        return self.eq.get_ref()


class CgInstance:
    """ Codegen: component instance """
    def __init__(self, mod, iname, cname):
        self.mod = mod          # module (Compiler)
        self.iname = iname      # instance name
        self.cname = cname      # component name
        self.wireports = []
        self.genmap = dict()

    def add_port_to(self, pname, eqval):
        """ Add new port named 'pname', input to the instance, driven by eqval. """
        # an attribute through which the output signal is routed
        at = Attrib(names.give('ow_{0}_{1}'.format(self.iname, pname)), None)
        if eqval:
            at.set_eqdef(eqval)
        self.mod.add_eqs([at])
        at.get_core().mark_as_necessary()
        # create the wire port of the instance
        wp = ModWirePort(ModWirePort.IN, pname, NId(at.get_core()))
        self.wireports.append(wp)
        return at.get_core()

    def add_port_from(self, pname, dtype):
        at = Attrib(names.give('iw_{0}_{1}'.format(self.iname, pname)), dtype)
        # self.mod.add_eqs([at])
        at.get_core().mark_as_necessary()
        at.get_core().set_allow_subst(False)
        # create the wire port of the instance
        wp = ModWirePort(ModWirePort.OUT, pname, NId(at.get_core()))
        self.wireports.append(wp)
        return at.get_core()

    def add_genmap(self, gm):
        self.genmap.update(gm)

    def vhdl_print_instantiation(self):
        sl = ['{0} : {1}'.format(self.iname, self.cname)]
        if len(self.genmap) > 0:
            sl.append('generic map (')
            j = 0
            for k in self.genmap.keys():
                j += 1
                if j < len(self.genmap):
                    comma = ','
                else:
                    comma = ''
                sl.append((' '*4)+'{0} => {1}{2}'.format(k, self.genmap[k], comma))
            sl.append(')')

        sl.append('port map (')
        for wp in self.wireports:
            sl.extend(wp.vhdl_print_instance_port())
        sl.append((' '*4)+'clk => clk, rst => rst')
        sl.append(');')
        sl.append('')
        return sl


class PipeBase:
    """
    A base class for pipe heads and tails.
    They are also used for element ports.
    """
    
    def __init__(self, elm, idx, nm = None, dtype = None):
        assert isinstance(elm, Element)
        assert type(idx) == int
        if nm is None:
            nm = elm.get_name()
        # the Element this pipe part belongs
        self.element = elm
        # the port index in the element
        self.prt_idx = idx
        # name of the port/pipe
        self.name = nm
        # the stage this pipe belongs to
        self.stage = Stage(self)
        # the P and R attributes of the pipe
        self.attr_F = Attrib('F%s%d' % (nm, idx), types.Bool_t, AttrKind.Flows)
        self.attr_F.set_eqdef( NPrf(Prf.AND, []) )
        self.attr_D = Attrib('D%s%d' % (nm, idx), dtype, AttrKind.Data)
        self.attr_FI = None       # driver for F, only in module ports
        # companions
        self.attr_D.get_core().set_companion(AttrKind.Flows, self.attr_F)
        # self.attr_D.set_companion(AttrKind.Ready, self.attr_R)
        # the type of boundary wrt stages
        self.stage_bound = Stage.INTRA

    def get_elmport(self): return (self.element, self.prt_idx)
    def get_aD(self): return self.attr_D
    def get_aF(self): return self.attr_F
    def get_aFI(self): return self.attr_FI
    def get_D_core(self): return self.attr_D.get_core()
    def get_F_core(self): return self.attr_F.get_core()
    def get_FI_core(self): return self.attr_FI.get_core()
    def get_stage(self):  return self.stage
    def get_stage_bound(self):  return self.stage_bound

    def rename(self, new_nm):
        self.name = new_nm
        self.attr_F.rename('F{0}{1}'.format(new_nm, self.prt_idx))
        self.attr_D.rename('D{0}{1}'.format(new_nm, self.prt_idx))

    def set_stage_bound(self, b):
        self.stage_bound = b
    
    def vhdl_print_modport__impl(self, drct, idrct):
        sl = ['{0}_P : {1} {2}'.format(self.element.get_name(), drct, PrintAsVhdlTrav().run_on(self.get_FP_core().get_actype())),
            '{0}_R : {1} {2}'.format(self.element.get_name(), idrct, PrintAsVhdlTrav().run_on(self.get_FR_core().get_actype())),
            '{0}_D : {1} {2}'.format(self.element.get_name(), drct, PrintAsVhdlTrav().run_on(self.get_D_core().get_actype())) ]
        return sl
    
    def mark_attribs_necessary(self):
        # self.get_P_core().mark_as_necessary()
        # self.get_R_core().mark_as_necessary()
        self.get_F_core().mark_as_necessary()
        self.get_D_core().mark_as_necessary()

    def merge_stages(self, other):
        """ Merge the stage of 'other' to self. """
        if self.stage is not other.stage:
            # remember the other's stage
            o_stage = other.stage
            self.stage.merge(o_stage)
            # print 'merge_stages: merged into Stage {0}, emptied Stage {1}'.format(self.stage.id, o_stage.id)

    def __str__(self):
        return '{0}.{1}'.format(self.name, self.prt_idx) 


class PipeInflow(PipeBase):
    """ An input side of a pipe. """
    def __init__(self, elm, idx, nm = None, dtype = None):
        PipeBase.__init__(self, elm, idx, nm, dtype)
        # the output side this pipe takes from
        self.outp = None
        
    def con_to_output(self, p):
        assert self.outp is None, 'The input pipe mouth is already bound to an output!'
        # The corresponding output.
        self.outp = p
        self.attr_F.merge(self.outp.get_aF())
        self.attr_D.merge(self.outp.get_aD())

    def is_inflow(self): return True
    def is_outflow(self): return False
    def get_outp(self): return self.outp

    def get_FP_core(self): return self.get_FI_core()
    def get_FR_core(self): return self.get_F_core()

    def vhdl_print_modport(self):
        return self.vhdl_print_modport__impl('in ', 'out')
    
    def vhdl_print_assign_modport(self):
        sl = ['{0} <= {1}_P;'.format(self.get_FI_core().get_name(), self.element.get_name()),
            '{1}_R <= {0};'.format(self.get_F_core().get_name(), self.element.get_name()),
            '{0} <= {1}_D;'.format(self.get_D_core().get_name(), self.element.get_name())]
        return sl

    def give_continuations(self, stage = None):
        """ Construct a set of pipes that continue data flow after this one. """
        # this is an inflow-pipe, it is at the inputs of elements. Hence, data-flow
        # continues across the element at its output, unless the pipe
        # has been marked as a boundary of the stage.
        if self.stage_bound != Stage.O_BOUND:
            # i-bound or intra are allowed
            # The following assert is fishy, it is not correct for a module input port directly connected to a Cell input.
            assert self not in self.stage.obound, 'PipeInflow({0}): input port is an output stage boundary!'.format(str(self))
            ops = self.element.get_out_ports()
            if stage is not None:
                ops = filter(lambda x: (x.get_stage() is stage), ops)
            return ops
        else:
            assert self.stage_bound == Stage.O_BOUND
            assert self in self.stage.obound
            return set([])

    def __lshift__(self, oup):
        """ Connect PipeOutflow oup to this input pipe. """
        assert self.get_outp() is None, 'In-pipe {0} is already bound to {1}, could not bind to {2}'.format(
            str(self), str(self.get_outp()), str(oup))
        connect_pipes(self, oup)



class PipeOutflow(PipeBase):
    """ Output-side of a pipe. """
    def __init__(self, elm, idx, nm = None, dtype = None):
        PipeBase.__init__(self, elm, idx, nm, dtype)
        self.inp = None
    
    def con_to_input(self, p):
        assert self.inp is None, 'The output pipe mouth is already bound to an input!'
        # The corresponding tail.
        self.inp = p
        # self.attr_P.merge(self.inp.get_aP())
        # self.attr_R.merge(self.inp.get_aR())
        self.attr_F.merge(self.inp.get_aF())
        self.attr_D.merge(self.inp.get_aD())
    
    def is_inflow(self): return False
    def is_outflow(self): return True
    
    def get_FP_core(self): return self.get_F_core()
    def get_FR_core(self): return self.get_FI_core()

    def vhdl_print_modport(self):
        return self.vhdl_print_modport__impl('out', 'in ')

    def vhdl_print_assign_modport(self):
        sl = ['{1}_P <= {0};'.format(self.get_F_core().get_name(), self.element.get_name()),
            '{0} <= {1}_R;'.format(self.get_FI_core().get_name(), self.element.get_name()),
            '{1}_D <= {0};'.format(self.get_D_core().get_name(), self.element.get_name())]
        return sl

    def give_continuations(self, stage = None):
        """ Construct a set of pipes that continue data flow after this one. """
        # this is an outflow-pipe, it is at the outputs of elements. Hence, data-flow
        # continues just at the input pipe.
        if self.inp is not None:
            assert self.stage_bound in [Stage.INTRA, Stage.I_BOUND], "PipeOutflow {0} has stage type {1}".format(
                self, self.stage_bound)
            return set([self.inp])
        else:
            assert self.stage_bound == Stage.O_BOUND, 'Dangling pipe output {0} (not connected to a module output port)'.format(
                self)
            return set([])


def connect_pipes(inp, outp):
    inp.con_to_output(outp)
    outp.con_to_input(inp)
    inp.merge_stages(outp)


class Element:
    def __init__(self, nm = ''):
        # the list (array) of ports of this element
        self.ports = []    # PipeInFlow, PipeOutFlow
        self.name = nm
    
    def __str__(self): return self.get_name()
    def __repr__(self): return self.get_name()
    def get_name(self): return self.name
    def get_fsm_stor(self): return []
    def rename(self, newname):
        self.name = newname
        for p in self.ports:
            p.rename(newname)
    
    def find_unbound_in(self):
        """ Return the first unbound input port. """
        for p in self.ports:
            if p.is_inflow() and p.get_outp() is None:
                return p
        assert False, 'All in-ports in "{0}" already bound! (there are {1} in-ports, {2} out-ports)'.format(
            self.get_name(), len(list(self.get_in_ports())), len(list(self.get_out_ports())))
        return None
        
    def get_port(self, x):
        """ Get port x, given as an integer or name. """
        if type(x) == int:
            assert (x >= 0) and (x < len(self.ports))
            return self.ports[x]
        else:
            if type(x) == string:
                for p in self.ports:
                    if p.get_name() == x:
                        return p
            else:
                assert False, 'Unknown port select type!'

    def get_in_ports(self):
        """ Return a set of input ports of this element. """
        return filter(lambda x: (x.is_inflow()), set(self.ports))

    def get_out_ports(self):
        """ Return a set of output ports of this element. """
        return filter(lambda x: (x.is_outflow()), set(self.ports))

    def get_all_ports(self):
        """ Return the list of all ports of this element. """
        return self.ports
    
    def prop_stages(self):
        """ Propagate stages. """
        # merge stages across all ports. This is a default implementation
        # for combinatorial (i.e. non-Cell) elements.
        s = self.ports[0]
        for p in self.ports:
            p.merge_stages(s)

    def get_stages(self):
        """ Return the set of stages this element is part of. """
        # create a set of all Stages in the local ports
        st = set([])
        for p in self.ports:
            st.add(p.get_stage())
        return st

    def expand(self):
        """ Expand the element into sub-elements, if needed. """
        return [self]
    
    def __truediv__(self, idx):     # for python3
        """ Port selection syntax: e.g. X/2 """
        return self.get_port(idx)
        
    def __div__(self, idx):         # for python2
        """ Port selection syntax: e.g. X/2 """
        return self.get_port(idx)

    def __lshift__(self, other):
        """ Port connection syntax: X << [A/1, B/2]
            or: X << (A/1) << B/2
            It finds a first unbound input (tail) pipe
            and connects it to the given head pipe.
        """
        # FIXME: isinstance() is ugly
        if isinstance(other, list):
            for k in other:
                self << k
            return self
        else:
            if isinstance(other, PipeOutflow):
                k = self.find_unbound_in()
                connect_pipes(k, other)
                return self
            else:
                if isinstance(other, Pipe):
                    k = self.find_unbound_in()
                    connect_pipes(k, other.ports[1])
                    return self
                else:
                    if isinstance(other, PipeInflow):
                        assert False, 'Cannot connect to an input pipe!'
                    assert False, 'Unknown type: %s' % type(other)

    def verify_consistency(self, pf_values, aa_values):
        """ Verify that the input/output pipes, whose state is in
            pf_values, are consistent with the FTL rules of the element. """
        # By default, assume a combinatorial element.
        # The state of all pipes must be the same, i.e. either all flow, or none.
        p0f = pf_values[self.ports[0]]
        for p in self.ports[1:]:
            if not(p0f == pf_values[p]):
                return False
        return True

    def get_latmat(self, prti):
        """ Return latency matrix relative to the port index prti.
            Default impl: fully combinatorial Element. """
        lm = len(self.ports) * [None]
        for pi in range(0, len(self.ports)):
            if self.ports[pi].is_inflow() != self.ports[prti].is_inflow():
                # input-to-output or output-to-input -> zero latency in comb. elements.
                lm[pi] = 0
        return lm

    def is_swisel(self): return False       # v2


class Pipe(Element):
    """ This is actually a pipe element. """
    def __init__(self, nm, dtype = None):
        Element.__init__(self, nm)
        self.ports = [PipeInflow(self, 0, dtype=dtype), PipeOutflow(self, 1, dtype=dtype)]
        self.ports[0].merge_stages(self.ports[1])

    def constr_eqs(self):
        # pipe 0 input, 1 output
        # self.ports[0].get_aR().set_eqdef(self.ports[1].get_R_core())
        # self.ports[1].get_aP().set_eqdef(self.ports[0].get_P_core())
        self.ports[0].get_F_core().wand_add( NId(self.ports[1].get_F_core()) )
        self.ports[1].get_F_core().wand_add( NId(self.ports[0].get_F_core()) )
        self.ports[1].get_aD().set_eqdef( NId(self.ports[0].get_D_core()) )
        return [self.ports[0].get_F_core(),
                self.ports[1].get_F_core(),
                self.ports[1].get_D_core()]

    def get_F_core(self):
        return self.ports[0].get_F_core()
    
    def get_aD(self):
        return self.ports[0].get_aD()


def data(pipe):
    return NId(pipe.get_D_core())

def flows(pipe):
    return NId(pipe.get_F_core())

