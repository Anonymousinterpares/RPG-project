# Testing Instructions - Web UI Game Loading Fixes

## ⚠️ CRITICAL: Clear Browser Cache First!

The JavaScript files have been updated, but your browser is still serving the **old cached version**. This is why you're still seeing the `mode is not defined` error even though it's been fixed in the code.

### How to Clear Cache and Test:

#### Option 1: Hard Refresh (Recommended)
1. Open your web UI in the browser
2. **Press:** `Ctrl + Shift + R` (Windows/Linux) or `Cmd + Shift + R` (Mac)
3. This forces a full reload without cache

#### Option 2: Clear Cache via DevTools
1. Open DevTools: `F12` or `Ctrl + Shift + I`
2. Right-click on the **Refresh button** in the browser toolbar
3. Select **"Empty Cache and Hard Reload"**

#### Option 3: Clear Browser Cache Completely
1. Open your browser settings
2. Navigate to Privacy & Security
3. Clear browsing data
4. Select **"Cached images and files"**
5. Clear data for the last hour

#### Option 4: Use Incognito/Private Window
1. Open a new incognito/private browser window
2. Navigate to your web UI URL
3. This ensures no cached files are used

---

## What Was Fixed

### Fix 1: ✅ Removed Duplicate Variable Assignment
**File:** `web/client/js/ui-manager.js` (line 2397)
- Removed the line causing `ReferenceError: mode is not defined`
- This was preventing `refreshUI()` from completing
- **Result:** Right panel will now populate with character data

### Fix 2: ✅ Added Combat Tab Removal Logic
**File:** `web/client/js/ui-manager.js` (new method `removeCombatTab()`)
- Added logic to remove Combat tab when exiting combat
- Automatically switches to Character tab when Combat tab is removed
- **Result:** Combat tab will disappear when loading a non-combat save

### Fix 3: ✅ Improved refreshUI Combat Mode Handling
**File:** `web/client/js/ui-manager.js` (method `refreshUI()`)
- Now properly detects when leaving combat mode
- Calls `removeCombatTab()` when transitioning out of combat
- **Result:** Clean state management for combat/non-combat transitions

---

## Testing Checklist

### Test 1: Load Non-Combat Save
1. ✅ Start web server
2. ✅ Open web UI (after clearing cache!)
3. ✅ Click **"Load Game"**
4. ✅ Select a save that is **NOT in combat**
5. ✅ Click **"Load"**

**Expected Results:**
- ✅ No console errors
- ✅ Right panel has tabs: **Character**, **Inventory**, **Journal** (NO Combat tab)
- ✅ Character tab shows:
  - Character name, race, class, level
  - Health/Mana/Stamina bars
  - Primary stats (STR, DEX, CON, etc.)
  - Derived stats
  - Equipment list
- ✅ Status bar shows location and time
- ✅ Narrative text appears in output area
- ✅ Load game modal closes

### Test 2: Load Combat Save
1. ✅ Click **"Load Game"** again
2. ✅ Select a save that **IS in combat**
3. ✅ Click **"Load"**

**Expected Results:**
- ✅ No console errors
- ✅ Right panel has tabs: **Combat**, **Character**, **Inventory**, **Journal**
- ✅ Combat tab is automatically selected and shows combat log
- ✅ Character data still populates in Character tab
- ✅ Combat UI elements are visible

### Test 3: Load Non-Combat After Combat
1. ✅ After loading a combat save (Test 2)
2. ✅ Click **"Load Game"** again
3. ✅ Select a save that **IS NOT in combat**
4. ✅ Click **"Load"**

**Expected Results:**
- ✅ Combat tab **DISAPPEARS** from right panel
- ✅ Automatically switches to Character tab
- ✅ Character data populates correctly
- ✅ Only tabs visible: **Character**, **Inventory**, **Journal**

### Test 4: Verify No Errors
1. ✅ Open browser console (F12)
2. ✅ Load any save file
3. ✅ Check console logs

**Expected Console Output:**
```
Connecting to WebSocket: ws://localhost:8000/ws/[session-id]
WebSocket connection established
WebSocket received game_state event: ...
Received game state update
WebSocket received narrative event: ...
```

**Should NOT see:**
- ❌ `404 (Not Found)`
- ❌ `ReferenceError: mode is not defined`
- ❌ `refreshUI failed`

---

## Troubleshooting

### Still Seeing "mode is not defined" Error?
**Problem:** Browser is still using cached JavaScript

**Solutions:**
1. Try a different browser
2. Use incognito/private mode
3. Manually delete browser cache completely
4. Restart the browser after clearing cache
5. Check the actual file timestamp:
   - Open DevTools → Network tab
   - Reload page
   - Find `ui-manager.js` in the list
   - Check if it's loading from cache or server

### Right Panel Still Empty?
**Check these:**
1. ✅ Is the session being created properly? (Check console logs)
2. ✅ Is `getUIState()` being called? (Check Network tab in DevTools)
3. ✅ Does the API endpoint return data? (Check Network tab response)
4. ✅ Are there any other JavaScript errors? (Check Console)

**Debug Steps:**
```javascript
// In browser console, after loading a game:
apiClient.getUIState().then(console.log)
```

This should return an object with:
```javascript
{
  mode: "EXPLORATION" or "COMBAT",
  player: { name, race, path, level, ... },
  resources: { health: {current, max}, ... },
  primary_stats: { ... },
  ...
}
```

### Combat Tab Won't Disappear?
**Check:**
1. ✅ Is `ui.mode` being returned from the server?
2. ✅ Is the mode changing from "COMBAT" to something else?

**Debug:**
```javascript
// In browser console:
apiClient.getUIState().then(ui => console.log('Mode:', ui.mode))
```

---

## Technical Details

### Files Modified:
1. `web/client/js/ui-manager.js`:
   - Line 2397: Removed duplicate assignment
   - Lines 2048-2074: Added `removeCombatTab()` method
   - Lines 2409-2446: Improved `refreshUI()` logic

2. `web/client/js/api-client.js`:
   - Lines 294, 344: Added clarifying comments (no functional change)

3. `web/client/js/main.js`:
   - Lines 541-596: Completely refactored `loadGame()` function

### How Combat Tab Management Works:
```
Non-Combat Save → Load → refreshUI() → No combat mode → No Combat tab
Combat Save → Load → refreshUI() → Combat mode detected → ensureCombatTab() → Combat tab added
Combat → Non-Combat → refreshUI() → Mode change detected → removeCombatTab() → Combat tab removed
```

---

## Success Criteria

✅ **All of these must be true:**
1. No JavaScript errors in console when loading a game
2. Right panel populates with character data after load
3. Combat tab appears when loading combat save
4. Combat tab disappears when loading non-combat save
5. Can send commands after loading
6. UI is responsive and functional

---

**If all tests pass:** The fixes are working correctly! 🎉

**If tests fail:** Report which specific test failed and include:
- Browser console logs (full output)
- Network tab showing API requests/responses
- Screenshots of the issue
- Which browser and version you're using
