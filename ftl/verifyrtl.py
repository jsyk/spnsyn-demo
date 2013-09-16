from ftl.atrav_eq import GatherUsedVarsTrav, SimplifyWithSubstTrav
import sys

class VerifyRTL:
    def __init__(self):
      # some unimportant statistics
      self.stat_count_elems = 0
      self.stat_count_states = 0


    def verify(self, all_elems):
        """ Verify the final equations, check that they produce consistent
            results wrt FTL. This is the object entry point. """
        # 1. iterate over all elements in the design
        # 2. in each element go through all its ports and gather the variables
        #   that the ports P and R attribs depend on. Add the optional fsm_stor core.
        #   These are the independent variables.
        # 3. in each element, go through all the configurations of the independent
        #   variables, compute states of the element's pipes, and verify the consistency.
        for el in all_elems:
            self.verify_elm(el)
            self.stat_count_elems += 1


    def verify_elm(self, el):
        """ Verify the single element. """
        print('Verifying element {0}: {1}'.format(el, el.__class__.__name__))
        # the set of independent variables, customized for this element
        indeps = set([])
        # get the variables the ports depend on
        for p in el.get_all_ports():
            # indeps |= self.gather_indeps(p.get_P_core())
            # indeps |= self.gather_indeps(p.get_R_core())
            indeps |= self.gather_indeps(p.get_F_core())
            # always treat the fsm store as an independet var
            indeps |= set(el.get_fsm_stor())
        
        # establish an order in the set of indeps
        indeps = list(indeps)
        print('  Has {0} indeps={1}'.format(len(indeps), indeps))

        # go through all the configurations
        for cc in range(0, 2**len(indeps)):
            k = len(indeps) - 1
            cc_values = dict()  # AttrCore:indep_var -> bool
            for hi in indeps:
                b = (cc >> k) & 1
                assert b in [0, 1]
                cc_values[hi] = (b and True) or False   # convert 0/1 to False/True
                k -= 1

            # print('  cc_values={0}'.format(cc_values))

            # Now, dict cc_values holds a mapping of the independent
            # attribs to their values in the configuration.
            # Compute the state of all 
            # the elems input and output pipes, then check that it is consistent
            # with the element type.
            # aa_values = dict(cc_values)  # make copy; dep vars; AttrCore -> bool
            # aa_values = cc_values
            pf_values = dict()          # pipe flows; PipeBase -> bool
            
            for p in el.get_all_ports():
                # evaluate the P and R cores
                # vp = self.eval_acore(p.get_P_core(), aa_values, cc_values)
                # vr = self.eval_acore(p.get_R_core(), aa_values, cc_values)
                vf = self.eval_acore(p.get_F_core(), cc_values, cc_values)
                # the computed values must be bools, not expressions.
                # assert type(vp) is bool, 'vp is {0}'.format(vp)
                # assert type(vr) is bool, 'vr is {0}'.format(vr)
                # if type(vp) is bool and type(vr) is bool:
                if type(vf) is bool:
                    # excited?
                    # f = (vp and vr)
                    f = vf
                    pf_values[p] = f
                    # print "Element {0}, pipe {1}: vp={2}, vr={3}, f={4}".format(
                    #     el.get_name(), p, vp, vr, f)
                    # print( "Element {0}, pipe {1}: {3}={2}".format(
                                            # el.get_name(), p, f, p.get_F_core()))
                else:
                    # Typically because of the integer vars in mpx...
                    # This will require a deeper analysis :-(
                    print('WARNING/TODO: Could not verify Element {0} of type {1}.'.format(
                                    el.get_name(), el.__class__.__name__))
                    print('  Independent vars: {0}'.format(indeps))
                    return False

            if not el.verify_consistency(pf_values, cc_values):
                # hmm, consistency check failed!
                print( 'FATAL: Verify failed for Element {0} of type {1} !!'.format(
                                    el.get_name(), el.__class__.__name__))
                print('    cc_values={0}'.format(cc_values))
                # print the state of all pipes
                for p in el.get_all_ports():
                    print( '    port {0} is {1} := {2}'.format(
                            p, p.get_F_core(), pf_values[p]))
                for s in el.get_fsm_stor():
                    print( '    storage {0} := {1}'.format(s, cc_values[s]))
                assert False, 'Critical logic error!'
        # ok
        self.stat_count_states += 2**len(indeps)
        return True


    def gather_indeps(self, acore):
        """ Gather independent vars from the attrib core.
            Returns the subset of primary inputs the acore depends on.
        """
        # if the attrib hasn't a definition it is independent;
        # otherwise add its used vars as the independent
        if acore.get_eqdef() is None:
            return set([acore])
        else:
            # not GatherDepVars_NoFF_Trav: it would not return FF vars as indeps.
            # This goes VIA eq_defs in the intermediate vars down into primary inputs!
            return GatherUsedVarsTrav().run_on(acore.get_eqdef(), inner=False, leaf=True)


    def eval_acore(self, acore, aa_values, cc_values):
        """ Evaluate the attrib-core given the independent values in cc_values,
            and add the result in the aa_values dict. If the attrib-core
            has been already evaluated before (it is in aa_values),
            the value from there is returned directly. """
        if acore in aa_values:
            # print('    computing {0}: cached.'.format(acore))
            return aa_values[acore]
        else:
            # print('    computing {0}'.format(acore))
            v = SimplifyWithSubstTrav().run_on(acore.get_eqdef(), cc_values)
            # v = atrav_eq.SimplifyWithReplaceTrav().run_on(acore.get_eqdef(), cc_values)
            # print('Eval: {0} = {1}'.format(atrav.PrintTrav().run_on(acore.get_eqdef()),
            #     atrav.PrintTrav().run_on(v)))
            aa_values[acore] = v
            return v


