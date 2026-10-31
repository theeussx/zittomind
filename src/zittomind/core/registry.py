from zittomind.schemas import Model


class Registry:
    def __init__(self, models: list[Model]):
        self.models = {model.id: model for model in models}

    def get(self, model_id: str) -> Model:
        if model_id not in self.models:
            raise ValueError("unknown model ID")
        return self.models[model_id]
