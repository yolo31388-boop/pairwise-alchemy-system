"""炼丹制药系统"""
from dataclasses import dataclass, field
import random

QUALITIES = ["common", "rare", "epic", "legendary"]

# 五行相生: 金生水 水生木 木生火 火生土 土生金
ELEMENT_GENERATES = {
    "metal": "water", "water": "wood", "wood": "fire",
    "fire": "earth", "earth": "metal",
}
# 五行相克: 金克木 木克土 土克水 水克火 火克金
ELEMENT_OVERCOMES = {
    "metal": "wood", "wood": "earth", "earth": "water",
    "water": "fire", "fire": "metal",
}

# 品质基础权重: 高品质概率低
BASE_QUALITY_WEIGHTS = {"common": 50.0, "rare": 30.0, "epic": 15.0, "legendary": 5.0}

FIRE_TOLERANCE = 10.0       # 最佳火候容忍区间
PITY_THRESHOLD = 5          # 连续失败保底炉数
BASE_REFINE_TIME = 5.0      # 基础炼丹时间(秒)


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
    level: int = 1
    # 副作用配置: {副作用名: 每点正面效果对应的副作用强度}
    side_effect_ratio: float = 0.25


class AlchemySystem:
    def __init__(self):
        self.recipes: dict[str, Recipe] = {}
        self.herbs: dict[str, Herb] = {}
        self.unlocked = set()
        self.learn_progress: dict[str, float] = {}   # 丹方领悟进度 0~1
        self.pity: dict[str, int] = {}               # 每个丹方的连续失败计数
        self.alchemist_level = 1

    # ---------- 药材匹配: 同时验证ID和品质 ----------
    def check_herbs(self, recipe_id, herb_ids):
        recipe = self.recipes[recipe_id]
        provided = {hid: self.herbs.get(hid) for hid in herb_ids}
        for req in recipe.herbs:
            hid = req["id"]
            herb = provided.get(hid)
            if herb is None:
                return False
            need = req.get("min_quality", recipe.min_quality)
            if herb.quality < need:
                return False
        return True

    # ---------- 药材搭配: 相生相克 ----------
    def check_combination(self, herb_ids):
        """返回 (ok, bonus): 相克组合会炸炉, 相生组合给加成"""
        elements = [self.herbs[h].element for h in herb_ids if h in self.herbs]
        bonus = 0.0
        for i in range(len(elements)):
            for j in range(i + 1, len(elements)):
                a, b = elements[i], elements[j]
                if ELEMENT_OVERCOMES.get(a) == b or ELEMENT_OVERCOMES.get(b) == a:
                    return False, 0.0
                if ELEMENT_GENERATES.get(a) == b or ELEMENT_GENERATES.get(b) == a:
                    bonus += 0.05
        return True, bonus

    # ---------- 火候: 偏离最佳区间降低评分 ----------
    def _fire_score(self, recipe, fire_temp):
        deviation = abs(fire_temp - recipe.best_fire)
        if deviation <= FIRE_TOLERANCE:
            return 1.0 - 0.2 * (deviation / FIRE_TOLERANCE)
        over = deviation - FIRE_TOLERANCE
        return max(0.0, 0.8 - over / 50.0)

    # ---------- 成功率: 药材品质+火候+丹方等级+炼丹师等级 ----------
    def _success_rate(self, recipe, herbs, fire_score, combo_bonus):
        avg_quality = sum(h.quality for h in herbs) / len(herbs)
        rate = 0.4
        rate += 0.06 * avg_quality              # 药材品质
        rate += 0.2 * fire_score                # 火候
        rate += 0.02 * self.alchemist_level     # 炼丹师等级
        rate -= 0.04 * recipe.level             # 丹方等级越高越难
        rate += combo_bonus                     # 相生加成
        return min(0.95, max(0.05, rate))

    # ---------- 品质: 加权随机, 受火候和药材影响 ----------
    def _roll_quality(self, herbs, fire_score, force_high=False):
        avg_quality = sum(h.quality for h in herbs) / len(herbs)
        boost = (avg_quality / 5.0) * fire_score
        weights = {}
        for q in QUALITIES:
            idx = QUALITIES.index(q)
            weights[q] = BASE_QUALITY_WEIGHTS[q] * (1.0 + boost * idx)
        if force_high:  # 保底: 至少 rare, 且高品权重翻倍
            weights["common"] = 0.0
            weights["epic"] *= 2
            weights["legendary"] *= 2
        total = sum(weights.values())
        roll = random.random() * total
        for q in QUALITIES:
            roll -= weights[q]
            if roll <= 0:
                return q
        return "common"

    # ---------- 丹药效果与副作用: 正面越强副作用越大 ----------
    def _make_pill(self, recipe, quality, herbs):
        tier = QUALITIES.index(quality) + 1
        avg_quality = sum(h.quality for h in herbs) / len(herbs)
        hp = int(20 * tier * (1 + avg_quality / 5.0))
        effects = {"hp": hp}
        side_effects = {"hp": -int(hp * recipe.side_effect_ratio)}
        return {
            "name": recipe.name,
            "quality": quality,
            "effects": effects,
            "side_effects": side_effects,
        }

    def refine(self, recipe_id, herb_ids, fire_temp):
        recipe = self.recipes[recipe_id]
        if not self.check_herbs(recipe_id, herb_ids):
            return None
        # 相克组合炸炉, 损失药材
        ok, combo_bonus = self.check_combination(herb_ids)
        if not ok:
            self.pity[recipe_id] = self.pity.get(recipe_id, 0) + 1
            return None
        herbs = [self.herbs[h] for h in herb_ids]
        fire_score = self._fire_score(recipe, fire_temp)
        # 保底: 连续失败N炉后必成且品质提升
        pity_hit = self.pity.get(recipe_id, 0) >= PITY_THRESHOLD
        if not pity_hit and random.random() >= self._success_rate(
            recipe, herbs, fire_score, combo_bonus
        ):
            self.pity[recipe_id] = self.pity.get(recipe_id, 0) + 1
            return None
        self.pity[recipe_id] = 0
        quality = self._roll_quality(herbs, fire_score, force_high=pity_hit)
        return self._make_pill(recipe, quality, herbs)

    def batch_refine(self, recipe_id, herb_ids, fire_temp, count):
        return [self.refine(recipe_id, herb_ids, fire_temp) for _ in range(count)]

    # ---------- 丹方领悟: 概率+进度, 可部分领悟或失败 ----------
    def learn_recipe(self, recipe_id, aptitude=0.4):
        if recipe_id in self.unlocked:
            return True
        if random.random() < aptitude:
            gain = random.uniform(0.2, 0.5)   # 部分领悟
        else:
            gain = random.uniform(0.0, 0.1)   # 领悟失败, 几乎无进展
        progress = self.learn_progress.get(recipe_id, 0.0) + gain
        if progress >= 1.0:
            self.unlocked.add(recipe_id)
            self.learn_progress[recipe_id] = 1.0
            return True
        self.learn_progress[recipe_id] = progress
        return False

    # ---------- 炼丹时间: 按丹方等级和目标品质动态计算 ----------
    def get_refine_time(self, recipe_id, quality=None):
        recipe = self.recipes[recipe_id]
        time = BASE_REFINE_TIME * recipe.level
        if quality in QUALITIES:
            time *= 1 + 0.5 * QUALITIES.index(quality)
        return time
