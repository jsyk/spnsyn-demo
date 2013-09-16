#!../../_runpyftl
from ftl.stdelem2 import *
from ftl.compiler2 import *
from ftl.minbooleq import *
from ftl.vhdlcodegen import *
from ftl.macro import *

void_dtype = 'void_t'
u8_dtype = NAp('std_logic_vector', [NPrf(Prf.DOWNTO, [7, 0])])

comp = Compiler(do_argv_parse=True)
elms = []


def ParToSer(elms, linkout_lst, idata):
    C = []
    for i in range(0, 10):
        Ci = ICell('P2S_C{0}'.format(i), void_dtype)
        C.append( Ci )
        elms.append( Ci )
    for i in range(1, 10):
        C[i] << [C[i-1]/1]

    linkout_lst.append( flows(C[0]/1) )
    for i in range(1, 9):
        linkout_lst.append( NPrf(Prf.AND, [flows(C[i]/1), NAp(NId(idata), (i-1, ))] ) )
    return (C[0]/0, C[9]/1)


def SerToPar(elms, shiftena_lst):
    C = []
    for i in range(0, 9):
        Ci = ICell('S2P_C{0}'.format(i), void_dtype)
        C.append( Ci )
        elms.append( Ci )
    for i in range(1, 9):
        C[i] << [C[i-1]/1]
    for i in range(1, 9):
        shiftena_lst.append( flows(C[i]/0) )
    return (C[0]/0, C[8]/1)


P1 = ICell('P1', void_dtype)
P2 = ICell('P2', void_dtype)
P11 = ICell('P11', void_dtype)
P12 = ICell('P12', void_dtype)
P14 = ICell('P14', void_dtype)
P15 = ICell('P15', void_dtype)
P16 = ICell('P16', void_dtype)
P17 = ICell('P17', void_dtype)
P28 = ICell('P28', void_dtype)
P29 = ICell('P29', void_dtype)
elms = [P1, P2, P11, P12, P14, P15, P16, P17, P28, P29]

# after reset: tokens in P1, P12, P17, P29
P1.set_init_st(True, None)
P12.set_init_st(True, None)
P17.set_init_st(True, None)
P29.set_init_st(True, None)

# input wires
LinkIn_at = Attrib('S_LinkIn', types.Bool_t, AttrKind.Other)
LinkIn = LinkIn_at.get_core()
IValid_at = Attrib('S_IValid', types.Bool_t, AttrKind.Other)
IValid  = IValid_at.get_core()
QAck_at = Attrib('S_QAck', types.Bool_t, AttrKind.Other)
QAck = QAck_at.get_core()
IData_at = Attrib('S_IData', u8_dtype, AttrKind.Other)
IData = IData_at.get_core()

# output wires
# IAck_at = Attrib('S_IAck', types.Bool_t, AttrKind.Other)
# IAck = IValid_at.get_core()
# ShiftEnable_at = Attrib('S_ShiftEnable', types.Bool_t, AttrKind.Other)
# ShiftEnable = ShiftEnable_at.get_core()
# LinkOut_at = Attrib('S_LinkOut', types.Bool_t, AttrKind.Other)
# LinkOut = LinkOut_at.get_core()
# QValid_at = Attrib('S_QValid', types.Bool_t, AttrKind.Other)
# QValid = QValid_at.get_core()


T1 = Gate('T1', NId(LinkIn))
elms.append(T1)
T1 << [P1/1]
P2 << [T1/1]

S1 = Select_Pri('S1')
S2 = Switch_Cond('S2', n_outs=2)
T10J = Join('T10J')
T10F = Fork('T10F')
elms.extend([S1, S2, T10J, T10F])
S2 << [P2/1]
S2.switch_to(2, NId(LinkIn)) .default_to(1)
T10J << [P28/1, S2/1]
T10F << [T10J/0]
P11 << [T10F/1]
S1 << [T10F/2]      # ....
P1 << [S1/0]

T11 = Gate('T11', NPrf(Prf.NOT, (NId(IValid), )))
elms.append(T11)
T11 << [P11/1]
P12 << [T11/1]

linkout_lst = []
T8J = Join('T8J')
T8G = Gate('T8G', NId(IValid))
S3 = Switch_Pri('S3')
S4 = Select_Pri('S4')
T9F = Fork('T9F')
elms.extend([T8J, T8G, S3, S4, T9F])
S3 << [P17/1]
T8J << [P12/1, S3/2]
T8G << [T8J/0]
P2S = ParToSer(elms, linkout_lst, IData)
P2S[0] << T8G/1
T9F << [P2S[1]]
P28 << [T9F/1]
P17 << [S4/0]
S4 << [T9F/2]         # ...
linkout_lst.extend([ flows(T8G/1) ])

shiftena_lst = []
S2P = SerToPar(elms, shiftena_lst)
T3J = Join('T3J')
T3F = Fork('T3F')
elms.extend([T3J, T3F])
S2P[0] << S2/2
T3J << [S2P[1], P29/1]
T3F << [T3J/0]
S1 << [T3F/1]
P14 << [T3F/2]


T5J = Join('T5J')
elms.extend([T5J])
T5J << [S3/1, P14/1]
P15 << [T5J/0]
linkout_lst.extend([ flows(T5J/0) ])

T6F = Fork('T6F')
T6G = Gate('T6G', NId(QAck))
elms.extend([T6F, T6G])
T6G << [P15/1]
T6F << [T6G/1]
S4 << [T6F/1]
P16 << [T6F/2]

T7G = Gate('T7G', NPrf(Prf.NOT, (NId(QAck), )))
elms.extend([T7G])
T7G << [P16/1]
P29 << [T7G/1]


comp.analyze_elems(elms)

comp.add_module_iwire_port('LinkIn', LinkIn_at)
comp.add_module_iwire_port('IValid', IValid_at)
comp.add_module_iwire_port('QAck', QAck_at)
comp.add_module_iwire_port('IData', IData_at)

comp.add_module_owire_port('IAck', flows(P11/0))
comp.add_module_owire_port('ShiftEnable', NPrf(Prf.OR, tuple(shiftena_lst)))
comp.add_module_owire_port('LinkOut', NPrf(Prf.OR, tuple(linkout_lst)))
comp.add_module_owire_port('QValid', full(P14))


comp.skip_print_tabulate = True
# comp.skip_verify = True
comp.run_phases()

cg = VhdlCodeGen(comp)
cg.vhdl_set_props(entity_name='tslink_ct')
fname = 'tslink_ct.vhd'

print ('Writing {0}'.format(fname))
f = open(fname, 'w')
f.write(joinlist(cg.vhdl_print()))
f.close()
