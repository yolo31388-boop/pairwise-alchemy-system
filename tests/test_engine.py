"""炼丹测试"""
import pytest, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from src.engine import AlchemySystem, Recipe, Herb

class TestHerbs:
    def test_herb_quality_checked(self):
        als = AlchemySystem()
        als.recipes["r1"] = Recipe("r1", "hp_potion", [{"id":"h1"}], 3, 50.0)
        als.herbs["h1"] = Herb("h1", "grass", 1, "water")
        # 品质1的药材不应满足品质3要求
        assert not als.check_herbs("r1", ["h1"]), "药材品质未检查"

class TestQuality:
    def test_quality_weighted(self):
        als = AlchemySystem()
        als.recipes["r1"] = Recipe("r1", "hp", [{"id":"h1"}], 1, 50.0)
        als.herbs["h1"] = Herb("h1", "grass", 3, "water")
        legendary_count = 0
        for i in range(100):
            r = als.refine("r1", ["h1"], 50.0)
            if r and r["quality"] == "legendary":
                legendary_count += 1
        # 传说品质不应均匀分布（100次约25次太多）
        assert legendary_count < 25, "品质均匀随机"

class TestSideEffect:
    def test_potion_has_side_effect(self):
        als = AlchemySystem()
        als.recipes["r1"] = Recipe("r1", "strong_potion", [{"id":"h1"}], 1, 50.0)
        als.herbs["h1"] = Herb("h1", "grass", 5, "fire")
        r = als.refine("r1", ["h1"], 50.0)
        if r:
            assert "side_effects" in r or r.get("effects",{}).get("hp",0) < 200, "丹药无副作用"
