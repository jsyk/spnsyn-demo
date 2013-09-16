from ftl.stdelem0 import *

class Select(Element):
    """ Selector chooses from several inputs to a single output. """
    
    def __init__(self, nm, n_ins = 2):
        Element.__init__(self, nm)
        self.port_conds = []
        self.covered_ports = set([])
        self.ports = [PipeOutflow(self, 0)]
        for i in range(0, n_ins):
            self.ports.append(PipeInflow(self, i+1))

    def select_from(self, iport, cond):
        #print iport, cond.get_name(), self.covered_ports
        assert iport > 0 and iport < len(self.ports)
        assert iport not in self.covered_ports
        self.port_conds.append((iport, cond))
        self.covered_ports.add(iport)
        return self
    
    def others_never(self):
        for i in range(1, len(self.ports)):
            if i not in self.covered_ports:
                self.select_from(i, False)
    
    def default_from(self, iport):
        self.select_from(iport, True)
        # set others to False
        self.others_never()
        return None
    
    def constr_eqs(self):
        # pipe 0 output, 1-n inputs
        self.others_never()
        eqs = []
        
        # output F &= ( OR all input F )
        inpF = []
        for p in self.ports[1:]:
            inpF.append( NId(p.get_F_core()) )
            eqs.append( p.get_F_core() )
        self.ports[0].get_F_core().wand_add( NPrf(Prf.OR, inpF) )
        eqs.append( self.ports[0].get_F_core() )

        # input i.F &= g_i & (output F)
        gi_1 = []
        for i in range(0, len(self.port_conds)):
            ip, cond = self.port_conds[i]
            assert cond is not None
            # gi = NPrf(Prf.AND, [cond, NId(self.ports[0].get_F_core())].extend(gi_1) )
            self.ports[ip].get_F_core().wand_add(
                [cond, NId(self.ports[0].get_F_core())] )
            self.ports[ip].get_F_core().wand_add( gi_1 )
            gi_1.append( NPrf(Prf.NOT, [cond]) )


        # output D
        dsel = None
        # construct the dsel expression tree from the bottom up,
        # hence we iterate in reverse
        for i in reversed(range(0, len(self.port_conds))):
            ip, cond = self.port_conds[i]
            assert cond is not None
            if dsel is not None:
                dsel = NPrf(Prf.COND, [ cond, NPrf(Prf.COLON, [NId(self.ports[ip].get_D_core()), dsel]) ])
                # dsel = ('?', cond, (':', NId(self.ports[ip].get_D_core()), dsel))
                #dsel = ('|', ('&', cond, self.ports[ip].get_D_core()), ('&', ('!', cond), dsel))
            else:
                dsel = NId(self.ports[ip].get_D_core())

        assert dsel is not None
        self.ports[0].get_aD().set_eqdef(dsel)
        eqs.append(self.ports[0].get_D_core())
        
        return eqs

    def verify_consistency(self, pf_values, aa_values):
        """ Verify that the input/output pipes, whose state is in
            pf_values, are consistent with the FTL rules of the element. """
        # If the port 0 is excited, exactly one of the other ports must be too.
        # If the port 0 is not excited, none of the other can be.
        # FIXME: this does not check the state of the condition!!
        #
        # count the number of active ports:
        cnt = 0
        for p in self.ports[1:]:
            if pf_values[p]:
                cnt += 1
        # check
        p0f = pf_values[self.ports[0]]
        if p0f:
            return (cnt == 1)
        else:
            return (cnt == 0)        


class Select_Pri(Select):
    """ Selector chooses from several inputs to a single output. """
    def __init__(self, nm, n_ins = 2):
        Select.__init__(self, nm, n_ins)
        for i in range(1, n_ins+1):
            self.select_from(i, NId(self.ports[i].get_F_core()) )
            # self.select_from(i, ('@@', 'phi', (',', self.ports[i].get_aP(), self.ports[i].get_aR())) )
    
    
class Select_Idx(Select):      #Element):
    """ Selector chooses based on a user index. """
    def __init__(self, nm, n_ins = 2):
        # Element.__init__(self, nm)
        Select.__init__(self, nm, n_ins)
        self.idx_cond = None
        # self.ports = [PipeOutflow(self, 0)]
        # for i in range(0, n_ins):
        #     self.ports.append(PipeInflow(self, i+1))

    def select_index(self, idx_cond):
        self.idx_cond = idx_cond

    def constr_eqs(self):
        # pipe 0 output, 1-n inputs
        for i in range(1, len(self.ports)):
            self.select_from(i, NPrf(Prf.EQ, [self.idx_cond, i-1]) )

        return Select.constr_eqs(self)


class Switch(Element):
    """ Switch chooses to several outputs, from a single input. """
    
    def __init__(self, nm, n_outs = 2):
        Element.__init__(self, nm)
        self.port_conds = []
        self.covered_ports = set([])
        self.ports = [PipeInflow(self, 0)]
        for i in range(0, n_outs):
            self.ports.append(PipeOutflow(self, i+1))
    
    def switch_to(self, iport, cond):
        assert iport > 0 and iport < len(self.ports)
        assert iport not in self.covered_ports
        self.port_conds.append((iport, cond))
        self.covered_ports.add(iport)
        return self
    
    def others_never(self):
        for i in range(1, len(self.ports)):
            if i not in self.covered_ports:
                self.switch_to(i, False)
    
    def default_to(self, iport):
        self.switch_to(iport, True)
        # set others to False
        self.others_never()
        return None
    
    def constr_eqs(self):
        # pipe 0 input, 1-n outputs
        self.others_never()
        eqs = []
        
        # input F &= ( OR all output F )
        outF = []
        for p in self.ports[1:]:
            outF.append( NId(p.get_F_core()) )
            eqs.append( p.get_F_core() )
        self.ports[0].get_F_core().wand_add( NPrf(Prf.OR, outF) )
        eqs.append( self.ports[0].get_F_core() )

        # output i.F &= g_i & (input F)
        gi_1 = []
        for i in range(0, len(self.port_conds)):
            ip, cond = self.port_conds[i]
            assert cond is not None
            # gi = NPrf(Prf.AND, [cond, NId(self.ports[0].get_F_core())].extend(gi_1) )
            self.ports[ip].get_F_core().wand_add(
                [cond, NId(self.ports[0].get_F_core())] )
            self.ports[ip].get_F_core().wand_add( gi_1 )
            gi_1.append( NPrf(Prf.NOT, [cond]) )

        # output Di <= D0
        for i in range(1, len(self.ports)):
            self.ports[i].get_aD().set_eqdef( NId(self.ports[0].get_D_core()) )
            eqs.append( self.ports[i].get_D_core() )
        
        return eqs

    def verify_consistency(self, pf_values, aa_values):
        """ Verify that the input/output pipes, whose state is in
            pf_values, are consistent with the FTL rules of the element. """
        # If the port 0 is excited, exactly one of the other ports must be too.
        # If the port 0 is not excited, none of the other can be.
        # FIXME: this does not check the state of the condition!!
        #
        # count the number of active ports:
        cnt = 0
        for p in self.ports[1:]:
            if pf_values[p]:
                cnt += 1
        # check
        p0f = pf_values[self.ports[0]]
        if p0f:
            return (cnt == 1)
        else:
            return (cnt == 0)        


class Switch_Pri(Switch):
    """ Switch chooses from several outputs from a single input. """
    def __init__(self, nm, n_outs = 2):
        Switch.__init__(self, nm, n_outs)
        #self.ports = [PipeInflow(self, 0)]
        for i in range(1, n_outs+1):
            self.switch_to(i, NId(self.ports[i].get_F_core()) )
            # self.switch_to(i, ('&', self.ports[i].get_aP(), self.ports[i].get_aR()) )
            # self.switch_to(i, ('@@', 'phi', (',', self.ports[i].get_aP(), self.ports[i].get_aR())) )


class Switch_Idx(Switch):   #Element):
    """ Switch chooses based on a user index. """
    def __init__(self, nm, n_outs = 2):
        #Element.__init__(self, nm)
        Switch.__init__(self, nm, n_outs)
        self.idx_cond = None
        # self.ports = [PipeInflow(self, 0)]
        # for i in range(0, n_outs):
        #     self.ports.append(PipeOutflow(self, i+1))

    def switch_index(self, idx_cond):
        self.idx_cond = idx_cond

    def constr_eqs(self):
        # pipe 0 output, 1-n inputs
        for i in range(1, len(self.ports)):
            self.switch_to(i, NPrf(Prf.EQ, [self.idx_cond, i-1]) )

        return Switch.constr_eqs(self)
