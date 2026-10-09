import pathlib

import pytest
from lupa.luajit21 import LuaRuntime

ROOT = pathlib.Path(__file__).resolve().parents[1]
MOD_DIR = ROOT / "mod/script/campaign/mod"
# load order matters only for the test runtime; the game loads all mod files before first tick
MOD_FILES = ["donation_army_config.lua", "donation_army_queue.lua", "donation_army_rosters.lua", "donation_army_composer.lua", "donation_army_spawn.lua", "donation_army.lua"]
LUA_DIR = pathlib.Path(__file__).parent / "lua"


class Game:
    """LuaJIT runtime with game stubs and the mod files that exist so far."""

    def __init__(self, queue_path):
        self.queue_path = queue_path
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.run((LUA_DIR / "stubs.lua").read_text(encoding="utf-8"))
        for name in MOD_FILES:
            path = MOD_DIR / name
            if path.exists():
                self.run(path.read_text(encoding="utf-8"))
        config = self.lua.globals().donation_army_config
        if config is not None:
            config.queue_file = str(queue_path)
        if self.lua.globals().donation_army is not None:
            self.run("donation_army.show_warning = function(text) table.insert(fake.popups, text) end")

    def run(self, code):
        self.lua.execute(code)

    def eval(self, expr):
        return self.lua.eval(expr)

    def queue(self, *lines):
        with open(self.queue_path, "a", encoding="utf-8", newline="\n") as f:
            for line in lines:
                f.write(line + "\n")

    def first_tick(self):
        self.run("for _, f in ipairs(fake.first_tick) do f() end")

    def poll(self):
        self.run('fake.real_callbacks["donation_army_poll"]()')

    def player_turn_start(self):
        self.run('fire_event("ScriptEventPlayerFactionTurnStart", { faction = function() return fake.factions[fake.local_faction] end })')

    @property
    def log(self):
        return list(self.lua.globals().test_log.values())

    @property
    def errors(self):
        return list(self.lua.globals().script_errors.values())


@pytest.fixture
def game(tmp_path):
    return Game(tmp_path / "donation_army_queue.txt")
