
def enum(**enums):
    return type('Enum', (), enums)

Prf = enum(
    # these should be ascii strings, they are used to form method names
    # ADD = 'add',
    # SUB = 'sub',
    # MUL = 'mul',
    # DIV = 'div',
    # DOT = 'dot',
    FF  = 'ff',
    AND = 'and',
    OR  = 'or',
    NOT = 'not',
    COND = 'cond',
    COLON = 'colon',
    COMMA = 'comma',
    # PHI = 'phi',
    EQ = 'eq',
    MPX = 'mpx',
    ZERO_CONST_TP = 'zero_const_tp',
    NOFOLLOW = 'nofo',
    GETFLD = 'getfld',
    DOWNTO = 'downto',
    TO = 'to',
    SWISEL = 'swisel'
    # FROM_ALL = "FROM_ALL",      # Join
    # TO_ALL = "TO_ALL",          # Fork
    # FROM_ONE = "FROM_ONE",      # Select
    # TO_ONE = "TO_ONE",          # Switch
    # WHEN = "WHEN",              # when:
    # LET = "LET"
    )


class Node:
    def __init__(self, loc=None):
        # SONS #
        # ATTRIBUTES #
        self.srcloc = loc           # location in the source code, ScanLocation
        self.rtype = None           # result type
        self.n_hash = None          # stored hash
    
    def set_loc(self, loc):
        self.srcloc = loc
    
    def get_loc(self):
        return self.srcloc
    
    def set_rtype(self, tp):
        assert isinstance(tp, NExpr)
        self.rtype = tp
    
    def get_rtype(self):
        return self.rtype

    def get_hash(self):
        return self.n_hash

    def set_hash(self, h):
        self.n_hash = h & 0xFFFFFFFFFFFFFFF

    def get_prf(self):
        return None


def nhash(x):
    if isinstance(x, Node):
        return x.get_hash()
    else:
        return hash(x)

def nprfget(x):
    if isinstance(x, Node):
        return x.get_prf()
    else:
        return None


class NExpr(Node):
    pass



class NConst(NExpr):
    """ Constant """
    def __init__(self, val, loc=None):
        # SONS #
        # ATTRIBUTES #
        self.val = val         # attrib
        #
        self.set_loc(loc)

    def get_val(self):
        return self.val


class NId(NExpr):
    """ An ID, reference to a variable or attrib. """
    def __init__(self, ref, loc=None):
        super(NId, self).__init__(loc=loc)
        # SONS #
        # ATTRIBUTES #
        self.__ref = ref

    def get_ref(self):
        return self.__ref.fwd()


class NBaseAp(NExpr):
    """ Reference or an application """
    def __init__(self, args, loc=None):
        super(NBaseAp, self).__init__(loc=loc)
        # SONS #
        # for a in args:
            # assert isinstance(a, NExpr), 'is of type {0}'.format(type(a))
        self._set_args(args)           # sons, list of ValueExpr
        # ATTRIBUTES #
        #

    def get_args(self): return self.__args
    def args(self): return self.__args

    def _set_args(self, a):    # private!
        assert type(a) == list or type(a) == tuple, "set_args: the 'args' must be a list or tuple, it is {0}".format(type(a))
        self.__args = tuple(a)


class NPrf(NBaseAp):
    """ Application of a built-in primitive function """
    
    def __init__(self, prf, args, loc=None):
        self.__prf = None
        super(NPrf, self).__init__(args, loc=loc)
        # SONS #
        # ATTRIBUTES #
        self.__prf = prf         # attrib; on of ADD, SUB, etc.
        self.rtype = None      # attrib
        #
    
    def get_prf(self):
        return self.__prf

    def _set_args(self, a):     # private!
        super(NPrf, self)._set_args(a)
        assert self.__prf != Prf.NOT or len(a) == 1

    def is_commutative(self):
        return self.__prf in [Prf.AND, Prf.OR, Prf.EQ]



class NAp(NBaseAp):
    """ An application of a user function. """
    def __init__(self, fun, args, loc=None):
        super(NAp, self).__init__(args, loc=loc)
        # assert isinstance(fun, NExpr)
        # SONS #
        # ATTRIBUTES #
        self.__fun = fun
        #

    def get_fun(self):
        return self.__fun


# class NStatement(Node):
#     pass


# class NAssign(NStatement):
#     def __init__(self):
#         self.lhs = []      # list of NExpr yelding l-vals
#         self.expr = None   # NExpr


# class NBlock(NStatement):
#     def __init__(self):
#         self.stmts = []    # list of NStatement


# class NPipeline(NExpr):
#     """ Serial composition of components. Implicit pipeline. """
#     def __init__(self):
#         # list of components in the pipeline
#         self.items = []     # sons
#         #self.cond = None
#         self.action = None     # son
    
#     def add_flowitem(self, pi):
#         assert isinstance(pi, NExpr), 'it is {0}'.format(pi.__class__.__name__)
#         self.items.append(pi)
    
#     def get_flowitems(self):
#         return self.items


# #class NCondFlow(NFlowExpr):
#     #""" A flow pipeline with the 'when' condition """ 
#     #def __init__(self, when_cond, fl):
#         #assert when_cond is None or isinstance(when_cond, NValueExpr)
#         #assert isinstance(fl, NFlowExpr)
#         #self.when = when_cond      # attrib, may be None, ValueExpr
#         #self.flow = fl             # son, FlowExpr


# class NCluster(NExpr):
#     """ Parallel composition of components """
#     def __init__(self):
#         # list of NClustItem in the cluster
#         self.items = []
    
#     def add_item(self, pp):
#         assert isinstance(pp, NClustItem), "it is {0}".format(pp.__class__.__name__)
#         self.items.append(pp)

#     def get_items(self):
#         return self.items


# class NClustItem(Node):
#     """ Item in the cluster. """
#     def __init__(self):
#         self.when = None       # optional NExpr, condition
#         self.flow = None       # NBlock or NExpr, typically NPipeline




# class NTubeLink(NExpr):
#     """ A tube opening """
#     def __init__(self):
#         self.f_implicit_in = False
#         self.f_implicit_out = False
    
#     def set_implicit_in(self, f):
#         self.f_implicit_in = f
    
#     def set_implicit_out(self, f):
#         self.f_implicit_out = f




# #class NLet(NFlowExpr):
#     #def __init__(self, value, loc=None):
#         #self.set_loc(loc)
#         #assert isinstance(value, NValueExpr)
#         #self.value = value           # son, expression
    
# class NModule(Node):
#     """ Module is a set of fun definitions. """
    
#     def __init__(self):
#         self.defs = []
    
#     def add_def(self, d):
#         assert isinstance(d, NDef)
#         self.defs.append(d)
    
#     def get_defs(self):
#         return self.defs


# class NDef(Node):
#     """ Definition of a symbol. Could be a value expression, type, flow. """
    
#     def __init__(self, name):
#         assert isinstance(name, NId)
#         self.name = name
#         self.params = None     # list of NParam
#         self.body = None       #
#         self.when = None       # optional NExpr, condition
    
#     def set_params(self, params):
#         assert isinstance(params, list)
#         for p in params: assert isinstance(p, NParam)
#         self.params = params
    
#     def set_body(self, body):
#         assert isinstance(body, (NValueExpr, NTypeSpec, NCluster))
#         self.body = body
    
#     def get_name(self):
#         return self.name


# class NParam(Node):
#     """ Formal parameter for a definition node. Holds name, type, and an optional default value. """
#     def __init__(self, name):
#         assert isinstance(name, NId)
#         self.name = name
#         self.default = None
    
#     def set_default(self, defv):
#         assert isinstance(defv, NValueExpr)
#         self.default = defv



# class NType(NExpr):
#     """ Base for types. Types can be named via NDef """
#     pass


# class NStructType(NType):
#     """ Structured type, such as record, union, cluster. """
#     def __init__(self):
#         self.fields = []       # list of NField


# class NPrimType(NType):
#     """ Primitive type. """
#     pass


# class NField(NParam):
#     pass

