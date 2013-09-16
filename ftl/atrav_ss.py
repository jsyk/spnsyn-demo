from ftl.ast import *
from ftl.atrav import DefaultTrav, PrintTrav

class ReplaceSwiSelRefsTrav(DefaultTrav):
    def run_on(self, eqd, ss_repls):
        self.ss_repls = ss_repls
        return self.do_trav(eqd)

    def trav_prf_swisel(self, eqd):
        # it is: args = (swisel_elm, index, NId(wnd_r_1), NId(wnd_r_2), ...)
        ss_elm = eqd.args()[0].get_val()        # it's arg[0] = NConst(swisel_elm)
        new_args = [NConst(ss_elm), eqd.args()[1]]
        for i in range(2, len(eqd.args())):
            wnd_r = eqd.args()[i].get_ref()
            wnd_new = self.ss_repls.get(tuple((ss_elm, wnd_r)))
            if wnd_new:
                new_args.append( NId(wnd_new) )
                print("    ReplaceSwiSelRefsTrav: choice elm {0}: {1} -> {2}".format(ss_elm, wnd_r, wnd_new))
            else:
                new_args.append( eqd.args()[i] )

        return NPrf(Prf.SWISEL, tuple(new_args))


