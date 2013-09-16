from ftl.compiler0 import *

class Compiler(CompilerBase):

    def run_phases(self):
        """ Run compiler phases. """
        if self.randomize:
            random.shuffle(self.all_eqs)

        _tim = dbgtim.Timing('run_phases')
        self.dedup_eq_refs()
        self.partition_stages()
        self.check_all_stages_acyclic()
        self.infer_types()
        self.explicit_port_drivers()
        self.extract_undefs()
        # self.extract_remove_phis()
    
        # self.basic_norm_wands()
        # self.elim_general_cyc()
        self.elim_wand_cycles()

        _tim.fin()

        # self.dedup_eq_refs()

        self.compute_deps()
        self.no_more_cycles()

        print('==== Dependency cycles eliminated.')

        self.minimize_all_eq()
        self.print_all(only_necessary=False)

        print('Module ports:')
        for mp in self.all_modports:
            a = mp.get_F_core()
            print('  {1}: {3}, {0} -> {2}'.format(mp.get_FI_core(), mp, 
                mp.get_F_core(), mp.get_D_core()))

        
        # # only after there are no singulars;
        # Minimize all equations, do the final round of substitutions
        # (this substitutes the former singular vars into the other),
        # and minimize.
        self.minimize_all_eq(do_print_eqs=False)
        # repeatedly try to unify duplicate eqs
        while True:        
            self.rehash()
            if self.elim_dup_eqs() == 0:
                break
        self.print_all(only_necessary=False, show_hash=True)

        # self.perform_substs()
        # self.minimize_all_eq()

        self.extract_undefs()
        # # self.convert_to_newast()
        self.optimize_ff_cond()
        self.rehash()
        self.mark_necessary_eqs()
        # self.hoist_mpx()            # vhdl cg
        self.print_all()

        # # repeatedly try to unify duplicate eqs
        # while True:        
        #     self.rehash()
        #     if self.elim_dup_eqs() == 0:
        #         break
        
        # self.extract_singulars()
        # self.no_more_singulars()
        
        # self.mark_necessary_eqs()
        self.conv_std_ulogic()      # vhdl cg
        # self.rehash()
        # self.print_all(show_hash=True, only_necessary=False)
        self.separate_ffs()

        if not self.skip_print_tabulate:
            self.tabulate_states(only_necessary=False)
        if not self.skip_verify:
            self.verify()

    # def elim_0hop_trivial(self, eqs):
    #     """ Eliminate 0-hop (direct) trivial WAND cycles.
    #         Identity self-ref is removed, negated self-ref is replaced by False.
    #     """
    #     _tim = dbgtim.Timing('elim_0hop_trivial')
    #     cnt = 0
    #     # over all nodes 'a'
    #     for a in eqs:
    #         if a.get_ackind() != AttrKind.Flows:
    #             continue
    #         if a in a.succ():
    #             # loop
    #             print('  Trivial self-loop in {0}'.format(a))
    #             e_aa = self.find_direct_edges(a, a)
    #             if len(e_aa) > 0:
    #                 # direct identity edges found
    #                 a.wand_remove_edges(e_aa)
    #                 cnt += 1
    #             e_iaa = self.find_inv_direct_edges(a, a)
    #             if len(e_iaa) > 0:
    #                 # direct identity edges found
    #                 a.wand_remove_edges(e_iaa, False)
    #                 cnt += 1
    #             # recompute a.pred(), update a.succ()
    #             self.recompute_pred_dep(a)
    #     _tim.fin()
    #     return cnt


    def elim_self_loop(self, eqs):
        """ Eliminate 0-hop (self) WAND cycles going over a function.
        """
        _tim = dbgtim.Timing('elim_self_loop')
        cnt = 0
        # over all nodes 'a'
        for a in eqs:
            if a.get_ackind() != AttrKind.Flows:
                continue
            if a in a.succ():
                # loop in the node 'a'
                print('  Fun-loop "f(a)->a" in {0} := {1}'.format(a, PrintTrav().run_on(a.get_eqdef())))
                print('    succ={0}'.format(a.succ()))
                _tim_1 = dbgtim.Timing('elim_self_loop/{0}'.format(a))

                a.replace_eqdef( SimplifyWithReplaceTrav().run_on(a.get_eqdef(), {a:True}) )
                self.normalize_wand(a)

                # lp_eds = []     # loopy incoming edges
                # nonlp_eds = []  # non-loopy incomming edges (other)
                # for e in a.wand_edges():        # over edges incomming to a
                #     # which nodes this edge depends on
                #     e_pred = GatherUsedVarsTrav().run_on(e)
                #     if a in e_pred:
                #         # it depends on 'a', hence it is a loopy edge.
                #         lp_eds.append(e)
                #     else:
                #         nonlp_eds.append(e)
                # assert len(lp_eds) > 0, 'No loopy edge after all?!'
                # # All refferences to 'a' in the loopy edges are replaced by True.
                # # Because 'a & f(a)' is equal to 'a & f(True)'.
                # # TODO: Do not separate nonlp_eds, just do the Replace on all.
                # for i in range(0, len(lp_eds)):
                #     # lp_eds[i] = ReplaceVariableTrav().run_on(lp_eds[i], {a:True})
                #     lp_eds[i] = SimplifyWithReplaceTrav().run_on(lp_eds[i], {a:True})
                # # merge the edges lists
                # nonlp_eds.extend(lp_eds)
                # a.replace_eqdef( NPrf(Prf.AND, nonlp_eds) )

                self.recompute_pred_dep(a)
                print('    {0} := {1}'.format(a, PrintTrav().run_on(a.get_eqdef())))
                cnt += 1
                _tim_1.fin()

                # # create a new node ab
                # ab_attr = Attrib(names.give(a.get_name()), a.get_actype(), a.get_ackind())
                # ab = ab_attr.get_core()
                # self.all_eqs.append(ab)
                # # give it the non-loopy edges
                # ab.set_eqdef( NPrf(Prf.AND, nonlp_eds) )
                # ab.init_tarjan()
                # ab.add_tarjan_succ(a)
                # self.recompute_pred_dep(ab)
                # print('    new wand {0} := {1}'.format(ab, PrintTrav().run_on(ab.get_eqdef())))
                # # rewrite the loopy edges to use ab instead of a
                # for i in range(0, len(lp_eds)):
                #     lp_eds[i] = ReplaceVariableTrav().run_on(lp_eds[i], {a:NId(ab)})
                # # lp_eds becomes input edges in 'a'; add the dependence on ab
                # lp_eds.append( NId(ab) )
                # a.replace_eqdef( NPrf(Prf.AND, lp_eds) )
                # self.recompute_pred_dep(a)
                # cnt += 1
        _tim.fin()
        return cnt


    def elim_basic_wand_cyc(self):
        """ Basic wand cycle eliminations.
            - direct and inverted-direct self-loops
            - direct a<->b cycle  =>> merge the nodes
            - self-loop via a function.

            1. simplify expressions
            2. resolve 1-st level direct loops
                2.1 via identity
                2.2 via negation
                2.3 via a general fun
            3. merge interdep wands
        """
        _tim = dbgtim.Timing('elim_basic_wand_cyc')

        restarting = True
        itr = 1
        while restarting:
            restarting = False
            print('--- Basic WAND elim: Iteration {0}'.format(itr))
            _tim_1 = dbgtim.Timing('elim_basic_wand_cyc/{0}'.format(itr))

            # 1. simplify, maintain WAND
            self.simplify_wands(self.all_eqs)

            # get strong components - detect cycles
            self.compute_deps()

            # self.print_all(show_deps=True, only_necessary=False)

            # print('Sccl: {0}'.format(sccl))
            # cnt_0hop = self.elim_0hop_trivial(self.all_eqs)     # direct, inv direct loops
            cnt_0hop = self.elim_self_loop(self.all_eqs)        # f(a) -> a
            cnt_1hop = self.elim_direct_cycles(self.all_eqs) # direct a<->b cycle
            if cnt_1hop > 0:
                self.dedup_eq_refs()
            # cnt_0hop += self.elim_0hop_fun(self.all_eqs)        # f(a) -> a
            
            restarting = (cnt_0hop + cnt_1hop) > 0
            itr += 1
            _tim_1.fin()

        _tim.fin()
        self.print_all(show_deps=True, only_necessary=False)


    def elim_general_cyc(self, a, sc):
        """ Remove a general cycle going over 'a' from the strong component 'sc'.
            The 'a' node must be a part of the strong component, but no longer listed in 'sc'.
            Requires up-to-date SCC info.
            The pred/succ info in the SC is left outdated.
        """
        _tim = dbgtim.Timing('elim_general_cyc/{0}'.format(a))
        # sc is a strong component, a set of nodes.
        print('  In SC={1} ({3}) wand node {0} = {2}'.format(
            a, sc, PrintTrav().run_on(a.get_eqdef()), len(sc)))
        # 'a' is a node in sc.
        # Gather all edges incomming from the sc to a.
        e_ext = []  # edges comming from external nodes
        e_int = []  # ==g; edges comming from sc internal nodes
        for e in a.wand_edges():
            e_pred = GatherUsedVarsTrav().run_on(e)
            if e_pred.isdisjoint(sc):
                # e has no edge comming from sc, it is external.
                e_ext.append(e)
            else:
                e_int.append(e)
        # Create a new node ab (A-bar)
        ab_attr = Attrib(names.give(a.get_name()), a.get_actype(), a.get_ackind())
        ab = ab_attr.get_core()
        # if e_ext:
        self.all_eqs.append(ab)
        # ab gets all external incomming edges:
        ab.set_eqdef( NPrf(Prf.AND, e_ext) )
        print('    new wand node {0} = {1}'.format(ab, PrintTrav().run_on(ab.get_eqdef())))
        # e_int == ab & g
        # if e_ext:
        e_int.append(NId(ab))
        print('    e_int={0}'.format(PrintTrav().run_on(e_int)))
        # a &= ab & g
        a.replace_eqdef( NPrf(Prf.AND, e_int) )
        print('    redefined {0} = {1}'.format(a, PrintTrav().run_on(a.get_eqdef())))
        # Over all other nodes in the sc:
        for b in sc:
            # replace all references to 'a' with (ab & g())
            # where g() are all the icomming edges from the local strong comp.
            b.replace_eqdef( ReplaceVariableTrav().run_on(b.get_eqdef(), 
                { a:NPrf(Prf.AND, e_int)}) )

            # # replace all references to 'a' with 'ab'
            # b.replace_eqdef( ReplaceVariableTrav().run_on(b.get_eqdef(), {a:NId(ab)}) )
            # # a list of more new incomming edges to 'b'
            # gf_edgs = []
            # # over all incomming edges to b.
            # for e in b.wand_edges():
            #     e_pred = GatherUsedVarsTrav().run_on(e)
            #     if ab in e_pred:
            #         # the edge 'e' is a fun of 'ab'.
            #         # Create a new edge that has all refs to 'ab' replaced by (ab & g)
            #         gf_edgs.append( ReplaceVariableTrav().run_on(e, 
            #             {ab : NPrf(Prf.AND, e_int)} ) )
            # # merge the original edges with the new ones into the WAND at 'b'
            # gf_edgs.extend(b.wand_edges())
            # b.replace_eqdef( NPrf(Prf.AND, gf_edgs) )

            # HACK:
            # b.replace_eqdef( DefaultTrav().run_on(b.get_eqdef()) )
            # OPTIMIZATION:
            # if not e_ext:
                # b.replace_eqdef( ReplaceVariableTrav().run_on(b.get_eqdef(), {ab:True}) )
            print('    {0} = {1}'.format(b, PrintTrav().run_on(b.get_eqdef())))
        # self.recompute_pred_dep(ab)
        _tim.fin()


    def elim_wand_cycles(self):
        """ Eliminate all wand cycles. """
        _tim = dbgtim.Timing('elim_wand_cycles')
        n_scc = 0
        itr = 1
        while True:
            print('==== Cycles elimination, round #{0}'.format(itr))
            _tim_1 = dbgtim.Timing('elim_wand_cycles/{0}'.format(itr))

            if self.randomize:
                random.shuffle(self.all_eqs)

            self.elim_basic_wand_cyc()

            # compute strong components, filter out the single node ones.
            self.compute_deps()
            sccl_all = TarjanSCC().run_on(self.all_eqs)     # all SCC
            # 
            if self.randomize:
                random.shuffle(sccl_all)
            # 
            sccl = list(filter(lambda sc: (len(sc)>1), sccl_all))  # multi-node SCC only
            print('Multi-node SCC: {0}'.format(sccl))

            # no more multi-node SCC? -> done
            if len(sccl) == 0:
                break

            assert n_scc < len(sccl_all), 'Num of SCC has not increased: {0} -> {1}'.format(n_scc, len(sccl_all))
            n_scc = len(sccl_all)

            # over all strong components
            print('--- General cycles elim #{0}: eqs={3}, all-SCC={1}, multi-node-SCC={2}'.format(
                itr, len(sccl_all), len(sccl), len(self.all_eqs)))
            print('SCCL: {0}'.format(sccl))
            for sc in sccl:
                if self.randomize:
                    random.shuffle(sc)
                a = sc.pop()   # pick a node (last) in the strong component sc
                # for ai in range(0, len(sc)):
                #     if sc[ai].get_ackind() == AttrKind.Flows:
                #         a = sc.pop(ai)
                #         break
                # else:
                #     assert False, "No F-node in SC={0} ?!".format(sc)
                self.elim_general_cyc(a, set(sc))

            itr += 1
            _tim_1.fin()

        _tim.fin()


    def elim_direct_cycles(self, eqs):
        """ Eliminate (1-hop) WAND cycles.
            Requires up-to-date pred() and succ() info, and keeps it.
            Returns number of elims done.
            TODO: support cycles of any length.
        """
        _tim = dbgtim.Timing('elim_direct_cycles')
        cnt = 0
        for a in eqs:
            if a.get_ackind() != AttrKind.Flows:
                continue
            # potential 1-hop cycles
            cyc = a.succ() & a.pred() - set([a])        # set
            for b in cyc:
                # there is a cycle: f(a) -> b,  g(b) -> a
                print('  Cycle: {0} <-> {1}'.format(a, b))
                e_ab = self.find_direct_edges(a, b)
                e_ba = self.find_direct_edges(b, a)
                if len(e_ab)>0 and len(e_ba)>0:
                    print('    direct; a.succ={0}, a.pred={1}, b.succ={2}, b.pred={3}'.format(
                        a.succ(), a.pred(), b.succ(), b.pred()))
                    # Start merging a and b to a single core.
                    # The a will be kept, the b is merged to a.
                    #
                    a.wand_remove_edges(e_ba)
                    b.wand_remove_edges(e_ab)
                    self.merge_wand_nodes(a, b)                    
                    cnt += 1
        _tim.fin()
        return cnt
