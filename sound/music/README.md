# Music Library Structure (definitive)

This document defines the folder layout and canonical mood list used by the engine and the web client. Place your tracks according to this structure to enable testing.

The Director scans folders at runtime and selects tracks by mood. Context (location, etc.) is used only as a soft bias and does not change the folder layout.

## Folder layout

sound/
  music/
    ambient/
    exploration/
    tension/
    stealth/
    combat/
    victory/
    defeat/
    # optional, see below
    boss/
    mystery/
    sorrow/
    wonder/
    travel/
    rest/
    horror/

Rules:
- Each folder contains audio files for that mood (no subfolders required for basic operation).
- Supported file types: .mp3, .ogg, .wav, .flac
- The server exposes files at /sound/music/<mood>/<file> for the web client.

## Canonical mood list

Required (Milestone 1 – supported everywhere):
- ambient (default for new games)
- exploration
- tension
- stealth
- combat
- victory
- defeat

Optional (Milestone 2+ – available if you add folders):
- boss
- mystery
- sorrow
- wonder
- travel
- rest
- horror

Notes:
- You can add more moods as needed by creating additional folders (the Director will discover them), but the seven required moods above are used in testing and scripts.
- Avoid using location names as mood folders. Location/venue/weather are handled via tags (see manifests) for selection bias without duplicating folders.

## Optional stingers (Phase B – not required to test core music)

If you want short stingers on mood transitions, use:

sound/
  music/
    <mood>/
      stingers/
        start/
          <files>
        boss_intro/
          <files>
        victory/
          <files>
        defeat/
          <files>
        danger_spike/
          <files>

- These are optional. If stinger folders/files are missing, the system just continues normal music.
- Stingers will duck the music briefly, then restore (implemented in a later milestone).

## Optional per-mood manifest (tags & loudness)

You may add a manifest to guide selection and normalize loudness:

sound/music/<mood>/manifest.yaml

Example:

mood: "tension"
default_intensity: 0.5
tracks:
  - file: "edge_of_fog.mp3"
    weight: 1.0
    loudness_offset_db: -1.5
    tags: ["forest", "night"]       # location_major/time_of_day tags
    min_play_seconds: 20
  - file: "shadows.ogg"
    weight: 0.8
    loudness_offset_db: -0.7
    tags: ["city"]

Field hints:
- weight: affects random selection probability for this mood
- loudness_offset_db: simple gain compensation (+/- dB)
- tags: recommend values from these sets to enable context bias:
  - location_major: city, camp, forest, seaside, desert, mountain, swamp, dungeon, castle, village, port, temple, ruins
  - time_of_day (optional): dawn, day, dusk, night
  - (venue and weather planned for later; safe to include now)

## Naming guidance (optional)
- You don’t need to encode tags in filenames, but during Phase A a lightweight bias uses filename tokens if present (e.g., a track name containing "forest").
- Use short, readable names; avoid special characters.

## Quick start checklist
- Create the seven required folders under sound/music/ (see Required list).
- Drop 1–3 tracks into each folder (mp3/ogg recommended for web).
- (Optional) Add manifest.yaml for any mood if you want weights or loudness offsets.
- Start the server. The Director will discover all moods and tracks at startup.

## Testing tips
- New game starts in ambient.
- Intensity controls perceived loudness within the ceiling set by sliders (master/music). A perceptual curve (gamma≈1.8) is used so low intensities are gently audible, and 1.0 is full presence.
- Use MUSIC commands (via LLM or command path) to test:
  - {"action":"set_mood","mood":"tension","confidence":0.9}
  - {"action":"set_intensity","intensity":0.6}
  - {"action":"jumpscare","peak":1.0,"attack_ms":60,"hold_ms":150,"release_ms":800}
  - {"action":"next"}
  - {"action":"mute"} / {"action":"unmute"}
- Web path for a track: /sound/music/<mood>/<filename>

## FAQ
- Can I add new moods? Yes. Create a folder with that mood name. The Director will pick it up automatically.
- Do I need stingers? No. They’re optional and implemented in a later milestone.
- Where do I put ambient SFX? See sound/sfx (planned in the SFX milestone). This README is for music only.
