---
title: RD06_Motion — Kunde Müller (placeholder)
last_validated: 2026-05
status: ACTIVE
---

# RD06_Motion — Kunde Müller (placeholder)

```yaml
status: DRAFT (30%)
```

## Summary
- 1 axis detected (Conveyor1 — SINAMICS G120 VFD)
- No servo axis (VFD only)

## Axes (draft)

| AxisID | AxisName | DriveType | DriveModel | Motor_Tag | Feedback_Tag | EngUnit | HomeMethod | PLCopenFBs | Status |
|--------|----------|-----------|------------|-----------|--------------|---------|------------|------------|--------|
| AX001 | Conveyor1_VFD | VFD_Profidrive | SINAMICS G120C | MOT_CV01_001_OUT | (no encoder, run feedback only) | rpm | None | MC_Power, MC_MoveVelocity, MC_Stop | DRAFT |

## Notes
- The old VFD is on PROFIBUS-DP slave 5 — the new project migrates to PROFINET (FND004 modernization)
- No servo needed (simple conveyor motion)

*v1.0.0 — Parameters to be added from the drive datasheet (Gate 3).*
