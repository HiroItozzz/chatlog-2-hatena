from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class LlmFee(ABC):
    def __init__(self, model:str):
        self.model = model

    @abstractmethod
    @property
    def fees(self):
        pass
    @abstractmethod
    @property
    def model_list(self):
        pass

    @abstractmethod
    def calculate(self, tokens:int, token_type:str) -> float:
        pass

class GeminiFee(LlmFee):
    '''2025/12/09現在'''
    _fees = {
        "gemini-2.5-flash": {"input": 0.03, "output": 2.5},  # $per 1M tokens 
        "gemini-2.5-pro": {
            "under_0.2M": {"input": 1.25, "output": 10.00},
            "over_0.2M": {"input": 2.5, "output": 15.0},
        }
    }
    _model_list = ["gemini-2.5-flash", "gemini-2.5-pro"]

    @property
    def fees(self):
        return self._fees
    
    @property
    def model_list(self):
        return self._model_list        

    def calculate(self, tokens, token_type) -> float:
        model = self.model
        token_type = "output" if token_type == "thoughts" else token_type
        if self.model not in self.model_list:
            logger.warning("料金表に登録されていないモデルです")
            logger.warning("'gemini-2.5-proの料金で試算します")
            model = "gemini-2.5-pro"
        if model == "gemini-2.5-flash":
            dollar_per_1M_tokens = tokens * self.fees[self.model][token_type]
        elif model == "gemini-2.5-pro":
            base_fee = self.fees["gemini-2.5-pro"]
            if tokens <= 200000:
                dollar_per_1M_tokens = base_fee["under_0.2M"][token_type]
            else:
                 dollar_per_1M_tokens = base_fee["over_0.2M"][token_type]
            
        return dollar_per_1M_tokens * tokens / 1000000

class DeepseekFee(LlmFee):
    _fees = {"input(cache_hit)": 0.028, "input(cache_miss)":0.28, "output": 0.42}
    _model_list = ["Deepseek-chat", "Deepseek-reasoner"]

    @property
    def fees(self):
        return self._fees

    @property
    def model_list(self):
        return self._model_list

    def calculate(self, tokens, token_type):
        token_type = "output" if token_type == "thoughts" else token_type
        if token_type == "output":
            dollar_per_1M_tokens = self.fees["output"]
        else:
            dollar_per_1M_tokens = self.fees["input(cache_miss)"]
        
        return dollar_per_1M_tokens * tokens / 1000000