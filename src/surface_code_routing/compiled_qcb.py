'''
    Compiled QCB
    Binds a set of routing instructions to a QCB layout to create a callable  
'''
from surface_code_routing.symbol import symbol_resolve
from surface_code_routing.scope import Scope
from surface_code_routing.instructions import RESET, MOVE, IDLE

from surface_code_routing.dag import DAG
from surface_code_routing.qcb import QCB, SCPatch
from surface_code_routing.allocator import Allocator
from surface_code_routing.qcb_graph import QCBGraph
from surface_code_routing.qcb_tree import QCBTree
from surface_code_routing.router import QCBRouter
from surface_code_routing.mapper import QCBMapper

from surface_code_routing.circuit_model import PatchGraph
from surface_code_routing.inject_rotations import RotationInjector

def compile_qcb(dag, height, width,
                *externs,
                verbose=False,
                extern_allocation_method='dynamic',
                qcb_kwargs = None,
                allocator_kwargs = None,
                graph_kwargs = None,
                tree_kwargs = None,
                mapper_kwargs = None,
                patch_graph_kwargs = None,
                router_kwargs = None,
                compiled_qcb_kwargs = None
                ):

    if verbose:
        print(f"Compiling {dag}")
        print("\tConstructing QCB...")
    qcb = QCB(height, width, dag)
    dag.verbose=verbose

    if verbose:
        print("\tAllocating QCB...")
    allocator = Allocator(qcb, *externs, tikz_build=True, verbose=verbose)
    qcb.allocator = allocator

    if verbose:
        print("\tConstructing Mapping")
    graph = QCBGraph(qcb)
    tree = QCBTree(graph)

    if mapper_kwargs is None:
        mapper_kwargs = {'extern_allocation_method':extern_allocation_method}
    elif 'extern_allocation_method' not in mapper_kwargs:
        mapper_kwargs['extern_allocation_method'] = extern_allocation_method

    mapper = QCBMapper(dag, tree, **mapper_kwargs)

    if verbose:
        print("\tRouting...")
    circuit_model = PatchGraph(qcb.shape, mapper, None)
    # TODO pass this through
    rot_injector = RotationInjector(dag, mapper, qcb, graph=circuit_model, verbose=verbose)

    if router_kwargs is None:
        router_kwargs = dict()
    router = QCBRouter(qcb, dag, mapper, graph=circuit_model, verbose=verbose, **router_kwargs)

    if compiled_qcb_kwargs is None:
        compiled_qcb_kwargs = dict()
    compiled_qcb = CompiledQCB(qcb, router, dag, **compiled_qcb_kwargs)
    return compiled_qcb

class CompiledQCB:
    '''
        CompiledQCB
        Binds a set of routing instructions to a QCB layout to create a callable extern
        :: qcb : QCB :: QCB layout 
        :: route : Router :: Router object 
        :: dag :: DAG :: Dag that the router implements 
        :: readin_operation : Operation :: Operation mediating how to pass inputs to this extern 
        :: readout_operation : Operation :: Operation mediating how to pass outputs from this extern 

        TODO: Vtable implementation for calling and overloading 
            : Bind readin and readout on a per-symbol basis, possibly for each element in the calltable 
    '''
    def __init__(self, qcb, router, dag, readin_operation=MOVE, readout_operation=MOVE):
        self.dag = dag
        self.router = router
        self.qcb = qcb

        self.symbol = qcb.symbol.extern()
        self.n_cycles = lambda : len(router.layers)
        self.n_pre_warm_cycles = lambda : 0
        self.width = qcb.width
        self.height = qcb.height
        self.externs = qcb.externs
        self.predicate = qcb.symbol
        self.io = qcb.symbol.io
        self.io_in = self.dag.symbol.io_in
        self.io_out = self.dag.symbol.io_out
        self.__is_factory = len(self.io_in) == 0

        self.readin_operation = readin_operation
        self.readout_operation = readout_operation

    def __len__(self):
        return self.n_cycles()

    def is_extern(self):
        '''
            All compiled QCBs act as externs
        '''
        return True

    def is_factory(self):
        '''
            Not all compiled QCBs are factories
        '''
        return self.__is_factory

    def instantiate(self):
        '''
            Create a new instance of the QCB
        '''
        return CompiledQCB(self.qcb, self.router, self.dag)

    def satisfies(self, other):
        '''
            Determine if the QCB satisfies the dependencies of another gate
        '''
        return self.symbol.satisfies(other)

    def get_symbol(self):
        '''
            Gets the symbol of a QCB
        '''
        return self.symbol

    def get_obj(self):
        return self

    def __call__(self, *args):
        return self.instruction(*args)

    def __repr__(self):
        return self.symbol.__repr__()

    def delays(self):
        '''
            Cycles spent waiting for various operations
        '''
        if self.router is not None:
            return self.router.delays
        return dict() 

    def space_time_volume(self):
        '''
            Space_time_volume of QCB
        '''
        if self.router is not None:
            extern_volumes = sum(
                map(
                    lambda x: x.space_time_volume(),
                    self.dag.externs.values()
                )
            )
            return self.router.space_time_volume + extern_volumes
        return self.height * self.width * self.n_cycles 

    def instruction(self, args, targs):
        '''
            Simple wrapper that resolves a default call to the QCB
        '''
        # Overload this for persistent externs
        args = tuple(map(symbol_resolve, args))
        targs = tuple(map(symbol_resolve, targs))

        sym = symbol_resolve(f'CALL {self.predicate.symbol}')
        fn = self.predicate.extern(io_in=self.io_in, io_out=self.io_out)
        scope = Scope({fn:fn})

        dag = DAG(sym, scope=scope)

        readin_gates = set()
        for arg, fn_arg in zip(args, self.predicate.ordered_io_in()):
            readin_gates.add(dag.add_gate(self.readin_operation(arg, fn(fn_arg)))[0])

        # No readin
        if len(args) == 0:
            for targ in targs:
                readin_gates.add(dag.add_gate(IDLE(targ))[0])

        extern_gate = dag.add_node(fn, n_cycles=self.n_cycles())

        # Extern initiation is predicated on all inputs
        for gate in readin_gates:
            gate.antecedents.add(extern_gate) 
            extern_gate.predicates.add(gate)

        readout_gates = set() 
        for targ, fn_arg in zip(targs, self.predicate.ordered_io_out()):
            readout_gates.add(dag.add_gate(self.readout_operation(fn(fn_arg), targ))[0])

        # Unbind linearity of dependencies
        # This is more DAG surgery than I would normally like
        for gate in readout_gates:
            gate.predicates = set(
                filter(
                    lambda x: x not in readout_gates,
                    gate.predicates
                )
            )
            gate.antecedents = set(
                filter(
                    lambda x: x not in readout_gates,
                    gate.antecedents
               )
            )

            gate.predicates.add(extern_gate)

        extern_gate.antecedents |= readout_gates

        reset_gate = dag.add_gate(RESET(fn))[0]
        
        for gate in readout_gates:
            gate.antecedents.add(reset_gate)

        reset_gate.predicates |= readout_gates

        return dag

    def __tikz__(self):
        return self.router.__tikz__()
