#!/usr/bin/env python3
"""
fb_templates.py — Standard FB Template Library (Phase 27-C)

Contains Function Block templates commonly used in industrial automation.
Templates are written in Siemens SCL syntax (S7-1500 compatible).

Available templates:
  - FB_Motor      : 3-phase motor control (Start/Stop/E-Stop/Fault)
  - FB_Valve      : Pneumatic/electromechanical valve control
  - FB_Counter    : Product/item counter (preset + reset)
  - FB_PID_Wrapper: Basic PID wrapper (calls CONT_C)
  - FB_Watchdog   : System watchdog timer
  - FB_ModeManager: Operation mode manager (Auto/Manual/Maint)

CLI:
  python fb_templates.py --list
  python fb_templates.py --template FB_Motor --output FILE.scl
  python fb_templates.py --project PROJECT_PATH --template FB_Motor
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional


# -- Template records ---------------------------------------------------------

@dataclass
class FBTemplate:
    name: str
    description: str
    category: str        # Motor / Valve / Counter / Control / System
    tags: list[str]
    scl: str


# -- SCL Templates ------------------------------------------------------------

_FB_MOTOR = """\
(* ===============================================================
   FB_Motor — Standard 3-Phase Motor Control
   AUTOMATION_FACTORY Standard Template v1.0
   ===============================================================
   Features:
     - Start / Stop commands
     - Emergency stop (E_Stop) — priority
     - Field feedback (Running_FB, Fault_FB)
     - Start timeout (Start_Timeout)
     - Latching fault memory (Latch) + external reset
   VAR_IN connections:
     Start_Cmd    -> HMI / higher-level logic
     Stop_Cmd     -> HMI / higher-level logic
     E_Stop       -> Safety PLC or hardware relay
     Running_FB   -> Motor thermal or contactor aux contact
     Fault_FB     -> Drive / thermal protection output
   VAR_OUT connections:
     Motor_Out    -> Contactor coil or drive enable
     Running_State -> HMI visualization
     Fault_State   -> HMI / alarm system
   --------------------------------------------------------------- *)

FUNCTION_BLOCK "FB_Motor"
{ S7_Optimized_Access := 'TRUE' }
AUTHOR : AUTOMATION_FACTORY
VERSION : 1.0

VAR_INPUT
    Start_Cmd   : BOOL;   // Start command
    Stop_Cmd    : BOOL;   // Stop command
    E_Stop      : BOOL;   // Emergency stop (TRUE = stopping)
    Running_FB  : BOOL;   // Motor running feedback
    Fault_FB    : BOOL;   // Motor fault feedback
    Reset_Fault : BOOL;   // Fault reset command
    Start_Timeout_s : REAL := 5.0;  // Start timeout (s)
END_VAR

VAR_OUTPUT
    Motor_Out     : BOOL;   // Motor output command
    Running_State : BOOL;   // Running state
    Fault_State   : BOOL;   // Fault state
    Timeout_State : BOOL;   // Timeout state
END_VAR

VAR
    _start_timer  : TON;
    _fault_latch  : BOOL;
    _run_request  : BOOL;
END_VAR

BEGIN
    // Emergency stop priority
    IF E_Stop THEN
        _run_request := FALSE;
        _fault_latch := FALSE;
        Timeout_State := FALSE;
    ELSE
        // Command logic
        IF Start_Cmd AND NOT _fault_latch THEN
            _run_request := TRUE;
        END_IF;
        IF Stop_Cmd THEN
            _run_request := FALSE;
        END_IF;

        // Fault detection — latching
        IF Fault_FB THEN
            _fault_latch := TRUE;
            _run_request := FALSE;
        END_IF;
        IF Reset_Fault AND NOT Fault_FB THEN
            _fault_latch := FALSE;
            Timeout_State := FALSE;
        END_IF;

        // Start timeout
        _start_timer(
            IN  := _run_request AND NOT Running_FB AND NOT _fault_latch,
            PT  := REAL_TO_TIME(Start_Timeout_s * 1000.0),
        );
        IF _start_timer.Q THEN
            _fault_latch := TRUE;
            Timeout_State := TRUE;
            _run_request  := FALSE;
        END_IF;
    END_IF;

    // Assign outputs
    Motor_Out     := _run_request AND NOT _fault_latch AND NOT E_Stop;
    Running_State := Running_FB AND Motor_Out;
    Fault_State   := _fault_latch;

END_FUNCTION_BLOCK
"""

_FB_VALVE = """\
(* ===============================================================
   FB_Valve — Pneumatic / Electromechanical Valve Control
   AUTOMATION_FACTORY Standard Template v1.0
   ===============================================================
   Features:
     - Open / Close commands
     - Open / Closed position feedback (reed switch / limit sw)
     - Stroke timeout (Stroke_Timeout)
     - Position discrepancy alarm
     - E-Stop: drive to safe position (failsafe direction configurable)
   --------------------------------------------------------------- *)

FUNCTION_BLOCK "FB_Valve"
{ S7_Optimized_Access := 'TRUE' }
AUTHOR : AUTOMATION_FACTORY
VERSION : 1.0

VAR_INPUT
    Open_Cmd         : BOOL;    // Open command
    Close_Cmd        : BOOL;    // Close command
    E_Stop           : BOOL;    // Emergency stop
    Open_FB          : BOOL;    // Open position feedback
    Closed_FB        : BOOL;    // Closed position feedback
    Reset_Fault      : BOOL;    // Fault reset
    Failsafe_Open    : BOOL := FALSE;  // TRUE = open on E-Stop, FALSE = close
    Stroke_Timeout_s : REAL := 10.0;  // Stroke timeout (s)
END_VAR

VAR_OUTPUT
    Open_Out        : BOOL;   // Open output command (solenoid)
    Close_Out       : BOOL;   // Close output command (solenoid)
    Open_State      : BOOL;   // Open state (FB confirmed)
    Closed_State    : BOOL;   // Closed state (FB confirmed)
    Moving_State    : BOOL;   // Moving
    Fault_State     : BOOL;   // Fault (timeout / discrepancy)
END_VAR

VAR
    _open_request  : BOOL;
    _fault_latch   : BOOL;
    _move_timer    : TON;
END_VAR

BEGIN
    // E-Stop — drive to failsafe direction
    IF E_Stop THEN
        _open_request := Failsafe_Open;
    ELSE
        IF Open_Cmd  THEN _open_request := TRUE;  END_IF;
        IF Close_Cmd THEN _open_request := FALSE; END_IF;
    END_IF;

    // Fault reset
    IF Reset_Fault AND NOT Fault_FB THEN
        _fault_latch := FALSE;
    END_IF;

    // Stroke timeout
    Moving_State := (_open_request AND NOT Open_FB) OR (NOT _open_request AND NOT Closed_FB);
    _move_timer(
        IN := Moving_State AND NOT _fault_latch,
        PT := REAL_TO_TIME(Stroke_Timeout_s * 1000.0),
    );
    IF _move_timer.Q THEN
        _fault_latch := TRUE;
    END_IF;

    // Discrepancy alarm (both feedbacks at the same time)
    IF Open_FB AND Closed_FB THEN
        _fault_latch := TRUE;
    END_IF;

    // Outputs
    Open_Out     := _open_request  AND NOT _fault_latch;
    Close_Out    := NOT _open_request AND NOT _fault_latch;
    Open_State   := Open_FB  AND Open_Out;
    Closed_State := Closed_FB AND Close_Out;
    Fault_State  := _fault_latch;

END_FUNCTION_BLOCK
"""

_FB_COUNTER = """\
(* ===============================================================
   FB_Counter — Product / Item Counter
   AUTOMATION_FACTORY Standard Template v1.0
   ===============================================================
   Features:
     - Rising-edge counting (pulse)
     - Output at preset value (Count_Done)
     - Reset
     - Count direction selection (Up/Down)
   --------------------------------------------------------------- *)

FUNCTION_BLOCK "FB_Counter"
{ S7_Optimized_Access := 'TRUE' }
AUTHOR : AUTOMATION_FACTORY
VERSION : 1.0

VAR_INPUT
    Pulse       : BOOL;         // Count pulse (rising edge)
    Reset       : BOOL;         // Reset the counter
    Preset      : INT := 100;   // Target count
    Count_Down  : BOOL := FALSE; // TRUE = count down
END_VAR

VAR_OUTPUT
    Count_Value : INT;    // Current counter value
    Count_Done  : BOOL;   // Equal to or past preset
END_VAR

VAR
    _prev_pulse : BOOL;
END_VAR

BEGIN
    // Reset
    IF Reset THEN
        Count_Value := 0;
        Count_Done  := FALSE;
        _prev_pulse := FALSE;
        RETURN;
    END_IF;

    // Rising-edge detection
    IF Pulse AND NOT _prev_pulse THEN
        IF Count_Down THEN
            Count_Value := Count_Value - 1;
        ELSE
            Count_Value := Count_Value + 1;
        END_IF;
    END_IF;
    _prev_pulse := Pulse;

    // Done state
    IF Count_Down THEN
        Count_Done := Count_Value <= 0;
    ELSE
        Count_Done := Count_Value >= Preset;
    END_IF;

END_FUNCTION_BLOCK
"""

_FB_WATCHDOG = """\
(* ===============================================================
   FB_Watchdog — System Watchdog Timer
   AUTOMATION_FACTORY Standard Template v1.0
   ===============================================================
   Features:
     - Periodic trigger check
     - If no trigger arrives, Watchdog_Trip=TRUE
     - Cleared by a manual reset
   --------------------------------------------------------------- *)

FUNCTION_BLOCK "FB_Watchdog"
{ S7_Optimized_Access := 'TRUE' }
AUTHOR : AUTOMATION_FACTORY
VERSION : 1.0

VAR_INPUT
    Trigger        : BOOL;          // Periodic trigger (must be pulsed every cycle)
    Timeout_ms     : TIME := T#2S;  // Timeout duration
    Reset          : BOOL;          // Fault reset
    Enable         : BOOL := TRUE;  // Enable the watchdog
END_VAR

VAR_OUTPUT
    Watchdog_OK   : BOOL;  // System healthy (not tripped)
    Watchdog_Trip : BOOL;  // Timeout — intervention required
END_VAR

VAR
    _wd_timer  : TON;
    _triggered : BOOL;
END_VAR

BEGIN
    IF NOT Enable THEN
        Watchdog_OK   := TRUE;
        Watchdog_Trip := FALSE;
        RETURN;
    END_IF;

    // Capture the trigger rising edge
    IF Trigger AND NOT _triggered THEN
        _triggered := TRUE;
    END_IF;

    // TON: counts when there is no trigger, resets when triggered
    _wd_timer(
        IN := NOT _triggered,
        PT := Timeout_ms,
    );

    IF _triggered THEN
        _triggered := FALSE;
    END_IF;

    // Timeout
    IF _wd_timer.Q THEN
        Watchdog_Trip := TRUE;
    END_IF;

    // Reset
    IF Reset AND NOT _wd_timer.Q THEN
        Watchdog_Trip := FALSE;
    END_IF;

    Watchdog_OK := NOT Watchdog_Trip;

END_FUNCTION_BLOCK
"""

_FB_MODE_MANAGER = """\
(* ===============================================================
   FB_ModeManager — Operation Mode Manager
   AUTOMATION_FACTORY Standard Template v1.0
   ===============================================================
   Modes: 0=Stop / 1=Auto / 2=Manual / 3=Maintenance
   Features:
     - Mode transition condition check
     - Active mode outputs
     - Authorization level check (optional)
   --------------------------------------------------------------- *)

FUNCTION_BLOCK "FB_ModeManager"
{ S7_Optimized_Access := 'TRUE' }
AUTHOR : AUTOMATION_FACTORY
VERSION : 1.0

VAR_INPUT
    Req_Stop        : BOOL;  // Stop mode request
    Req_Auto        : BOOL;  // Automatic mode request
    Req_Manual      : BOOL;  // Manual mode request
    Req_Maint       : BOOL;  // Maintenance mode request
    Allow_Auto      : BOOL := TRUE;  // Permission to enter Auto mode (ready OK)
    Allow_Maint     : BOOL := FALSE; // Permission to enter Maintenance mode (password etc.)
    E_Stop          : BOOL;          // Emergency stop -> force Stop
END_VAR

VAR_OUTPUT
    Mode_Active     : INT;   // 0=Stop 1=Auto 2=Manual 3=Maint
    Is_Stop         : BOOL;
    Is_Auto         : BOOL;
    Is_Manual       : BOOL;
    Is_Maint        : BOOL;
    Mode_Changed    : BOOL;  // Mode changed (single-cycle pulse)
END_VAR

VAR
    _prev_mode : INT;
END_VAR

BEGIN
    _prev_mode := Mode_Active;

    // Emergency stop -> Stop mode
    IF E_Stop THEN
        Mode_Active := 0;
    ELSE
        IF Req_Maint AND Allow_Maint THEN
            Mode_Active := 3;
        ELSIF Req_Auto AND Allow_Auto THEN
            Mode_Active := 1;
        ELSIF Req_Manual THEN
            Mode_Active := 2;
        ELSIF Req_Stop THEN
            Mode_Active := 0;
        END_IF;
    END_IF;

    // Mode outputs
    Is_Stop   := (Mode_Active = 0);
    Is_Auto   := (Mode_Active = 1);
    Is_Manual := (Mode_Active = 2);
    Is_Maint  := (Mode_Active = 3);

    // Change pulse
    Mode_Changed := (Mode_Active <> _prev_mode);

END_FUNCTION_BLOCK
"""


# -- Template catalog ---------------------------------------------------------
# (tags keep both English and Turkish keywords to match device descriptions
#  in either language)

TEMPLATE_CATALOG: dict[str, FBTemplate] = {
    "FB_Motor": FBTemplate(
        name="FB_Motor",
        description="3-phase motor control (Start/Stop/E-Stop/Timeout/Fault)",
        category="Motor",
        tags=["motor", "pump", "pompa", "fan", "kompresör", "Drive"],
        scl=_FB_MOTOR,
    ),
    "FB_Valve": FBTemplate(
        name="FB_Valve",
        description="Pneumatic/electromechanical valve (Open/Close/Timeout/Discrepancy)",
        category="Valve",
        tags=["valve", "valf", "actuator", "solenoid"],
        scl=_FB_VALVE,
    ),
    "FB_Counter": FBTemplate(
        name="FB_Counter",
        description="Product counter (preset / up-down / reset)",
        category="Counter",
        tags=["counter", "sayaç", "adet", "product"],
        scl=_FB_COUNTER,
    ),
    "FB_Watchdog": FBTemplate(
        name="FB_Watchdog",
        description="System watchdog timer (periodic trigger)",
        category="System",
        tags=["watchdog", "bekçi", "heartbeat", "timeout"],
        scl=_FB_WATCHDOG,
    ),
    "FB_ModeManager": FBTemplate(
        name="FB_ModeManager",
        description="Operation mode manager (Stop/Auto/Manual/Maint)",
        category="System",
        tags=["mode", "mod", "operasyon", "manual", "auto"],
        scl=_FB_MODE_MANAGER,
    ),
}


# -- API Functions ------------------------------------------------------------

def list_templates() -> list[FBTemplate]:
    return list(TEMPLATE_CATALOG.values())


def get_template(name: str) -> Optional[FBTemplate]:
    # Case-insensitive lookup
    return TEMPLATE_CATALOG.get(name) or TEMPLATE_CATALOG.get(name.upper()) or \
        next((t for t in TEMPLATE_CATALOG.values() if t.name.lower() == name.lower()), None)


def install_template(
    template_name: str,
    project_path: Path,
    overwrite: bool = False,
    custom_name: str = "",
) -> dict:
    """
    Copy template to project _output/scl/ folder.
    Returns: {"success": bool, "path": Path|None, "message": str}
    """
    tmpl = get_template(template_name)
    if not tmpl:
        return {"success": False, "path": None, "message": f"Template not found: {template_name}"}

    scl_dir = project_path / "_output" / "scl"
    scl_dir.mkdir(parents=True, exist_ok=True)

    fname = f"{custom_name or tmpl.name}.scl"
    out_path = scl_dir / fname

    if out_path.exists() and not overwrite:
        return {
            "success": False,
            "path": out_path,
            "message": f"File already exists: {fname} (use --overwrite to replace)",
        }

    out_path.write_text(tmpl.scl, encoding="utf-8")
    return {"success": True, "path": out_path, "message": f"Copied: {fname}"}


def format_catalog_list() -> str:
    lines = ["FB Template Library", ""]
    cats: dict[str, list[FBTemplate]] = {}
    for t in TEMPLATE_CATALOG.values():
        cats.setdefault(t.category, []).append(t)
    for cat, tmpls in sorted(cats.items()):
        lines.append(f"  {cat}:")
        for t in tmpls:
            lines.append(f"    {t.name:<20} — {t.description}")
    return "\n".join(lines)


# -- CLI ----------------------------------------------------------------------

def main():
    import argparse
    p = argparse.ArgumentParser(description="FB Template Library")
    p.add_argument("--list", action="store_true", help="List all templates")
    p.add_argument("--template", metavar="NAME", help="Template name")
    p.add_argument("--project", metavar="PROJECT_PATH")
    p.add_argument("--output", metavar="FILE.scl", help="Write directly to file")
    p.add_argument("--overwrite", action="store_true")
    args = p.parse_args()

    if args.list:
        print(format_catalog_list())
        return

    if args.template:
        tmpl = get_template(args.template)
        if not tmpl:
            print(f"Template not found: {args.template}")
            return
        if args.output:
            Path(args.output).write_text(tmpl.scl, encoding="utf-8")
            print(f"Written: {args.output}")
        elif args.project:
            res = install_template(args.template, Path(args.project), overwrite=args.overwrite)
            print(f"{'[OK]' if res['success'] else '[FAIL]'} {res['message']}")
        else:
            print(tmpl.scl)
        return

    p.print_help()


if __name__ == "__main__":
    main()
