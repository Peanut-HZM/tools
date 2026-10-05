"""狼人杀引擎测试共享辅助"""
import random

from app.services.werewolf.boards import GameSettings
from app.services.werewolf.engine import Phase, WerewolfEngine

NIGHT_PHASES = (Phase.NIGHT_GUARD, Phase.NIGHT_WEREWOLF, Phase.NIGHT_SEER, Phase.NIGHT_WITCH)


def make_engine(roles, seed=42, settings=None):
    players = [(i, f"玩家{i}") for i in range(1, sum(roles.values()) + 1)]
    eng = WerewolfEngine(players, roles, settings or GameSettings(), now=1000.0,
                         rng=random.Random(seed))
    eng.start(1000.0)
    return eng


def seats_with_role(eng, role):
    return [p.seat for p in eng.players if p.role == role]


class DriveHelper:
    """靠超时驱动对局推进（夜晚/发言/投票全部按托管处理）"""

    def __init__(self, eng: WerewolfEngine):
        self.eng = eng
        self.t = 1000.0

    def _tick(self):
        self.t += 500
        self.eng.check_timeouts(self.t)

    def run_to(self, phase: Phase, max_ticks: int = 300):
        while self.eng.phase != phase and self.eng.phase != Phase.RESULT and max_ticks > 0:
            self._tick()
            max_ticks -= 1
        assert self.eng.phase == phase, f"未推进到 {phase}，当前 {self.eng.phase}"

    def run_to_phase_in(self, phases, max_ticks: int = 300):
        while self.eng.phase not in phases and self.eng.phase != Phase.RESULT and max_ticks > 0:
            self._tick()
            max_ticks -= 1
        assert self.eng.phase in phases or self.eng.phase == Phase.RESULT

    def to_next_night(self):
        self.run_to_phase_in(list(NIGHT_PHASES))
