Prompt construction overview (Narrator)
•  System prompt (in narrator.py _generate_system_prompt):
•  Player info (name, race, path/class, background).
•  Location, district, time-of-day, weather, mode.
•  A stamina system note when in Narrative mode and stamina isn’t full.
•  Strict JSON-only output instruction describing the AgentOutput contract.
•  Guidance for interpreting skill checks, state changes, and mode transition requests.
•  Rule for data retrieval requests to be explicit (inventory, stats, quests, location info).
•  User message (narrator.py _prepare_messages):
•  Includes conversation history.
•  Conditionally includes formatted stats/inventory if player input mentions them; always includes basic location info; environment tags if present.
•  Then appends the literal “Player Input” content.
•  The agent calls the LLM with:
•  messages = [{role: system, content: system_prompt}, history..., {role: user, content: compiled user message}]
•  AgentManager drives a two-pass loop when requests like GET_QUESTS are present. It adds the fetched info to context.additional_context and regenerates the narrative.





•  System prompt highlights:
•  “Output only JSON per schema; never invent quest or objective IDs; update only in-progress objectives.”
•  “Use confidence 0..1 and give a short evidence string based on the last narrative and the RecentEvents.”
•  “NEVER mark an objective complete if the DSL states it’s impossible based on provided signals.”
•  User message parts:
•  Context: time/place, only the changed signals (deltas) and current values for keys relevant to the listed objectives.
•  Active quests snapshot: only quest titles and objective ids + short descriptions for in-progress (mandatory first).
•  Recent narrative (last LLM response), last player input.
•  RecentEvents: a compact list (last few only, with timestamps).
•  Instruction: “Propose only changes you are confident about; if none, return an empty quest_updates array.”