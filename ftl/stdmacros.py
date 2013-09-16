from ftl.stdelem2 import *
from ftl.atrav_cg import ZeroConstTypeTrav
from ftl.macro import MacroDef, MacroInst


# COUNTER
def create_counter_md(cnt_dtype, zero_cnt_const):
    Y = Pipe('Y', dtype=cnt_dtype) #out
    C = Cell('C', dtype=cnt_dtype)
    A = Source('A', dtype=cnt_dtype, fun=
        NPrf(Prf.COND, [
            C.is_full_tail(), NPrf(Prf.COLON, [
                NAp('minus', [C.data_tail()]),
                zero_cnt_const
            ])
        ]) )

    C << [A/0]
    Y << [C/1]
    return MacroDef('counter_md', [Y, C, A])
# /COUNTER


def create_sw_to_index(n_outs, dtype, itype):
    A = Pipe('A', dtype=dtype)
    I = Pipe('I', dtype=itype)
    # C = Pipe('C', dtype=dtype)
    J = Join('J', dtype=dtype, fun='@take_first')
    S = Switch_Idx('S', n_outs=n_outs)
    JI = Attrib('JI', types.Integer_t)
    # JI.set_eqdef( ('@', 'to_integer', (',', 
    #         ('@', 'unsigned', (',', (I/1).get_aD())) )))
    JI.set_eqdef( NAp('to_integer', [
            NAp('unsigned', [NId((I/1).get_D_core())]) ]))
    JI.get_core().set_allow_subst(False)
    S.switch_index( NId(JI.get_core()) )
    J << [A/1, I/1]
    S << [J/0]
    return MacroDef('to_idx', [A, I, J, S], [JI])


def create_sel_from_index(n_ins, dtype, itype):
    A = Pipe('A', dtype=dtype)
    I = Pipe('I', dtype=itype)
    # C = Pipe('C', dtype=dtype)
    J = Join('J', dtype=dtype, fun='@take_first')
    # S = Select('S', n_ins=n_ins)
    S = Select_Idx('S', n_ins=n_ins)
    AI = Attrib('AI', types.Integer_t)
    AI.set_eqdef( NAp('to_integer', [ 
            NAp('unsigned', [NId((I/1).get_D_core())]) ]))
    AI.get_core().set_allow_subst(False)
    S.select_index( NId(AI.get_core()) )
    J << [S/0, I/1]
    A << [J/0]
    return MacroDef('from_idx', [A, I, J, S], [AI])


def create_fifo_md(my_dtype, fifo_len_w=1):
    cnt_dtype = NAp('std_logic_vector', [NPrf(Prf.DOWNTO, [fifo_len_w-1, 0])])
    zero_cnt_const = 'ZERO_' + ZeroConstTypeTrav().run_on(cnt_dtype)
    
    sw_to_idx_md = create_sw_to_index(2**fifo_len_w, my_dtype, cnt_dtype)
    sel_from_idx_md = create_sel_from_index(2**fifo_len_w, my_dtype, cnt_dtype)
    counter_md = create_counter_md(cnt_dtype, zero_cnt_const)

    A = Pipe('A', dtype=my_dtype)
    Z = Pipe('Z')

    icnt = MacroInst('icnt', counter_md)
    isw = MacroInst('isw', sw_to_idx_md)
    ocnt = MacroInst('ocnt', counter_md)
    osel = MacroInst('osel', sel_from_idx_md)

    isw['A'] << [A/1]
    isw['I'] << [icnt['Y']]

    osel['I'] << [ocnt['Y']]

    cells = [None] * (2**fifo_len_w)
    for k in range(0, 2**fifo_len_w):
        C = ICell('C{0}'.format(k), dtype=my_dtype)
        # print(k)
        C << [isw['S']/(k+1)]
        osel['S'] << [C/1]
        cells[k] = C

    Z << [osel['A']/1]

    elms = [A, Z]
    elms.extend(cells)
    elms.extend(icnt.elems())
    elms.extend(ocnt.elems())
    elms.extend(isw.elems())
    elms.extend(osel.elems())
    eqs = []
    eqs.extend(osel.eqs())
    eqs.extend(isw.eqs())
    return MacroDef('fifo_md', elms, eqs)
