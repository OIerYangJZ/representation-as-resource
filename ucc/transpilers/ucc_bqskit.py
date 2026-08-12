try:
    from bqskit.compiler import Compiler
    from bqskit.ext.qiskit.translate import bqskit_to_qiskit, qiskit_to_bqskit
    from bqskit.passes import (
        ForEachBlockPass,
        QuickPartitioner,
        LEAPSynthesisPass,
        UnfoldPass,
    )
except ImportError:
    raise ImportError(
        "bqskit is required to use BQSKitTransformationPass but is not a dependency for ucc, so it is not installed by default. You can install it from pypi e.g. 'pip install bqskit' or 'uv add bqskit'."
    )

import qiskit.transpiler.basepasses
import qiskit.converters


class BQSKitTransformationPass(
    qiskit.transpiler.basepasses.TransformationPass
):
    def __init__(self, bqskit_passes=None):
        super().__init__()
        if bqskit_passes is None:
            self.bqskit_passes = self.default_passes()
        else:
            self.bqskit_passes = bqskit_passes

    def default_passes(self):
        return [
            QuickPartitioner(3),
            ForEachBlockPass(
                LEAPSynthesisPass(), replace_filter="less-than-multi"
            ),
            UnfoldPass(),
        ]

    def run(self, dag):
        circuit = qiskit_to_bqskit(qiskit.converters.dag_to_circuit(dag))
        with Compiler() as compiler:
            circuit = compiler.compile(circuit, self.bqskit_passes)
        return qiskit.converters.circuit_to_dag(bqskit_to_qiskit(circuit))
