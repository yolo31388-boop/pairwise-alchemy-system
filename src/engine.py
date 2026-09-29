"""炼丹制药 - 带9个bug"""
from dataclasses import dataclass, field
import random

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
        self.pity = {}  # bug6: 无保底

    def check_herbs(self, recipe_id, herb_ids):
        recipe = self.recipes[recipe_id]
        for h in recipe.herbs:
            # bug1: 只检查ID不检查品质
            if h["id"] not in herb_ids:
                return False
        return True

    def refine(self, recipe_id, herb_ids, fire_temp):
        if not self.check_herbs(recipe_id, herb_ids):
            return None
        # bug2: 火候不影响
        # bug3: 固定50%
        if random.random() < 0.5:
            # bug4: 均匀随机品质
            quality = random.choice(["common", "rare", "epic", "legendary"])
            # bug5: 无副作用
            return {"name": self.recipes[recipe_id].name, "quality": quality, "effects": {"hp": 100}}
        return None

    def batch_refine(self, recipe_id, herb_ids, fire_temp, count):
        results = []
        for i in range(count):
            # bug6: 无保底
            results.append(self.refine(recipe_id, herb_ids, fire_temp))
        return results

    def learn_recipe(self, recipe_id):
        # bug7: 固定解锁
        self.unlocked.add(recipe_id)
        return True

    def get_refine_time(self, recipe_id):
        # bug9: 固定时间
        return 10
