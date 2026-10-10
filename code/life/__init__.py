"""Persona-life layer (M1/M2/M4/M5/M7) — deterministic skeleton.

Main loop (perceive -> retrieve -> plan -> act -> reflect) lives in `agent.py`;
Phase 3.5 settlement (L1..L7) in `settlement.py`; memory stream in `memory.py`.
The layer talks to the world only through `ports.KernelPort` (IF-1 / IF-2).

Run the offline demo:   python -m life.run_demo
Run the tests:          python -m life.tests.test_skeleton   (from code/)
"""
