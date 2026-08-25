"""Deterministic publish gates for reconciled standard relations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RelationQualityReport:
    self_relations: list[tuple[int, int]]
    cycles: list[list[int]]
    missing_targets: list[int]
    reverse_chronology: list[tuple[int, int]]

    @property
    def is_publishable(self) -> bool:
        return not self.self_relations and not self.cycles and not self.missing_targets and not self.reverse_chronology


def validate_relation_edges(
    edges: list[tuple[int, int]],
    *,
    known_ids: set[int] | None = None,
    standard_years: dict[int, int | str | None] | None = None,
) -> RelationQualityReport:
    """Return self edges and directed cycles without mutating source evidence."""

    self_relations = sorted({edge for edge in edges if edge[0] == edge[1]})
    graph: dict[int, set[int]] = {}
    for source, target in edges:
        if source != target:
            graph.setdefault(source, set()).add(target)
            graph.setdefault(target, set())

    cycles: list[list[int]] = []
    visiting: list[int] = []
    active: set[int] = set()
    visited: set[int] = set()

    def walk(node: int) -> None:
        if node in active:
            start = visiting.index(node)
            cycle = visiting[start:] + [node]
            if cycle not in cycles:
                cycles.append(cycle)
            return
        if node in visited:
            return
        active.add(node)
        visiting.append(node)
        for target in sorted(graph.get(node, ())):
            walk(target)
        visiting.pop()
        active.remove(node)
        visited.add(node)

    for node in sorted(graph):
        walk(node)
    missing_targets = (
        sorted({target for _, target in edges if target not in known_ids})
        if known_ids is not None
        else []
    )
    reverse_chronology = []
    if standard_years is not None:
        def normalized_year(value: int | str | None) -> int | None:
            try:
                year = int(value) if value is not None else None
            except (TypeError, ValueError):
                return None
            if year is not None and 0 <= year < 100:
                return 2000 + year if year <= 30 else 1900 + year
            return year

        reverse_chronology = sorted({
            (source, target)
            for source, target in edges
            if normalized_year(standard_years.get(source)) is not None
            and normalized_year(standard_years.get(target)) is not None
            and normalized_year(standard_years.get(source)) > normalized_year(standard_years.get(target))
        })
    return RelationQualityReport(
        self_relations=self_relations,
        cycles=cycles,
        missing_targets=missing_targets,
        reverse_chronology=reverse_chronology,
    )
