from ftl.compiler0 import *
from ftl.atrav_ss import ReplaceSwiSelRefsTrav
from collections import deque

class Compiler(CompilerBase):
    pass

    def run_phases(self):
        """ Run compiler phases. """
        print('Compiler 2 starting.')
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
        # self.elim_wand_cycles()

        # Merge WANDs with direct cycle, e.g.  a &= b ; b &= a.
        # This is only a technical means of late wand/f-core merging.
        # print("Merging wands in direct cycles:")
        # self.compute_deps()
        self.elim_direct_cycles(self.all_eqs)

        # self.simplify_wands(self.all_eqs)
        
        self.print_all(only_necessary=False)

        self.expand_swisels()

        # self.compute_deps()
        self.elim_direct_cycles(self.all_eqs)


        # the net must be acyclic
        self.compute_deps()
        self.print_all(only_necessary=False, show_deps=True)
        self.no_more_cycles()

        _tim.fin()

        print('==== The activation net is expanded and acyclic.')

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


    def expand_swisels(self):
        """ Expanding @swisel prfs into boolean logic. """
        if self.randomize:
            random.shuffle(self.all_swisels)
        print("Shall expand {0} swisels:".format(len(self.all_swisels)))

        ss_repls = dict()       # dict: tuple(choice_element, eq) -> NId(replacement_eq)

        # over all wand eqs, materialize the list because all_eqs is expanded
        orig_eqs = list(filter(lambda x: x.get_ackind() == AttrKind.Flows, self.all_eqs))
        for eq in orig_eqs:
            # over all in-edges in the wand eq
            # print("  {0}".format(str(eq)))
            self.expand_swisels_in_wand(eq, ss_repls)

        print("  replacement dict: {0}".format(ss_repls))

        for eq in filter(lambda x: x.get_ackind() == AttrKind.Flows, self.all_eqs):
            print("  replacing in {0}".format(eq))
            eq.replace_eqdef( ReplaceSwiSelRefsTrav().run_on(eq.get_eqdef(), ss_repls) )

        self.print_all(only_necessary=False)

        # assert False, "Do expansions!"
        for ss in self.all_swisels:
            print("  Pattern-expading swisel {0}".format(ss))
            wnds_w = [None] * len(ss.get_all_ports())
            wnds_r = [None] * len(ss.get_all_ports())
            for eq in filter(lambda x: x.get_ackind() == AttrKind.Flows, self.all_eqs):
                for we_i in range(0, len(eq.wand_edges())):
                    we = eq.wand_edges()[we_i]
                    if nprfget(we) != Prf.SWISEL:
                        # skip non-SWISEL edges
                        continue
                    if we.get_args()[0].get_val() == ss:
                        # the wand edge 'we' is a @@swisel prf for our swisel!
                        pi = we.get_args()[1]       # writing swisel port index
                        assert wnds_w[pi] is None
                        wnds_w[pi] = eq         # remember: the wand is the at port index pi
                        for ri in range(2, len(we.get_args())):
                            rp = we.get_args()[ri].get_ref()
                            assert (wnds_r[ri-2] is None) or (wnds_r[ri-2] == rp), "Mismatch in swisel reading wands!"
                            wnds_r[ri-2] = rp
                        eq.wand_remove_edges([we_i])
                        # found = True

            print("    wnds_w={0}, wnds_r={1}".format(wnds_w, wnds_r))
            ss.expand_pattern(wnds_w, wnds_r)



    def expand_swisels_in_wand(self, eq, ss_repls):
        """ This does wands multi-spliting for swisels.
            Each wand eq is processed independently. We gather a list of swisel prfs in the eq.
            The eq is split in eqb, link is created: eqb -> eq.
            For each swisel, a pair of new wands is created, R and W.
            At the end a dict() for replacements is created.
        """
        swisels_pf = []     # list of swisel prfs, for searching
        swisels_wi = []     # list of edge indices in this eq that contain a swisel prf
        # swisels_ri = []     # list of lists of 

        for we_i in range(0, len(eq.wand_edges())):
            we = eq.wand_edges()[we_i]      # 'we' is a wand edge - an expression
            if nprfget(we) != Prf.SWISEL:
                # skip non-SWISEL edges
                continue
            # ok, it is a swisel prf.
            if we not in swisels_pf:        # FIXME: is the check meaningful? It should always be true!
                # a new swisel we have found;
                swisels_pf.append(we)
                swisels_wi.append(we_i)

        # exit if no swisels in our eq
        if not swisels_pf:
            return

        print('    {0} has swisel prfs at positions {1}'.format(eq, swisels_wi))

        # Split the eq wand. Create a new node ab (EQ-bar)
        eqb_attr = Attrib(names.give(eq.get_name()), eq.get_actype(), eq.get_ackind())
        eqb = eqb_attr.get_core()
        # wnds_r[i] = eqb
        self.all_eqs.append(eqb)
        # eqb gets all external incomming edges; these are all the edges incoming into 'a'.
        eqb.set_eqdef( eq.get_eqdef() )
        eqb.wand_remove_edges( swisels_wi )      # remove the @swisel writes in the eqb
        # 'eq' gets an edge from eqb; there will be edge
        # from wnds_r to wnds_w.
        eq.replace_eqdef( NPrf(Prf.AND, [NId(eqb)]) )
        # We have: external_writes -> eqb -> eq -> external_reads

        # Create wand pairs R+W for swisels
        wnd_r = []
        wnd_w = []
        for ss_pf in swisels_pf:
            # create W wand
            w_eq_attr = Attrib(names.give(eq.get_name()+'_SSW'), eq.get_actype(), eq.get_ackind())
            w_eq = w_eq_attr.get_core()
            self.all_eqs.append(w_eq)
            wnd_w.append(w_eq)
            w_eq.set_eqdef( ss_pf )     # it gets the orig prf:  @swisel -> w_eq
            eq.wand_add( NId(w_eq) )         # the output eq reads from it: w_eq -> eq

            # create R wand
            r_eq_attr = Attrib(names.give(eq.get_name()+'_SSR'), eq.get_actype(), eq.get_ackind())
            r_eq = r_eq_attr.get_core()
            self.all_eqs.append(r_eq)
            wnd_r.append(r_eq)
            r_eq.set_eqdef( NPrf(Prf.AND, [NId(eqb)]) )     # it gets a read from the input: eqb -> r_eq

        # create internal connections among the R+W wands
        for i in range(0,len(wnd_r)):
            for k in range(0,len(wnd_w)):
                if i != k:
                    # W_k -> R_i, for all i != k
                    wnd_r[i].wand_add( NId(wnd_w[k]) )

        # in all @swisel prfs in the all_eqs we must replace eq with appropriate wnd_r[i]
        for i in range(0,len(swisels_pf)):
            ss_pf = swisels_pf[i]
            ss_elm = ss_pf.args()[0].get_val()            # the Element

            # (ss_elm, eq) -> (ss_elm, wnd_r[i])
            ss_repls[tuple((ss_elm, eq))] = wnd_r[i]



    # def expand_swisels(self):
    #     if self.randomize:
    #         random.shuffle(self.all_swisels)
    #     print("Expanding {0} swisels:".format(len(self.all_swisels)))

    #     starting = list(self.all_swisels)
    #     next = deque()

        # found = False
    #     while starting or next:
    #         ss = None
    #         if next:
    #             ss = next.popleft()
    #             starting.remove(ss)
    #         else:
    #             ss = starting.pop()

    #         neighs = self.expand_swisel(ss)
    #         if neighs:
    #             next.extend(neighs)
    #         print('  next={0}'.format(next))

    #     # for ss in self.all_swisels:
    #     #     neighs = list(self.expand_swisel(ss))


    # def expand_swisel(self, ss):
    #     print("  Swi/Sel {0}".format(ss))
    #     # Find all the wands this swisel has prfs in.
    #     # Identify the ports -in,out- of the swisel.
    #     # Remove swisel's prfs from the wands.
    #     # 
    #     # wnds_i/o are lists of paired wands that will
    #     # support the incomming and outgoing edges of the swisel pattern.
    #     wnds_w = [None] * len(ss.get_all_ports())
    #     wnds_r = [None] * len(ss.get_all_ports())
    #     neighs = set()        # set of neighbouring swisels (Elements)

    #     # over all wand eqs
    #     for eq in filter(lambda x: x.get_ackind() == AttrKind.Flows, self.all_eqs):
    #         # over all in-edges in the wand eq
    #         local_neighs = set()
    #         found = False
    #         for we_i in range(0, len(eq.wand_edges())):
    #             we = eq.wand_edges()[we_i]
    #             if nprfget(we) != Prf.SWISEL:
    #                 # skip non-SWISEL edges
    #                 continue
    #             if we.get_args()[0].get_val() == ss:
    #                 # the wand edge 'we' is a @@swisel prf for our swisel!
    #                 pi = we.get_args()[1]       # writing swisel port index
    #                 assert wnds_w[pi] is None
    #                 wnds_w[pi] = eq         # remember: the wand is the at port index pi
    #                 for ri in range(2, len(we.get_args())):
    #                     rp = we.get_args()[ri].get_ref()
    #                     assert (wnds_r[ri-2] is None) or (wnds_r[ri-2] == rp), "Mismatch in swisel reading wands!"
    #                     wnds_r[ri-2] = rp
    #                 eq.wand_remove_edges([we_i])
    #                 found = True
    #                 # break  # next eq
    #             else:
    #                 # prf for a different swisel.
    #                 local_neighs.add( we.get_args()[0].get_val() )
    #         if found:
    #             # swisels in the local eqs are all neighbours of the current one.
    #             # We shall expand them next after we're done here.
    #             neighs.update(local_neighs)

    #     print("    wnds_w={0}, wnds_r={1}".format(wnds_w, wnds_r))
    #     # all the wnds_w/r must be filled in.
    #     if not(all(wnds_w) and all(wnds_r)):
    #         self.print_all(only_necessary=False)
    #         assert all(wnds_w) and all(wnds_r), "Missing a wand for swisel!"

    #     # If a pair 'i' in wnds_r[i]/wnds_w[i] is an identical wand,
    #     # the node must be split.
    #     for i in range(0, len(wnds_w)):
    #         if wnds_w[i] == wnds_r[i]:
    #             # It is an identical node, split the node.
    #             # 
    #             a = wnds_w[i]       # orig node
    #             # Create a new node ab (A-bar)
    #             ab_attr = Attrib(names.give(a.get_name()), a.get_actype(), a.get_ackind())
    #             ab = ab_attr.get_core()
    #             wnds_r[i] = ab
    #             self.all_eqs.append(ab)
    #             # ab gets all external incomming edges; these are all the edges incoming into 'a'.
    #             ab.set_eqdef( a.get_eqdef() )
    #             # 'a' gets an edge from ab; there will be edge
    #             # from wnds_r to wnds_w.
    #             a.replace_eqdef( NPrf(Prf.AND, [NId(ab)]) )
    #         else:
    #             # two different nodes.
    #             # XXX add edge from wnds_r to wnds_w; XXX -- see t208 why this is bad idea
    #             # wnds_w[i].wand_add( NId(wnds_r[i]) )
    #             pass

    #     print("    wnds_w={0}, wnds_r={1}".format(wnds_w, wnds_r))
    #     print('    neighs={0}'.format(str(neighs)))
    #     ss.expand_pattern(wnds_w, wnds_r)
    #     return neighs


    def find_direct_cycles(self, a, stack, colours):
        if (a.get_eqdef() is None) or (a.get_ackind() != AttrKind.Flows):
            # empty eqdef, probably an undef (input) node,
            # or non-F node
            return
        if a in stack:
            # cycle!
            i = stack.index(a)    # index of the leading node in the cycle
            ca = colours[a]         # colour of the leading node 'a'
            assert ca is not None
            # change the colour of all the nodes in this cycle to the
            # colour of the leading node.
            for b in stack[i+1:]:
                colours[b] = ca
            # print('Found a direct cycle, coloured {1}: {0}'.format(stack[i:], ca))
        else:
            # no cycle, recurse, depth first
            stack.append(a)
            a_dd = list(self.gather_direct_deps(a))
            for b in a_dd:
                self.find_direct_cycles(b, stack, colours)
            stack.pop()


    def elim_direct_cycles(self, eqs):
        """ Eliminate n-hop WAND cycles.
            Returns number of elims done.
            Destroys dependency info.
        """
        print("Merging wands in direct cycles:")
        _tim = dbgtim.Timing('elim_direct_cycles')

        # initially each F-node has a different colour
        colours = dict()          # node -> colour:int
        i = 1
        for a in filter(lambda x: x.get_ackind() == AttrKind.Flows, eqs):
            colours[a] = i
            i += 1

        # Find cycles by depth-first search, colour the nodes.
        for a in filter(lambda x: x.get_ackind() == AttrKind.Flows, eqs):   # over all F-nodes 'a'
            self.find_direct_cycles(a, [], colours)

        # Gather nodes that have common colour.
        colour_nds = dict()     # colour:int -> set(nodes)
        for nd in colours.keys():
            c = colours[nd]
            # (nd,c) = node and its colour
            if c in colour_nds:
                # the colour is already known; add the node
                colour_nds[c].add(nd)
            else:
                # new colour encountered
                colour_nds[c] = set([nd])

        cnt = 0
        # Print the cycles by colour
        print('  Direct cycles:')
        for c in colour_nds.keys():
            nds = colour_nds[c]         # set of nodes
            if len(nds) > 1:
                print('    \"{0}\" : {1}'.format(c, nds))
                cnt += 1

                # In all nodes of the cycle remove internal edges of the cycle.
                for b in nds:
                    # b is a node in the cycle set
                    r = []
                    eds = b.wand_edges()
                    for i in range(0, len(eds)):        # over edges incomming to t
                        if isinstance(eds[i], NId) and eds[i].get_ref() in nds:
                            # the edge 'i' goes to the cycle, add it
                            r.append(i)
                    # remove all edges that go in the cycle
                    b.wand_remove_edges(r)

                # Merge all cycle nodes into a 'head' node (an arbitrary one of them)
                head = nds.pop()
                # print('      head: {0}'.format(head))
                for b in nds:
                    print('      merging: {0} <- {1}'.format(head, b))
                    self.merge_wand_nodes__nodeps(head, b)
                print('      {0} :F= {1}'.format(head.get_name(), PrintTrav().run_on(head.get_eqdef())))

        _tim.fin()
        print('  {0} wands merged.'.format(cnt))
        return cnt
