#!/usr/bin/env python3
"""Benchmark md-context indexing and retrieval on a 2,000-note synthetic vault."""

import sys
import tempfile
import time
from pathlib import Path

from md_context import build_index, build_pack, load_index, save_index


def generate_vault(vault_dir: Path, note_count: int = 2000) -> None:
    tags_pool = ["architecture", "research", "database", "python", "notes", "planning", "security"]
    for i in range(note_count):
        tag1 = tags_pool[i % len(tags_pool)]
        tag2 = tags_pool[(i * 3 + 1) % len(tags_pool)]
        next_note = f"note_{((i + 1) % note_count):04d}"
        prev_note = f"note_{((i - 1) % note_count):04d}"
        content = f"""---
title: Synthetic Note {i:04d}
tags: [{tag1}, {tag2}]
date: 2026-01-{(i % 28) + 1:02d}
---
# Synthetic Note {i:04d}

This is note {i:04d} discussing system {tag1} and evaluation methods for {tag2}.
Cross references: [[{next_note}]] and [[{prev_note}]].

## Architecture overview

Section analyzing system architecture and modular component interactions.
Key term: keyword_{i % 50}.

## Implementation details

Details on data flow, token budget constraints, and caching mechanisms.
Further reading in [[{next_note}]].
"""
        (vault_dir / f"note_{i:04d}.md").write_text(content, encoding="utf-8")


def main() -> int:
    note_count = 2000
    query_count = 20
    print(f"Generating synthetic vault with {note_count} notes...")
    with tempfile.TemporaryDirectory() as tmp_dir:
        vault = Path(tmp_dir) / "benchmark_vault"
        vault.mkdir()
        t0 = time.perf_counter()
        generate_vault(vault, note_count=note_count)
        gen_time = time.perf_counter() - t0
        print(f"  Generated {note_count} notes in {gen_time:.2f} s")

        print("Benchmarking build_index...")
        t0 = time.perf_counter()
        index = build_index(vault)
        index_time = time.perf_counter() - t0
        print(f"  build_index: {index_time:.3f} s ({index.stats()['notes']} notes)")

        print("Benchmarking save_index and load_index...")
        t0 = time.perf_counter()
        save_index(index)
        save_time = time.perf_counter() - t0
        print(f"  save_index:  {save_time:.3f} s")

        t0 = time.perf_counter()
        loaded = load_index(vault)
        load_time = time.perf_counter() - t0
        print(f"  load_index:  {load_time:.3f} s")

        queries = [f"keyword_{k}" for k in range(query_count)]
        print(f"Benchmarking {len(queries)} queries...")
        t0 = time.perf_counter()
        first_query_time = 0.0
        for idx, q in enumerate(queries):
            q_start = time.perf_counter()
            pack = build_pack(loaded, q, budget=4000)
            q_elapsed = time.perf_counter() - q_start
            if idx == 0:
                first_query_time = q_elapsed
            assert len(pack.sources) > 0, f"Query '{q}' returned no sources"
        total_query_time = time.perf_counter() - t0
        avg_query_time = (total_query_time * 1000) / len(queries)

        print(f"  First query (with cache warmup): {first_query_time * 1000:.1f} ms")
        print(f"  Total for {len(queries)} queries:           {total_query_time:.3f} s")
        print(f"  Average query time:             {avg_query_time:.1f} ms/query")

        total_time = gen_time + index_time + save_time + load_time + total_query_time
        print(f"\nTotal benchmark elapsed time: {total_time:.2f} s")
        if total_time < 60.0:
            print("Benchmark completed in under 60 s! SUCCESS.")
            return 0
        else:
            print("Benchmark exceeded 60 s limit! FAILED.")
            return 1


if __name__ == "__main__":
    sys.exit(main())
