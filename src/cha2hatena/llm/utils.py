import logging
from cha2hatena.llm import gemini_client, deepseek_client

logger=logging.getLogger(__name__)

def create_ai_client(params):
    if params["model"].startswith("gemini"):
        client = gemini_client.GeminiClient(**params)
    elif params["model"].startswith("deepseek"):
        client = deepseek_client.DeepseekClient(**params)
    else:
        logger.error("モデル名が正しくありません。実行を中止します。")
        logger.error(f"モデル名: {params['model']}")
    return client