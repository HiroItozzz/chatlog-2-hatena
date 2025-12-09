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

'''
def summarize_and_upload(
    preset_categories: list,
    llm_config: dict,
    hatena_secret_keys: dict,
    debug_mode: bool = False,
) -> tuple[dict, dict]:
    # GoogleへAPIリクエスト
    llm_outputs, llm_stats = conversational_ai.get_summary(llm_config)

    # はてなブログへ投稿 投稿結果を辞書型で返却
    response_dict = hatenablog_poster.blog_post(
        **llm_outputs,
        hatena_secret_keys=hatena_secret_keys,
        preset_categories=preset_categories,
        author=None,  # str | None   Noneの場合自分のはてなID
        updated=None,  # datetime | None  公開時刻設定。Noneの場合5分後に公開
        is_draft=debug_mode,  # デバッグ時は下書き
    )

    return response_dict, llm_stats
'''