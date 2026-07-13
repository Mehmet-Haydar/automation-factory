---
status: DRAFT_UNVERIFIED
source: ai_preanalysis
rd: RD13
generated_at: 2026-07-12T18:25:02+00:00
model: deepseek-chat
step: RD13 Legacy Annotation Draft
---

> **Status: DRAFT_UNVERIFIED** — AI-generated draft from Retrofit
> Pre-Analysis. An engineer MUST verify every row against the real
> machine and set `status:` to `done`/`approved` before the gate
> can advance. Addresses and safety flags are NOT trustworthy yet.

Here is the RD13 Annotation Draft for the legacy PLC code, presented in the requested Markdown table format.

| Block | Networks/Lines | Meaning | Modern Equivalent | Risk | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **FC 10** | NW1: 4 lines | Safety chain: Two normally-closed (NC) E-Stop pushbuttons (E1.0, E1.1) are ANDed with a maintenance bypass flag (M50.0). The result drives the main contactor (A3.7). | Safety PLC (F-CPU) with dual-channel, test-pulsed inputs. A dedicated safety relay or F-DO for the main contactor. The maintenance bypass must be key-switched and logged. | **HIGH** | DRAFT_UNVERIFIED |
| **FC 10** | NW2: 3 lines | Light curtain (E1.2, NC) is ANDed with the inverted maintenance bypass (M50.0) to create a loading release (M60.0). | Safety PLC function block for light curtain muting, or a dedicated safety relay with muting lamp. | **HIGH** | DRAFT_UNVERIFIED |
| **FC 20** | NW1: 2 lines | Reads the selector switch (E0.2) and stores the state in a global bit (M10.7). 1 = AUTO, 0 = HAND. | Directly use the input in the program or a system-defined operating mode word (e.g., OB100). | **LOW** | DRAFT_UNVERIFIED |
| **FC 30** | NW1: 6 lines | Step 10: Start filling. Triggered by start button (E0.0) in AUTO mode (M10.7) with safety chain OK (A3.7) and no other step active. Sets step bit M20.0 and opens inlet valve (A0.4). | S7-GRAPH or a structured state machine (e.g., CASE statement in SCL). | **LOW** | DRAFT_UNVERIFIED |
| **FC 30** | NW2: 4 lines | Transition 10→20: When step 10 is active and high level (E2.1) is reached, reset step 10 and set step 20. | S7-GRAPH transition condition. | **LOW** | DRAFT_UNVERIFIED |
| **FC 30** | NW3: 5 lines | Step 20: Mixing. Starts a 30-second timer (T5). When T5 expires, reset step 20 and set step 30. | S7-GRAPH step with a timer in the action. | **LOW** | DRAFT_UNVERIFIED |
| **FC 30** | NW4: 4 lines | Step 30: Emptying. When low level (E2.0) is reached, reset step 30 (cycle ends). | S7-GRAPH step with a transition condition. | **LOW** | DRAFT_UNVERIFIED |
| **FC 40** | NW1: 3 lines | Request mixer: Active only in step 20 (M20.1) and motor protection switch (E0.4, NC) is not tripped. Stores in M30.0. | Standard motor control FB (e.g., MOTOR in TIA Portal). | **LOW** | DRAFT_UNVERIFIED |
| **FC 40** | NW2: 4 lines | Main contactor (A0.3) follows request. Starts a 6-second timer (T1) for star time. | Part of a standard star-delta function block. | **LOW** | DRAFT_UNVERIFIED |
| **FC 40** | NW3: 6 lines | Star contactor (A0.1) is on until T1 expires. Delta contactor (A0.2) is on after T1, with interlock (star must be off). | Part of a standard star-delta function block. | **LOW** | DRAFT_UNVERIFIED |
| **FC 50** | NW1: 2 lines | Reads analog input (EW64, 4-20mA) and stores raw value (0-27648) in MW100. | Standard analog input scaling block (e.g., NORM_X / SCALE_X). | **LOW** | DRAFT_UNVERIFIED |
| **FC 50** | NW2: 4 lines | Heater ON: If raw value < 15500 (approx. 60°C) AND step 20 is active (mixing), set heater output (A0.5). | PID controller or a two-point controller FB with hysteresis. | **LOW** | DRAFT_UNVERIFIED |
| **FC 50** | NW3: 3 lines | Heater OFF: If raw value > 16500, reset heater output (A0.5). | Part of the two-point controller logic. | **LOW** | DRAFT_UNVERIFIED |
| **FC 60** | NW1: 4 lines | Alarm: E-Stop triggered (E1.0 or E1.1 is 0). Sets DB30.DBX0.0. | Standard alarm block with a rising edge trigger. | **LOW** | DRAFT_UNVERIFIED |
| **FC 60** | NW2: 2 lines | Alarm: Mixer motor protection (E0.4) is 0. Sets DB30.DBX0.1. | Standard alarm block. | **LOW** | DRAFT_UNVERIFIED |
| **FC 60** | NW3: 4 lines | Collective fault: OR of the two alarm bits. Drives the fault lamp (A0.6). | Standard alarm word or HMI alarm group. | **LOW** | DRAFT_UNVERIFIED |
| **FC 70** | NW1: 4 lines | Conveyor belt: Runs when loading release (M60.0) is true, motor protection (E0.3, NC) is not tripped, and safety chain (A3.7) is OK. | Standard motor control FB (e.g., MOTOR in TIA Portal). | **LOW** | DRAFT_UNVERIFIED |

## Unclear Sections

1.  **FC 10, NW1 & NW2: Maintenance Bypass (M50.0):** The variable `M50.0` is used as a "Wartungs-Bypass" (maintenance bypass) for both the E-Stop chain and the light curtain. The code does not show how this bit is set or reset. If it can be set by a standard HMI button or a simple toggle in the program, this represents a **critical safety violation** that bypasses all safety functions. The intended mechanism (e.g., key switch, password-protected HMI screen, hardware jumper) must be clarified and documented.
2.  **FC 30, NW3: Timer T5 Usage:** The timer T5 is used with an `SE` (on-delay) instruction. The logic `U T5` then triggers the transition to step 30. This means the step 20 (mixing) lasts exactly 30 seconds, regardless of whether the mixing process is complete. This is a fixed-time step, not a process-driven one. This is functionally clear but is a design choice that should be noted.
3.  **FC 50, NW2 & NW3: Heater Hysteresis:** The heater control uses a simple on/off comparison with a 1000-count deadband (15500 to 16500). The comment mentions a hysteresis of +/- 500, but the actual code uses a 1000-count window. The exact setpoint and hysteresis values are ambiguous and should be verified against the original specification.
4.  **FC 60, NW1: E-Stop Alarm Logic:** The alarm logic `UN E1.0 O UN E1.1` will set the alarm bit if *either* E-Stop is not pressed (i.e., the NC contact is closed). This is correct for detecting a "released" or "tripped" state. However, it does not differentiate between a normal, safe state (both E-Stops pressed in) and a fault state (one is released). A more robust alarm would check for a state change or a specific fault pattern.
5.  **General: Data Block DB30:** The alarm bits are written to `DB30.DBX 0.0` and `DB30.DBX 0.1`. The structure of DB30 is not defined in this code snippet. The mapping of these bits to HMI alarms or a higher-level SCADA system is unknown. The entire DB30 structure must be documented.
6.  **General: Motor Protection Logic (E0.3, E0.4):** The motor protection switches are used as NC (normally-closed) inputs. The logic `UN E0.3` means the motor runs when the input is 1 (switch not tripped). This is standard. However, the code does not include any latching or reset logic for a motor protection fault. If the switch trips, the motor will simply stop and restart automatically when the fault is cleared, which could be a safety or operational hazard. A fault latch with a manual reset is expected.