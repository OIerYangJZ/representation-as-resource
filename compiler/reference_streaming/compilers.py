#!/usr/bin/env python3
"""Auditable reference implementations of the W1 upper constructions."""

from __future__ import annotations

from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any

from encoding.codec import (
    CircuitDAG,
    ControlState,
    FlatUpdateStream,
    IRField,
    IREdge,
    IRNode,
    Instruction,
    LiveWindow,
    ParameterEntry,
    ParameterLedger,
    StoreState,
    SymbolicParameter,
    UpdateRecord,
)
from instrumentation.event_trace import EventTraceWriter
from instrumentation.resource_accounting import ResourceSnapshot

from .model import RunConfig, encode_aggregate_output, encode_update_output


COMPILER_NAMES = (
    "echo",
    "full_aggregation",
    "hybrid_25",
    "hybrid_50",
    "hybrid_75",
    "ir_materializing",
)
HYBRID_FRACTIONS = {"hybrid_25": 0.25, "hybrid_50": 0.50, "hybrid_75": 0.75}


@dataclass
class _State:
    aggregates: dict[int, int] = field(default_factory=dict)
    ir_records: list[UpdateRecord] = field(default_factory=list)
    ir_nodes: list[IRNode] = field(default_factory=list)
    ir_edges: list[IREdge] = field(default_factory=list)
    ir_last_node: dict[int, int] = field(default_factory=dict)
    output_records: int = 0


def effective_fraction(config: RunConfig) -> float:
    if config.compiler == "echo":
        return 0.0
    if config.compiler in {"full_aggregation", "ir_materializing"}:
        return 1.0
    return HYBRID_FRACTIONS[config.compiler]


def cap_coordinates(config: RunConfig) -> int:
    fraction = effective_fraction(config)
    if fraction == 0:
        return 0
    return min(config.m, max(1, __import__("math").ceil(fraction * config.m)))


def selected_coordinates(config: RunConfig) -> int:
    if config.compiler in {"full_aggregation", "ir_materializing"}:
        return config.m
    return min(config.m, config.passes * cap_coordinates(config))


def expected_output_records(config: RunConfig) -> int:
    if config.compiler == "echo":
        return config.m * config.r
    if config.compiler in {"full_aggregation", "ir_materializing"}:
        return config.m
    selected = selected_coordinates(config)
    return selected + (config.m - selected) * config.r


def _active_block(config: RunConfig, pass_index: int) -> tuple[int, int]:
    if config.compiler == "full_aggregation":
        return (0, config.m) if pass_index == 0 else (0, 0)
    if config.compiler == "ir_materializing":
        return (0, config.m) if pass_index == 0 else (0, 0)
    if config.compiler == "echo":
        return (0, 0)
    cap = cap_coordinates(config)
    start = min(config.m, pass_index * cap)
    return start, min(config.m, start + cap)


def _snapshot(
    config: RunConfig,
    state: _State,
    *,
    pass_index: int,
    input_position: int,
    active_block: tuple[int, int],
    current: UpdateRecord | None,
    phase: str,
) -> ResourceSnapshot:
    control = ControlState(
        {
            "schema": "ucc.reference-restart-state.v1",
            "compiler": config.compiler,
            "m": config.m,
            "r": config.r,
            "K": config.K,
            "Q": config.Q,
            "pass_count": config.passes,
            "pass_index": pass_index,
            "input_position": input_position,
            "active_block_start": active_block[0],
            "active_block_stop": active_block[1],
            "output_records": state.output_records,
            "phase": phase,
        }
    )
    store = StoreState(
        {
            "mode": config.compiler,
            "aggregate_layout": "public-consecutive-base-Q-block",
            "aggregate_slots": active_block[1] - active_block[0]
            if config.compiler not in {"echo", "ir_materializing"}
            else 0,
            "ir_node_count": len(state.ir_nodes),
        }
    )
    window = LiveWindow(
        ()
        if current is None
        else (
            Instruction(
                "qary_update",
                (current.generator,),
                current.support,
                (current.parameter,),
                {"round_index": current.round_index},
            ),
        )
    )
    entries: list[ParameterEntry] = []
    if config.compiler not in {"echo", "ir_materializing"} and active_block[0] < active_block[1]:
        packed = 0
        place = 1
        for generator in range(active_block[0], active_block[1]):
            packed += state.aggregates.get(generator, 0) * place
            place *= config.Q
        entries.append(
            ParameterEntry(
                (0, active_block[0], active_block[1]),
                SymbolicParameter(Fraction(packed)),
            )
        )
    entries.extend(
        ParameterEntry((1, node.node_id, 0), state.ir_records[index].parameter)
        for index, node in enumerate(state.ir_nodes)
    )
    if current is not None:
        entries.append(ParameterEntry((2, pass_index, input_position, 0), current.parameter))
    parameter = ParameterLedger(tuple(entries))
    if state.ir_nodes:
        dag = CircuitDAG(
            config.m,
            tuple(state.ir_nodes),
            tuple(state.ir_edges),
            {"materialization": "input-update-dag"},
        )
        ir = IRField((dag,))
    else:
        ir = IRField()
    return ResourceSnapshot(
        control,
        store,
        window,
        parameter,
        ir,
        b"",
        pass_count=config.passes,
        pass_index=pass_index,
    )


def _record(
    trace: EventTraceWriter,
    config: RunConfig,
    state: _State,
    *,
    event_kind: str,
    input_position: int,
    pass_index: int,
    round_index: int | None,
    side: str,
    active_block: tuple[int, int],
    current: UpdateRecord | None = None,
    crossing: str | None = None,
    phase: str,
    details: dict[str, Any] | None = None,
) -> None:
    trace.record_event(
        _snapshot(
            config,
            state,
            pass_index=pass_index,
            input_position=input_position,
            active_block=active_block,
            current=current,
            phase=phase,
        ),
        event_kind=event_kind,
        input_position=input_position,
        pass_index=pass_index,
        round_index=round_index,
        side=side,
        crossing=crossing,
        details=details,
    )


def _materialize_ir(state: _State, record: UpdateRecord) -> None:
    node_id = len(state.ir_nodes)
    instruction = Instruction(
        "qary_update",
        (record.generator,),
        record.support,
        (record.parameter,),
        {"round_index": record.round_index},
    )
    state.ir_nodes.append(IRNode(node_id, instruction))
    state.ir_records.append(record)
    previous = state.ir_last_node.get(record.generator)
    if previous is not None:
        state.ir_edges.append(IREdge(previous, node_id, 0))
    state.ir_last_node[record.generator] = node_id


def _emit_aggregates(
    trace: EventTraceWriter,
    config: RunConfig,
    state: _State,
    generators: range,
    *,
    pass_index: int,
    input_position: int,
    active_block: tuple[int, int],
) -> None:
    for generator in generators:
        residue = state.aggregates.get(generator, 0) % config.Q
        trace.append_output(encode_aggregate_output(generator, residue))
        state.output_records += 1
        _record(
            trace,
            config,
            state,
            event_kind="output_commit",
            input_position=input_position,
            pass_index=pass_index,
            round_index=config.r - 1,
            side="B",
            active_block=active_block,
            phase="emit_aggregate",
            details={"generator": generator, "record_kind": "aggregate"},
        )


def execute_compiler(config: RunConfig, flat: FlatUpdateStream, trace: EventTraceWriter) -> dict[str, Any]:
    """Execute exactly ``passes`` forward scans and record every update/crossing."""

    if config.compiler not in COMPILER_NAMES:
        raise ValueError(f"unknown compiler {config.compiler!r}")
    if abs(config.memory_fraction - effective_fraction(config)) > 1e-12:
        raise ValueError("declared memory_fraction does not match the compiler's public strategy")
    if flat.width != config.m or flat.rounds != config.r:
        raise ValueError("flat input declaration differs from run config")
    state = _State()
    _record(
        trace,
        config,
        state,
        event_kind="setup",
        input_position=0,
        pass_index=0,
        round_index=None,
        side="A",
        active_block=_active_block(config, 0),
        phase="setup",
        details={"header_committed": True},
    )

    selected = selected_coordinates(config)
    for pass_index in range(config.passes):
        active = _active_block(config, pass_index)
        state.aggregates.clear()
        if config.compiler == "ir_materializing" and pass_index == 0:
            state.ir_records.clear()
            state.ir_nodes.clear()
            state.ir_edges.clear()
            state.ir_last_node.clear()
        for input_position, record in enumerate(flat.records, start=1):
            side = "A" if record.round_index < config.r - 1 else "B"
            if config.compiler == "echo":
                if pass_index == 0:
                    trace.append_output(encode_update_output(record))
                    state.output_records += 1
            elif config.compiler == "full_aggregation":
                if pass_index == 0:
                    state.aggregates[record.generator] = (
                        state.aggregates.get(record.generator, 0) + record.parameter.constant.numerator
                    ) % config.Q
            elif config.compiler in HYBRID_FRACTIONS:
                if active[0] <= record.generator < active[1]:
                    state.aggregates[record.generator] = (
                        state.aggregates.get(record.generator, 0) + record.parameter.constant.numerator
                    ) % config.Q
                elif pass_index == 0 and record.generator >= selected:
                    trace.append_output(encode_update_output(record))
                    state.output_records += 1
            elif config.compiler == "ir_materializing" and pass_index == 0:
                _materialize_ir(state, record)

            _record(
                trace,
                config,
                state,
                event_kind="input_update",
                input_position=input_position,
                pass_index=pass_index,
                round_index=record.round_index,
                side=side,
                active_block=active,
                current=record,
                phase="post_update",
                details={"generator": record.generator, "record_kind": "update"},
            )
            if record.round_index == config.r - 2 and input_position % config.m == 0:
                _record(
                    trace,
                    config,
                    state,
                    event_kind="crossing",
                    input_position=input_position,
                    pass_index=pass_index,
                    round_index=record.round_index,
                    side="A",
                    active_block=active,
                    crossing="A_to_B",
                    phase="cross_A_to_B",
                )

        if config.compiler == "full_aggregation" and pass_index == 0:
            _emit_aggregates(
                trace,
                config,
                state,
                range(config.m),
                pass_index=pass_index,
                input_position=len(flat.records),
                active_block=active,
            )
        elif config.compiler in HYBRID_FRACTIONS and active[0] < active[1]:
            _emit_aggregates(
                trace,
                config,
                state,
                range(active[0], active[1]),
                pass_index=pass_index,
                input_position=len(flat.records),
                active_block=active,
            )
        elif config.compiler == "ir_materializing" and pass_index == 0:
            totals = {generator: 0 for generator in range(config.m)}
            for record in state.ir_records:
                totals[record.generator] = (totals[record.generator] + record.parameter.constant.numerator) % config.Q
            state.aggregates = totals
            _emit_aggregates(
                trace,
                config,
                state,
                range(config.m),
                pass_index=pass_index,
                input_position=len(flat.records),
                active_block=active,
            )

        state.aggregates.clear()
        state.ir_records.clear()
        state.ir_nodes.clear()
        state.ir_edges.clear()
        state.ir_last_node.clear()
        if pass_index < config.passes - 1:
            _record(
                trace,
                config,
                state,
                event_kind="crossing",
                input_position=len(flat.records),
                pass_index=pass_index,
                round_index=config.r - 1,
                side="B",
                active_block=(0, 0),
                crossing="B_to_A",
                phase="cross_B_to_A",
            )

    _record(
        trace,
        config,
        state,
        event_kind="complete",
        input_position=len(flat.records),
        pass_index=config.passes - 1,
        round_index=config.r - 1,
        side="B",
        active_block=(0, 0),
        phase="complete",
    )
    if state.output_records != expected_output_records(config):
        raise ValueError(
            f"compiler emitted {state.output_records} records; expected {expected_output_records(config)}"
        )
    return {
        "compiler": config.compiler,
        "passes_executed": config.passes,
        "cap_coordinates_per_pass": cap_coordinates(config),
        "selected_coordinates": selected,
        "output_records": state.output_records,
    }


__all__ = [
    "COMPILER_NAMES",
    "HYBRID_FRACTIONS",
    "cap_coordinates",
    "effective_fraction",
    "execute_compiler",
    "expected_output_records",
    "selected_coordinates",
]
