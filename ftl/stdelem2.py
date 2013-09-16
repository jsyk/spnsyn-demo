from ftl.stdelem0 import *

# SwiSelBase ---- SwiSelPri
#             |-- SwiSelCond
#             `-- SwiSelIdx
# 

class SwiSelBase:
    """ Common base for Switches and Selects. Handles control wands, because they are identical
        in Switches and Selects.
    """

    def is_swisel(self): return True

    def constr_eqs_ctrl(self):
        # new equations
        eqs = []
        # resolved condition firing wands, 1-hot encoded
        self.portcnd_fire = [None] * (len(self.ports)-1)
        for i in range(0, len(self.portcnd_fire)):
            self.portcnd_fire[i] = Attrib('F{0}_cnd{1}'.format(self.get_name(), i), types.Bool_t, AttrKind.Flows, eqd=True)
            p = self.ports[i+1]
            p.get_F_core().wand_add( NId(self.portcnd_fire[i].get_core()) )
            eqs.append( self.portcnd_fire[i].get_core() )
        # create list of all ports, indivudually wrapped in NId
        apw = []
        for p in self.ports:
            apw.append( NId(p.get_F_core()) )

        # Add Prf.SWISEL at all ports, with links to self, and port index.
        # The pattern will be expanded in compiler traversal.
        for i in range(0, len(self.ports)):
            p = self.ports[i]     # we need both the index and the port
            args = [NConst(self), i]
            args.extend( apw )
            # ... & @swisel(i, self, NId(p0), NId(p1), ...) & ...
            p.get_F_core().wand_add( NPrf(Prf.SWISEL, args) )
            eqs.append(p.get_F_core())

        return eqs


    def expand_pattern(self, wnds_w, wnds_r):
        """ Expand the swisel wand pattern into the graph. """
        # basic swisel
        # [0] &= OR([1], [2], ...)
        ed = map(lambda x: NId(x), wnds_r[1:])
        wnds_w[0].wand_add( NPrf(Prf.OR, list(ed)) )
        # 
        for i in range(1,len(wnds_w)):
            wnds_w[i].wand_add( NId(wnds_r[0]) )


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


class SwiSelPri(SwiSelBase):
    """ Control wands for priority Switch or Select """

    def constr_eqs_ctrl(self):
        eqs = SwiSelBase.constr_eqs_ctrl(self)
        for i in range(0, len(self.portcnd_fire)):
            p = self.ports[i+1]
            self.portcnd_fire[i].get_core().wand_add( NId(p.get_F_core()) )
        return eqs

    def expand_pattern(self, wnds_w, wnds_r):
        # expand the common pattern
        SwiSelBase.expand_pattern(self, wnds_w, wnds_r)

        # add priority
        prevneg = [ NPrf(Prf.NOT, [NId(wnds_r[1])]) ]
        for i in range(2, len(wnds_w)):
            wnds_w[i].wand_add( prevneg )
            prevneg.append( NPrf(Prf.NOT, [NId(wnds_r[i])]) )


class SwiSelCond(SwiSelBase):
    """ Control wands for Switch/Selects with external conditions. """
    def __init__(self):
        SwiSelBase.__init__(self)
        self.port_conds = []
        self.covered_ports = set([])

    def choose(self, iport, cond):
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
    
    def default_choice(self, iport):
        self.choose(iport, True)
        # set others to False
        self.others_never()
        return None
    
    def constr_eqs_ctrl(self):
        eqs = SwiSelBase.constr_eqs_ctrl(self)

        # inhibit all unbound conditions
        self.others_never()
        
        # input i.F &= cond & g_i,
        # g_{i+1} = g_i & !cond
        gi_1 = []
        for i in range(0, len(self.port_conds)):
            ip, cond = self.port_conds[i]
            assert cond is not None
            self.portcnd_fire[ip-1].get_core().wand_add( cond )
            self.portcnd_fire[ip-1].get_core().wand_add( gi_1 )
            # self.ports[ip].get_F_core().wand_add( cond )
            # self.ports[ip].get_F_core().wand_add( gi_1 )
            gi_1.append( NPrf(Prf.NOT, [cond]) )

        return eqs


class SwiSelIdx(SwiSelBase):
    """ Control wands for Switches/Selects with index condition. """
    def __init__(self):
        SwiSelBase.__init__(self)
        self.idx_cond = None

    def choose_index(self, idx_cond):
        self.idx_cond = idx_cond

    def constr_eqs_ctrl(self):
        eqs = SwiSelBase.constr_eqs_ctrl(self)
        # pipe 0 common, 1-n chosen from.
        for i in range(1, len(self.ports)):
            # self.select_from(i, NPrf(Prf.EQ, [self.idx_cond, i-1]) )
            # self.ports[i].get_F_core().wand_add( NPrf(Prf.EQ, [self.idx_cond, i-1]) )
            self.portcnd_fire[i-1].get_core().wand_add( NPrf(Prf.EQ, [self.idx_cond, i-1]) )
        return eqs



# ##############################################################################################

class SelectBase(Element):
    """ Selector chooses from several inputs to a single output. """
    def __init__(self, nm, n_ins):
        Element.__init__(self, nm)
        self.ports = [PipeOutflow(self, 0)]
        for i in range(0, n_ins):
            self.ports.append(PipeInflow(self, i+1))

    # def is_swisel(self): return True

    def constr_eqs_data(self):
        # DATA PATH
        eqs = []
        # output D
        dsel = None
        # construct the dsel expression tree from the bottom up,
        # hence we iterate in reverse (???)
        # for i in reversed(range(0, len(self.port_conds))):
        for ip in reversed(range(1, len(self.ports))):
            # ip, cond = self.port_conds[i]
            # cond = NId(self.ports[ip].get_F_core())
            cond = NId(self.portcnd_fire[ip-1].get_core())
            assert cond is not None
            if dsel is not None:
                # dsel = NPrf(Prf.COND, [ cond, NPrf(Prf.COLON, [NId(self.ports[ip].get_D_core()), dsel]) ])
                dsel = NPrf(Prf.COND, [ cond, NPrf(Prf.COLON, [NId(self.ports[ip].get_D_core()), dsel]) ])
            else:
                dsel = NId(self.ports[ip].get_D_core())

        assert dsel is not None
        self.ports[0].get_aD().set_eqdef(dsel)
        eqs.append(self.ports[0].get_D_core())
        
        return eqs




class Select_Cond(SwiSelCond, SelectBase):
    """ Selector chooses from several inputs to a single output. """

    def __init__(self, nm, n_ins = 2):
        SwiSelCond.__init__(self)
        SelectBase.__init__(self, nm, n_ins)
        # aliases
        self.select_from = self.choose
        self.default_from = self.default_choice
    
    def constr_eqs(self):
        eqs1 = SwiSelCond.constr_eqs_ctrl(self)
        eqs2 = SelectBase.constr_eqs_data(self)

        eqs1.extend(eqs2)
        return eqs1


class Select_Pri(SwiSelPri, SelectBase):
    """ Selector chooses from several inputs to a single output. """
    def __init__(self, nm, n_ins = 2):
        SwiSelPri.__init__(self)
        SelectBase.__init__(self, nm, n_ins)

    def constr_eqs(self):
        eqs1 = SwiSelPri.constr_eqs_ctrl(self)
        eqs2 = SelectBase.constr_eqs_data(self)
        eqs1.extend(eqs2)
        return eqs1
   

class Select_Idx(SwiSelIdx, SelectBase):
    """ Selector chooses based on a user index. """
    def __init__(self, nm, n_ins = 2):
        SwiSelIdx.__init__(self)
        SelectBase.__init__(self, nm, n_ins)
        self.select_index = self.choose_index

    def constr_eqs(self):
        eqs1 = SwiSelIdx.constr_eqs_ctrl(self)
        eqs2 = SelectBase.constr_eqs_data(self)
        eqs1.extend(eqs2)
        return eqs1


# #################################################################################

class SwitchBase(Element):
    """ Selector chooses from several inputs to a single output. """
    def __init__(self, nm, n_outs):
        Element.__init__(self, nm)
        self.ports = [PipeInflow(self, 0)]
        for i in range(0, n_outs):
            self.ports.append(PipeOutflow(self, i+1))


    def constr_eqs_data(self):
        eqs = []
        # output Di <= D0
        for i in range(1, len(self.ports)):
            self.ports[i].get_aD().set_eqdef( NId(self.ports[0].get_D_core()) )
            eqs.append( self.ports[i].get_D_core() )

        return eqs


class Switch_Pri(SwiSelPri, SwitchBase):
    """ Selector chooses from several inputs to a single output. """
    def __init__(self, nm, n_outs = 2):
        SwiSelPri.__init__(self)
        SwitchBase.__init__(self, nm, n_outs)

    def constr_eqs(self):
        eqs1 = SwiSelPri.constr_eqs_ctrl(self)
        eqs2 = SwitchBase.constr_eqs_data(self)
        eqs1.extend(eqs2)
        return eqs1


class Switch_Cond(SwiSelCond, SwitchBase):
    def __init__(self, nm, n_outs = 2):
        SwiSelCond.__init__(self)
        SwitchBase.__init__(self, nm, n_outs)
        # aliases
        self.switch_to = self.choose
        self.default_to = self.default_choice

    def constr_eqs(self):
        eqs1 = SwiSelCond.constr_eqs_ctrl(self)
        eqs2 = SwitchBase.constr_eqs_data(self)
        eqs1.extend(eqs2)
        return eqs1


class Switch_Idx(SwiSelIdx, SwitchBase):
    """ Switch chooses based on user index. """
    def __init__(self, nm, n_outs = 2):
        SwiSelIdx.__init__(self)
        SwitchBase.__init__(self, nm, n_outs)
        self.switch_index = self.choose_index

    def constr_eqs(self):
        eqs1 = SwiSelIdx.constr_eqs_ctrl(self)
        eqs2 = SwitchBase.constr_eqs_data(self)
        eqs1.extend(eqs2)
        return eqs1



# aliases
Select = Select_Cond
Switch = Switch_Cond
