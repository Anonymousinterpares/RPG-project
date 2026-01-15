import sys
import os
import traceback

sys.path.append(os.getcwd())

try:
    from core.game_flow.input_router import InputRouter
    print("Success: InputRouter imported")
except ImportError:
    print("Failed: InputRouter import")
    traceback.print_exc()

try:
    from core.stats.stats_commands import register_stats_commands
    print("Success: register_stats_commands imported")
except ImportError:
    print("Failed: register_stats_commands import")
    traceback.print_exc()
