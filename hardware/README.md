# AeroClim carrier hardware files

These files preserve the available PCB exports and design snapshots. Original filenames are retained to make their dates and revisions visible.

## Available exports

| Location | Contents | Date on source files |
| --- | --- | --- |
| `production/2026-10-07/` | Gerber ZIP, bill of materials and pick-and-place export | 7 October 2026 |
| `design/PCB_PCB_aeroclim_carrier_2_2026-10-03 (3).json` | Latest locally recovered editable PCB snapshot from 3 October; EasyEDA editor format 6.5.54 | 3 October 2026 |
| `design/SCH_aeroclim_carrier_wired.json` | Latest locally recovered wired schematic; EasyEDA editor format 6.5.54 | Local file dated 5 October 2026 |
| `design/PCBLIB_HDR-F-2.54_2X15_2026-10-05.json` | Two-row header footprint library | 5 October 2026 |
| `design/Schematic_aeroclim_carrier_2026-10-03.png` | Schematic image for reference | 3 October 2026 |

The files named `.csv` use tab-separated columns, as exported by the PCB editor.

## Revision relationship

**The editable PCB snapshot predates the production exports.** No editable PCB file corresponding to the 7 October Gerbers was recovered. The October 3 PCB, October 5 schematic and October 7 manufacturing files must not be assumed to describe identical nets, footprints or routing. The schematic image also predates the wired schematic JSON.

Open the JSON files in the matching EasyEDA editor/import workflow. Preserve the original snapshots when making changes and export a new, consistently dated schematic, PCB, BOM and Gerber set together. Existing library contributor metadata is retained as attribution.

The 7 October Gerber archive contains top and bottom copper, silkscreen, solder mask, board outline and plated-hole drill files. Inclusion here records the supplied files; the files have not been cross-checked against each other or electrically validated during repository preparation.

## Firmware and board bring-up

Read [the hardware bring-up guide](../docs/HARDWARE.md) before using the carrier with the firmware. It documents the MQ analog divider, PMS UART connection and initial sensor configuration. The shipped firmware settings describe proposed rework and must be checked against the actual board; they do not establish that the older PCB snapshot or the production Gerbers implement that rework.
