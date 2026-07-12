"""
TIA Portal Openness bridges.

V19 and V20 supported. Both load Siemens.Engineering.dll via pythonnet.
API surfaces are 99% identical; only the DLL path and project file
extension (.ap19 vs .ap20) differ.

This module **can be imported even when pythonnet is not installed**.
A missing pythonnet shows up in the detect() call; the GUI is not broken.

License note:
  TIA Openness has been free since V14 SP1. No separate purchase needed.
  The user must be in the "Siemens TIA Openness" local user group on
  Windows. To check: lusrmgr.msc -> Groups -> Siemens TIA Openness.
"""
