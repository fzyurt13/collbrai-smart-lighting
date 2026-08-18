from config.profiles import PROFILES


class RecipeManager:

    def __init__(self):
        self.recipes = PROFILES

    def list_recipes(self):
        return list(self.recipes.keys())

    def exists(self, recipe_name):
        return recipe_name in self.recipes

    def get(self, recipe_name):
        if recipe_name not in self.recipes:
            raise ValueError(
                "Unknown recipe: {}".format(recipe_name)
            )

        return dict(self.recipes[recipe_name])

    def validate(self, recipe):
        required = [
            "name",
            "target_cct",
            "target_brightness",
            "confidence_threshold"
        ]

        missing = [
            key for key in required
            if key not in recipe
        ]

        if missing:
            raise ValueError(
                "Recipe missing fields: {}".format(
                    ", ".join(missing)
                )
            )

        return True
