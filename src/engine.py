"""炼丹制药系统"""
from dataclasses import dataclass, field
import random

QUALITY_TIERS = ["common", "rare", "epic", "legendary"]

# 相生相克表（五行）
ELEMENT_GENERATES = {"wood": "fire", "fire": "earth", "earth": "metal",
                     "metal": "water", "water": "wood"}
ELEMENT_CLASHES = {"wood": "earth", "earth": "water", "water": "fire",
                   "fire": "metal", "metal": "wood"}

FIRE_TOLERANCE = 10.0   # 最佳火候容忍区间半径
PITY_THRESHOLD = 5      # 连续失败保底炉数
BASE_REFINE_TIME = 5    # 基础炼丹秒数

@dataclass
class Herb:
    hid: str
    name: str
    quality: int
    element: str

@dataclass
class Recipe:
    rid: str
    name: str
    herbs: list
    min_quality: int
    best_fire: float

class AlchemySystem:
    def __init__(self):
        self.recipes: dict[str, Recipe] = {}
        self.herbs: dict[str, Herb] = {}
        self.unlocked = set()
        self.learn_progress = {}   # 丹方领悟进度 0.0~1.0
        self.pity = {}             # 每个丹方的连续失败计数
        self.level = 1             # 炼丹师等级

    # bug1 修复：同时验证药材ID和品质等级
    def check_herbs(self, recipe_id, herb_ids):
        recipe = self.recipes[recipe_id]
        for req in recipe.herbs:
            hid = req["id"]
            if hid not in herb_ids:
                return False
            herb = self.herbs.get(hid)
            if herb is None:
                return False
            need = req.get("min_quality", recipe.min_quality)
            if herb.quality < need:
                return False
        return True

    # bug2 修复：火候有最佳区间，偏离越多得分越低
    def _fire_score(self, recipe, fire_temp):
        deviation = abs(fire_temp - recipe.best_fire)
        return max(0.0, 1.0 - deviation / (FIRE_TOLERANCE * 2))

    # bug8 修复：药材相生相克，相克组合炸炉
    def _check_clash(self, recipe):
        elements = [self.herbs[h["id"]].element
                    for h in recipe.herbs if h["id"] in self.herbs]
        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                a, b = elements[i], elements[j]
                if ELEMENT_CLASHES.get(a) == b or ELEMENT_CLASHES.get(b) == a:
                    return True
        return False

    # bug3 修复：成功率综合药材品质、火候、丹方等级、炼丹师等级
    def _success_rate(self, recipe, fire_temp):
        herbs = [self.herbs[h["id"]] for h in recipe.herbs
                 if h["id"] in self.herbs]
        avg_q = sum(h.quality for h in herbs) / max(len(herbs), 1)
        herb_factor = min(avg_q / max(recipe.min_quality, 1), 1.5) / 1.5
        fire = self._fire_score(recipe, fire_temp)
        rate = (0.25 + 0.25 * herb_factor + 0.30 * fire
                + 0.05 * self.level - 0.05 * recipe.min_quality)
        return max(0.05, min(0.95, rate))

    # bug4 修复：加权随机品质，高品质概率低，受火候和药材影响
    def _roll_quality(self, recipe, fire_temp, boosted=False):
        herbs = [self.herbs[h["id"]] for h in recipe.herbs
                 if h["id"] in self.herbs]
        avg_q = sum(h.quality for h in herbs) / max(len(herbs), 1)
        bonus = 0.5 * self._fire_score(recipe, fire_temp) + 0.05 * min(avg_q, 10)
        if boosted:
            bonus += 0.4
        weights = [max(5.0, 70 - 30 * bonus), 20.0,
                   8 + 10 * bonus, 2 + 8 * bonus]
        return random.choices(QUALITY_TIERS, weights=weights, k=1)[0]

    # bug5 修复：丹药附带副作用，正面效果越强副作用越大
    def _make_pill(self, recipe, quality):
        tier = QUALITY_TIERS.index(quality)
        potency = (tier + 1) * recipe.min_quality
        return {
            "name": recipe.name,
            "quality": quality,
            "effects": {"hp": 50 * potency},
            "side_effects": {"mp": -10 * potency, "stamina": -5 * potency},
        }

    def refine(self, recipe_id, herb_ids, fire_temp):
        if not self.check_herbs(recipe_id, herb_ids):
            return None
        recipe = self.recipes[recipe_id]
        # 相克组合炸炉，损失药材
        if self._check_clash(recipe):
            self.pity[recipe_id] = 0
            return {"name": recipe.name, "exploded": True,
                    "lost_herbs": list(herb_ids)}
        # bug6 修复：连续失败N炉后保底，必成且品质提升
        if self.pity.get(recipe_id, 0) >= PITY_THRESHOLD:
            self.pity[recipe_id] = 0
            return self._make_pill(recipe,
                                   self._roll_quality(recipe, fire_temp,
                                                      boosted=True))
        if random.random() < self._success_rate(recipe, fire_temp):
            self.pity[recipe_id] = 0
            return self._make_pill(recipe,
                                   self._roll_quality(recipe, fire_temp))
        self.pity[recipe_id] = self.pity.get(recipe_id, 0) + 1
        return None

    def batch_refine(self, recipe_id, herb_ids, fire_temp, count):
        return [self.refine(recipe_id, herb_ids, fire_temp)
                for _ in range(count)]

    # bug7 修复：领悟有概率和进度，可能部分领悟或失败，需多次尝试
    def learn_recipe(self, recipe_id):
        if recipe_id in self.unlocked:
            return True
        progress = self.learn_progress.get(recipe_id, 0.0)
        if random.random() < 0.6:
            progress += random.uniform(0.2, 0.5)   # 领悟推进
        else:
            progress += random.uniform(0.0, 0.05)  # 领悟失败，仅少许感悟
        self.learn_progress[recipe_id] = progress
        if progress >= 1.0:
            self.unlocked.add(recipe_id)
            return True
        return False

    # bug9 修复：炼丹时间按丹方等级和品质动态计算
    def get_refine_time(self, recipe_id, quality="common"):
        recipe = self.recipes[recipe_id]
        tier = QUALITY_TIERS.index(quality)
        return BASE_REFINE_TIME + 3 * recipe.min_quality + 2 * tier
