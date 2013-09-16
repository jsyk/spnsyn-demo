import copy


class MacroDef:
    """ Macros are subgraphs, expanded when instantiated.
    """
    def __init__(self, name, elems=None, eqs=None):
        """ Create macro definition """
        self.all_elems = dict()             # name:string -> Element
        self.all_eqs = dict()
        self.macname = name
        if elems:
            self.add(elems)
        if eqs:
            self.add_eqs(eqs)

    def add(self, elems):
        """ Add a list of elems to the macro definition. """
        for elm in elems:
            if elm.get_name() in self.all_elems:
                print("MacroDef {0}: element with the name '{1}' already in the macro!".format(
                    self.macname, elm.get_name()))
            self.all_elems[elm.get_name()] = elm

    def add_eqs(self, eqs):
        for eq in eqs:
            if eq.get_name() in self.all_eqs:
                print("MacroDef {0}: eq with the name '{1}' already in the macro!".format(
                    self.macname, eq.get_name()))
            self.all_eqs[eq.get_name()] = eq



class MacroInst:
    """ An instance of a macro.
    """
    def __init__(self, iname, mdef):
        self.inst_name = iname
        self.mdef = mdef
        # deep copy the graph
        self.inst_elems, self.inst_eqs = copy.deepcopy((mdef.all_elems, mdef.all_eqs))
        self.map_def2inst = dict()        # mdef Element -> inst Element
        self.mapeq_def2inst = dict()
        # rename the copied elems (but not in inst_elems keys!)
        # construct map_def2inst that maps the old Elements in mac-def to ours
        for en in self.inst_elems:
            elm = self.inst_elems[en]
            oldel = self.mdef.all_elems[en]
            self.map_def2inst[oldel] = elm
            elm.rename("{0}_{1}".format(self.inst_name, elm.get_name()))
        for en in self.inst_eqs:
            eq = self.inst_eqs[en]
            oldeq = self.mdef.all_eqs[en]
            self.mapeq_def2inst[oldeq] = eq
            eq.rename('{0}_{1}'.format(self.inst_name, eq.get_name()))

    def get_elm(self, e):
        """ Return the element given its name (string) or the corresponding
            instance in the macro definition. """
        if type(e) == str:
            return self.inst_elems[e]
        else:
            return self.map_def2inst[e]

    def __getitem__(self, e):
        """ Return the element given its name (string) or the corresponding
            instance in the macro definition. """
        return self.get_elm(e)

    def elems(self):
        """ Return a list of all elements in the macro instance. """
        return self.inst_elems.values()

    def eqs(self):
        return self.inst_eqs.values()

