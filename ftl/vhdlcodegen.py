from ftl.ast import *
from ftl.atrav import ComputeHashesTrav, CompareTrav
from ftl.atrav_cg import PrintAsVhdlTrav, ZeroConstTypeTrav
from ftl.attrs import AttrKind


class VhdlCodeGen:
    """ VHDL code generator/printer. """

    def __init__(self, comp):
        """ Init the code generator for the Compiler comp """
        self.comp = comp
        self.vhdl_entity_name = None
        self.vhdl_uses = []
        self.vhdl_libs = ['ftl']
        self.vhdl_clk_name = 'clk'
        self.vhdl_rst_name = 'rst'
        self.vhdl_generics = []
        # OPTIMIZATION: do not reset data in FF to undefined when the reg is empty
        self.opt_noundef_ffdata = False

    def vhdl_print_modports(self):
        sl = []
        # pipe ports
        for mp in self.comp.all_modports:
            sl.extend(mp.vhdl_print_modport())
        # wire ports
        for wp in self.comp.all_modwireports:
            sl.extend(wp.vhdl_print_wireport())
        return sl
    
    
    def vhdl_prints_sigdefs(self):
        """ Print the definitions of all signals in the VHDL format. """
        sl = ['-- Undefined attributes (assuming inputs):']
        for eq in self.comp.all_undefs:
            if eq.is_necessary() and eq.get_ackind() not in [AttrKind.Const]:
                tpvhd = PrintAsVhdlTrav().run_on(eq.get_actype())
                sl.append(('signal {0} : {1};'.format(eq.get_name(), tpvhd)))
        sl.append('')
        sl.append('-- Defined attributes:')
        for eq in self.comp.all_eqs + self.comp.all_ffs:
            if eq.is_necessary():
                tpvhd = PrintAsVhdlTrav().run_on(eq.get_actype())
                sl.append(('signal {0} : {1};'.format(eq.get_name(), tpvhd)))
        return sl

    def do_print_mpx(self, sl, eq, eqd):
        ivars = GatherUsedVarsTrav().run_on(eqd)
        sl.append('MPX_{0}: process ({1}) is'.format(eq.get_name(), joinlist_notrail(ivars, ', ')))
        sl.append('begin')
        sl.append('    case {0} is'.format( PrintAsVhdlTrav().run_on(eqd.get_args()[0])) )
        for k in range(1, len(eqd.get_args())):
            sl.append('        when {0} => {1} <= {2};'.format(k-1, 
                eq.get_name(),
                PrintAsVhdlTrav().run_on(eqd.get_args()[k])) )

        undef_const = ZeroConstTypeTrav().run_on(eq.get_actype())
        sl.append('        when others => {0} <= UNDEF_{1};'.format(
            eq.get_name(), undef_const) )
        sl.append('    end case;')
        sl.append('end process;')    
    
    def vhdl_prints_eqs(self):
        """ Print the combinatorial equations in the VHDL form. """
        sl = []
        for eq in self.comp.all_eqs:
            if eq.is_necessary():
                eqd = eq.get_eqdef()
                sl.append('')
                tpvhd = PrintAsVhdlTrav().run_on(eq.get_actype())
                sl.append('-- {0} : {1}'.format(eq.get_name(), tpvhd))
                if isinstance(eqd, NPrf) and eqd.get_prf() == Prf.MPX:
                    # print MPX process
                    self.do_print_mpx(sl, eq, eqd)
                else:
                    # print normal assignment
                    sl.append('{0} <= {1};'.format(eq.get_name(), PrintAsVhdlTrav().run_on(eqd)))
        return sl

    
    def ff_print_updbody(self, eq, newval, pre, ins, post):
        sl = []
        sl.append('            {0}'.format(pre))
        sl.append('            {0}{1} <= {2};'.format(ins, eq.get_name(), PrintAsVhdlTrav().run_on(newval)))
        
        if eq.get_ackind() == AttrKind.Data:
            # companion Present attribute
            dt_p_eq = eq.get_companion(AttrKind.Present).get_core()
            assert isinstance(dt_p_eq.get_eqdef(), NPrf)
            assert dt_p_eq.get_eqdef().get_prf() == Prf.FF
            sl.append('            {0}-- Present: {1}'.format(ins, dt_p_eq.get_name()))
            # dt_p_newval is the new value of the Present companion
            # FIXME: assuming the register enable signal is the same!!
            dt_p_newval = dt_p_eq.get_eqdef().get_args()[0]
            undef_const = ZeroConstTypeTrav().run_on(eq.get_actype())
            # emit code to set the data value to undef when the Valid bit is false
            if not self.opt_noundef_ffdata:
                sl.append('            {0}-- synthesis translate_off'.format(ins))
                sl.append('            {0}if not to_bool({1}) then'.format(ins,
                            PrintAsVhdlTrav().run_on(dt_p_newval)))
                sl.append('                {0}{1} <= UNDEF_{2};'.format(ins, eq.get_name(), undef_const))
                sl.append('            {0}end if;'.format(ins))
                sl.append('            {0}-- synthesis translate_on'.format(ins))

        if post is not None:
            sl.append('            {0}'.format(post))

        return sl


    def vhdl_prints_ffs(self, clk_name = 'clk', rst_name = 'rst'):
        """ Print the flip-flop equations in the VHDL format. """
        sl = []
        # flip-flop
        sl.append('all_ffs: process ({0}) is'.format(clk_name))
        sl.append('begin')
        sl.append('    if rising_edge({0}) then'.format(clk_name))
        sl.append('        if to_bool({0}) then'.format(rst_name))

        # Generate RESETs
        for eq in self.comp.all_ffs:
            if not eq.is_necessary():
                continue
            # The eq FF is necessary.
            eqd = eq.get_eqdef()
            assert isinstance(eqd, NPrf) and eqd.get_prf() == Prf.FF
            a_ini = eqd.get_args()[2]      # init value after reset
            
            # Data regs do not need to reset iff the associated Valid bit is False after reset.
            pre = ''
            if eq.get_ackind() == AttrKind.Data:
                # the eq is a data register. The v_eq is the associated Validity-bit FF
                v_eq = eq.get_companion(AttrKind.Present).get_core()
                v_eqd = v_eq.get_eqdef()
                assert isinstance(v_eqd, NPrf) and v_eqd.get_prf() == Prf.FF
                v_ini = v_eqd.args()[2]     # init value of the Valid bit after the reset
                if v_ini is False:
                    # the Cell is initially empty.
                    pre = '-- '

            if isinstance(a_ini, NPrf) and a_ini.get_prf() == Prf.ZERO_CONST_TP:
                zero_const = ZeroConstTypeTrav().run_on(eq.get_actype())
                sl.append('            {2}{0} <= ZERO_{1};'.format(eq.get_name(), zero_const, pre))
            else:
                sl.append('            {2}{0} <= {1};'.format(eq.get_name(), PrintAsVhdlTrav().run_on(a_ini), pre ))

        sl.append('        else')
        # Generate UPDATEs
        
        cndffs = []     # FFs with real non-trivial conditions.
        for eq in self.comp.all_ffs:
            if not eq.is_necessary():
                continue
            # The eq is a necessary FF.
            eqd = eq.get_eqdef()
            cond = eqd.get_args()[1]
            newval = eqd.get_args()[0]

            if cond == True:
                pre = '-- {0} is always written:'.format(eq.get_name())
                ins = ''
                post = None
            else:
                if cond == False:
                    pre = '-- WARNING: {0} is never written:'.format(eq.get_name())
                    ins = '-- '
                    post = None
                else:
                    # non-trivial condition; will handle later
                    ComputeHashesTrav().run_on(cond)
                    cndffs.append(eq)
                    continue  # later
            
            sl.extend(self.ff_print_updbody(eq, newval, pre, ins, post))

        while cndffs:
            eq = cndffs.pop()
            eqd = eq.get_eqdef()
            cond = eqd.get_args()[1]
            newval = eqd.get_args()[0]
            
            pre = 'if to_bool({0}) then'.format(PrintAsVhdlTrav().run_on(cond))
            ins = '    '
            # post = 'end if;'

            sl.extend(self.ff_print_updbody(eq, newval, pre, ins, None))

            # try finding another ff with identical condition.
            h = nhash(cond)
            more = []
            for eq2 in cndffs:
                eqd2 = eq2.get_eqdef()
                cond2 = eqd2.get_args()[1]
                if h != nhash(cond2):
                    continue
                # hashes match, check trees.
                if not CompareTrav().run_on(cond, cond2):
                    continue
                # trees match.
                more.append(eq2)

            for eq3 in more:
                eqd3 = eq3.get_eqdef()
                newval3 = eqd3.get_args()[0]
                sl.extend(self.ff_print_updbody(eq3, newval3, '-- cond. chained:', ins, None))

            sl.append('            {0}'.format('end if;'))
            more = set(more)
            cndffs = list(filter(lambda x: x not in more, cndffs))


        sl.append('        end if;')
        sl.append('    end if;')
        sl.append('end process;')
        return sl
    
    
    def vhdl_print_entity_decl_impl(self, entname, kind):
        sl = ['{0} {1} is'.format(kind, entname)]
        if len(self.vhdl_generics) > 0:
            sl.append('generic (')
            j = 0
            for g in self.vhdl_generics:
                j += 1
                if j < len(self.vhdl_generics):
                    comma = ';'
                else:
                    comma = ''
                sl.append('    {0}{1}'.format(g, comma))
            sl.append(');')
        sl.append('port (')
        sl.append('    clk : in  std_ulogic;')
        sl.append('    rst : in  std_ulogic;')
        mps = self.vhdl_print_modports()
        for imp in range(0, len(mps)):
            mp = mps[imp]
            if imp < len(mps)-1:
                sl.append('    ' + mp + ';')
            else:
                sl.append('    ' + mp)
        sl.extend( [');', 'end {0};'.format(kind)] )
        return sl
    
    def vhdl_print_entity_decl(self, entname):
        return self.vhdl_print_entity_decl_impl(entname, 'entity')
    
    def vhdl_print_component_decl(self, entname):
        return self.vhdl_print_entity_decl_impl(entname, 'component')
    
    def vhdl_print_assigns_modports(self):
        sl = ['-- I/O assignments:']
        # pipe ports
        for mt in self.comp.all_modports:
            sl.extend(mt.vhdl_print_assign_modport())
        # wire ports
        for wp in self.comp.all_modwireports:
            sl.extend(wp.vhdl_print_assign_wireport())
        sl.append('')
        return sl
    
    
    def vhdl_set_props(self, entity_name=None, uses=None, libs=None, generics=None):
        if entity_name is not None:
            self.vhdl_entity_name = entity_name
        if uses is not None:
            self.vhdl_uses = uses
        if libs is not None:
            self.vhdl_libs = libs
        if generics:
            self.vhdl_generics = generics
    
    def vhdl_print_uselibs(self):
        sl = ['library ieee;',
            'use ieee.std_logic_1164.all;',
            'use ieee.numeric_std.all;']
        for lb in self.vhdl_libs:
            sl.append('library {0};'.format(lb))
        sl.append('use {0}.ftlbase.all;'.format(self.vhdl_libs[0]))
        for use in self.vhdl_uses:
            sl.append('use {0};'.format(use))
        sl.append('')
        return sl

    def vhdl_print_cginstances(self):
        sl = ['-- code-gen (blackbox) instances ({0})'.format(len(self.comp.all_cgi))]
        for cgi in self.comp.all_cgi:
            # cgi is instance of CgInstance
            sl.extend(cgi.vhdl_print_instantiation())
        return sl

    def vhdl_print(self):
        # return ['--not working']
        sl = []
        sl.extend(self.vhdl_print_uselibs())
        sl.extend(['package comp_{0} is'.format(self.vhdl_entity_name)])
        sl.extend(self.vhdl_print_component_decl(self.vhdl_entity_name))
        sl.extend(['end package;'])
        sl.append('')
        sl.append('')
        sl.extend(self.vhdl_print_uselibs())
        sl.extend(self.vhdl_print_entity_decl(self.vhdl_entity_name))
        sl.append('')
        sl.extend(['architecture rtl of {0} is'.format(self.vhdl_entity_name)])
        sl.extend(self.vhdl_prints_sigdefs())
        sl.extend(['', 'begin', ''])
        sl.extend(self.vhdl_print_assigns_modports())
        sl.extend(self.vhdl_print_cginstances())
        sl.extend(self.vhdl_prints_eqs())
        sl.append('')
        sl.extend(self.vhdl_prints_ffs(self.vhdl_clk_name, self.vhdl_rst_name))
        sl.extend(['end architecture rtl;'])
        return sl


def joinlist(sl, ch = "\n"):
    s = ''
    for se in sl:
        s += str(se) + ch
    return s

def joinlist_notrail(sl, ch = "\n"):
    s = ''
    for se in sl:
        if s != '':
            s += ch
        s += str(se)
    return s


