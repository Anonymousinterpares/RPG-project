# Layout Editing Tools — How to Use

This document explains every feature of the in‑browser layout editor available in developer mode, including how to move/resize elements, save/restore snapshots, reset to defaults, and use Undo/Redo.

Where to find the tools
- Open Settings → Style Tools.
- Use the toggles to enable the inspector, grid, and the Element Resize Mode. Optional: Enable Move Mode to allow dragging the selection.

Main concepts
- Selection: Click any element on the page to select it. Ctrl+Click adds/removes items to a multi‑selection. When selected, a blue frame with round handles appears.
- Overlay toolbar: Appears above the selection with controls: Unlock, Reset WH, Reset Pos, Clear Sel, Undo, Redo, Save Layout, Restore, Reset All.
- Persistence: Edits are saved live into localStorage (per browser). The Save Layout button stores an additional snapshot that can be restored later.

Controls in Settings → Style Tools
- Enable Layout Inspector: Shows a hover tooltip that displays element info and layout variables. You can edit layout variables there or in the form fields.
- Show Grid Overlay: Draws a grid over the UI; grid size is configurable.
- Enable Element Resize Mode: Shows selection overlay and handles.
- Enable Move Mode: Allows dragging the selection via the overlay’s center area.
- Grid Size / Left Menu Width / Right Panel Width / Content Gap / Right Panel Pane Max Height: Live‑edit these CSS variables. Values are persisted.
- Reset Layout to Defaults: Full reset to CSS defaults and clears all local overrides.
- Restore Layout From Saved Snapshot: Applies the last snapshot created with Save Layout.

Overlay toolbar buttons (developer mode)
- Unlock: Hides the overlay and exits the current selection.
- Reset WH: Clears inline width/height for selected element(s).
- Reset Pos: Clears inline position/left/top/zIndex of selected element(s).
- Clear Sel: Reduces multi‑selection to only the anchor element.
- Undo / Redo: Steps backward/forward through your last editor actions (resize/move/reset/inspector edits). Shortcuts: Ctrl+Z and Ctrl+Shift+Z (or Ctrl+Y).
- Save Layout: Stores a snapshot (layout variables + element inline styles) under localStorage key rpg_layout_saved. This does not change the UI.
- Restore: Restores from the saved snapshot. Useful as a safety net during editing.
- Reset All: Same as the Settings reset — clears all overrides, turns off editor/move, and returns the layout to defaults.

Moving elements
- Enable Element Resize Mode and Move Mode.
- Select an element (or multi‑select with Ctrl+Click).
- Drag inside the blue frame (not the handles) to move.
- Snap‑to‑grid: Hold Shift while dragging to snap movement to the grid size set in Style Tools.

Resizing elements
- Enable Element Resize Mode.
- Drag any of the round handles (sides/corners) to resize.
- Inspector numeric inputs: With a selection, the inspector panel shows Width, Height, Max Height, and OverflowY — edits here also record Undo/Redo actions.

Multi‑selection
- Ctrl+Click multiple elements to select several items. Dragging will move them as a group. Reset WH/Pos applies to all selected.

Saving and restoring
- Save Layout (toolbar): Saves a snapshot with current CSS variables and the inline styles of edited elements. The app keeps using your live edits.
- Restore (toolbar) or Restore Layout From Saved Snapshot (Settings): Applies the saved snapshot and updates inputs/overlays accordingly.

Resetting to defaults
- Use Reset All (toolbar) or Reset Layout to Defaults (Settings). This clears all local overrides and resets CSS variables to defaults. Editor/move modes are disabled.

Troubleshooting
- Can’t move elements? Ensure:
  - Element Resize Mode is ON, Move Mode is ON, and the element is selected (blue frame visible).
  - If toggling Move Mode didn’t change the cursor, toggle it off/on once — the overlay now refreshes pointer state automatically.
- UI looks broken? Use Reset Layout to Defaults. If that fails, reload the page and try again.
- Nothing happens on Restore? Make sure you previously clicked Save Layout to create a snapshot.

Storage keys (for reference)
- rpg_element_styles: live per‑selector style overrides
- rpg_layout_saved: snapshot payload (vars + element_styles)
- rpg_layout_left, rpg_layout_right, rpg_layout_gap, rpg_rp_max, rpg_grid_size: variable overrides
- rpg_grid_enabled, rpg_dev_inspector_enabled, rpg_dev_editor_enabled, rpg_dev_move_enabled: feature toggles

Notes
- All data is stored in your browser’s localStorage for this origin. Snapshots and edits are per‑browser and per‑machine. If you need cross‑machine persistence, consider exporting these keys and committing them to version control or wiring a server API.

