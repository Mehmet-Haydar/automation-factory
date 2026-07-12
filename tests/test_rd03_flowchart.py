"""rd03_flowchart: table parsing, deterministic mermaid derivation, and the
no-AI impact check used by the flowchart chat loop."""

from __future__ import annotations

from pathlib import Path

from workbench.core.rd03_flowchart import (
    FlowStep,
    generate_mermaid,
    impact_check,
    parse_flow_steps,
    parse_md_tables,
    replace_mermaid_block,
    steps_to_md_table,
)

RD03_SAMPLE = """---
project_id: TEST
status: DRAFT
---

# RD03_Flowchart — Test

## Flow Steps

| StepID | StepName | StepType | Description | EntryCondition | ExitCondition | Actions | NextStep | ErrorStep | TimerRef | ModeReq | ISA88Level | Notes | Status |
|--------|----------|----------|-------------|----------------|---------------|---------|----------|-----------|----------|---------|------------|-------|--------|
| S000 | Initial | Initial | Initial state | TRUE | Start_Cmd | All outputs := FALSE | S010 | | | AUTO,MAN | Phase | | Active |
| S010 | Tank_Fill | Normal | Tank filling | S000 done | Tank_Level > 80% | Open V_Fill | S020 | S099 | TMR_HOLD_001 | AUTO | Phase | | Active |
| S020 | Mixing | Normal | Mixing | S010 done | Mix_Time elapsed | Start Mixer | (end) | S099 | | AUTO | Phase | | Active |
| S099 | Error_Recovery | Final | Error state | Error active | Reset_Cmd | Stop all | (end) | | | ALL | Phase | | Active |

## Mermaid Diagram

```mermaid
stateDiagram-v2
    [*] --> OLD_CONTENT
```
"""


# ── parsing ──────────────────────────────────────────────────────────────────

def test_parse_flow_steps_reads_all_rows():
    steps = parse_flow_steps(RD03_SAMPLE)
    assert [s.step_id for s in steps] == ["S000", "S010", "S020", "S099"]
    assert steps[1].timer_ref == "TMR_HOLD_001"
    assert steps[1].error_step == "S099"
    assert steps[0].entry_condition == "TRUE"


def test_parse_skips_tables_without_stepid():
    md = "| Tag | Address |\n|---|---|\n| X | %I0.0 |\n"
    assert parse_flow_steps(md) == []


def test_parse_md_tables_ignores_code_fences():
    md = "```\n| not | a | table |\n|---|---|---|\n```\n| A | B |\n|---|---|\n| 1 | 2 |\n"
    tables = parse_md_tables(md)
    assert len(tables) == 1
    assert tables[0]["rows"] == [["1", "2"]]


def test_roundtrip_table_render():
    steps = parse_flow_steps(RD03_SAMPLE)
    again = parse_flow_steps("# t\n\n" + steps_to_md_table(steps))
    assert [s.step_id for s in again] == [s.step_id for s in steps]
    assert again[1].exit_condition == steps[1].exit_condition


# ── mermaid derivation ──────────────────────────────────────────────────────

def test_mermaid_basic_structure():
    mm = generate_mermaid(parse_flow_steps(RD03_SAMPLE))
    lines = mm.split("\n")
    assert mm.startswith("flowchart TD")
    assert "_s --> S000" in mm                                    # initial entry
    assert any("S000" in l and "S010" in l for l in lines)       # S000→S010 edge
    assert any("S020" in l and "_e" in l for l in lines)         # (end)→_e
    assert 'S010 -->|"Error"| S099' in mm                        # error edge
    assert "OLD_CONTENT" not in mm


def test_mermaid_alternative_branches():
    steps = [
        FlowStep(step_id="S000", step_type="Initial", entry_condition="TRUE",
                 next_step="S010A | S010B"),
        FlowStep(step_id="S010A", next_step="(end)"),
        FlowStep(step_id="S010B", next_step="(end)"),
    ]
    mm = generate_mermaid(steps)
    assert "S000 --> S010A" in mm
    assert "S000 --> S010B" in mm


def test_mermaid_label_sanitised():
    steps = [FlowStep(step_id="S000", step_name="A:B|C", step_type="Initial",
                      next_step="(end)", exit_condition="x > 1; y")]
    mm = generate_mermaid(steps)
    assert "A -B/C" in mm
    assert ";" not in mm.split("\n")[-1]


def test_replace_mermaid_block_swaps_existing():
    out = replace_mermaid_block(RD03_SAMPLE, "stateDiagram-v2\n    [*] --> S000")
    assert "OLD_CONTENT" not in out
    assert out.count("```mermaid") == 1
    assert "[*] --> S000" in out
    # the table is untouched
    assert "| S010 | Tank_Fill" in out


def test_replace_mermaid_block_appends_when_absent():
    md = "# RD03\n\n| StepID | NextStep |\n|---|---|\n| S000 | (end) |\n"
    out = replace_mermaid_block(md, "stateDiagram-v2")
    assert "## Mermaid Diagram" in out
    assert "```mermaid" in out


# ── impact check: graph integrity ───────────────────────────────────────────

def _codes(findings):
    return {f["code"] for f in findings}


def test_clean_table_no_graph_errors(tmp_path):
    findings = impact_check(parse_flow_steps(RD03_SAMPLE), None)
    assert not [f for f in findings if f["severity"] == "error"]


def test_missing_target_detected():
    steps = [FlowStep(step_id="S000", step_type="Initial",
                      entry_condition="TRUE", next_step="S999")]
    assert "MISSING_TARGET" in _codes(impact_check(steps))


def test_duplicate_step_detected():
    steps = [
        FlowStep(step_id="S000", step_type="Initial", next_step="(end)"),
        FlowStep(step_id="S000", next_step="(end)"),
    ]
    assert "DUP_STEP" in _codes(impact_check(steps))


def test_no_initial_detected():
    steps = [FlowStep(step_id="S010", next_step="(end)")]
    assert "NO_INITIAL" in _codes(impact_check(steps))


def test_unreachable_step_detected():
    steps = [
        FlowStep(step_id="S000", step_type="Initial", next_step="(end)"),
        FlowStep(step_id="S050", next_step="(end)"),
    ]
    assert "UNREACHABLE" in _codes(impact_check(steps))


def test_dead_end_detected():
    steps = [
        FlowStep(step_id="S000", step_type="Initial", next_step="S010"),
        FlowStep(step_id="S010", step_type="Normal", next_step=""),
    ]
    assert "DEAD_END" in _codes(impact_check(steps))


# ── impact check: RD cross-references ───────────────────────────────────────

def _metadata(tmp_path: Path) -> Path:
    md = tmp_path / "metadata"
    md.mkdir()
    (md / "RD01_IO_List.md").write_text(
        "| Tag | Address |\n|---|---|\n| Tank_Level | %IW64 |\n| V_Fill | %Q0.0 |\n",
        encoding="utf-8",
    )
    (md / "RD02_DataDict.md").write_text(
        "| VarName | Scope |\n|---|---|\n| Start_Cmd | GlobalDB |\n| Mix_Time | GlobalDB |\n| Reset_Cmd | GlobalDB |\n",
        encoding="utf-8",
    )
    (md / "RD07_Timing.md").write_text(
        "| TimerID | Name |\n|---|---|\n| TMR_HOLD_001 | Hold |\n",
        encoding="utf-8",
    )
    (md / "RD04_Mode.md").write_text(
        "| ModeID | ModeName | OldModeName |\n|---|---|---|\n"
        "| M01 | Auto | AUTO |\n| M02 | Manual | MAN |\n",
        encoding="utf-8",
    )
    return md


def test_known_references_pass(tmp_path):
    findings = impact_check(parse_flow_steps(RD03_SAMPLE), _metadata(tmp_path))
    assert "UNKNOWN_REF" not in _codes(findings)
    assert "UNKNOWN_TIMER" not in _codes(findings)
    assert "UNKNOWN_MODE" not in _codes(findings)


def test_missing_sensor_is_flagged(tmp_path):
    """The user-story case: a new step references a sensor that is not in
    RD01 — the check must say so explicitly."""
    steps = parse_flow_steps(RD03_SAMPLE)
    steps[2].exit_condition = "Sensor_X_Trig = TRUE"
    findings = impact_check(steps, _metadata(tmp_path))
    hits = [f for f in findings if f["code"] == "UNKNOWN_REF"]
    assert hits and "Sensor_X_Trig" in hits[0]["msg"]


def test_unknown_timer_is_flagged(tmp_path):
    steps = parse_flow_steps(RD03_SAMPLE)
    steps[1].timer_ref = "TMR_NEW_009"
    findings = impact_check(steps, _metadata(tmp_path))
    assert "UNKNOWN_TIMER" in _codes(findings)


def test_unknown_mode_is_flagged(tmp_path):
    steps = parse_flow_steps(RD03_SAMPLE)
    steps[1].mode_req = "TURBO"
    findings = impact_check(steps, _metadata(tmp_path))
    assert "UNKNOWN_MODE" in _codes(findings)


def test_rd01_missing_yields_info_not_warning(tmp_path):
    md = tmp_path / "metadata"
    md.mkdir()
    findings = impact_check(parse_flow_steps(RD03_SAMPLE), md)
    assert "RD01_MISSING" in _codes(findings)
    assert not [f for f in findings if f["code"] == "UNKNOWN_REF"]
