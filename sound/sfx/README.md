# SFX folders

Recommended layout (engine-agnostic, mapping-driven):
- sound/sfx/venue/    # tavern_bell.mp3, market_chatter_1.mp3, library_pageflip.mp3, fireplace_crackle.mp3
- sound/sfx/weather/  # thunder_roll_1.mp3, rain_patters_1.mp3, wind_gust_1.mp3
- sound/sfx/crowd/    # chatter_busy_1.mp3, footsteps_sparse_1.mp3, empty_room_tail.mp3
- sound/sfx/ui/       # optional UI clicks/confirm/back

Place any file types supported by the backend (mp3/ogg/wav/flac). Use config/audio/sfx_mappings.json to select exactly which file to play per context value.
