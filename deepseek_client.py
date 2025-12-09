import json
import logging
import time
from pathlib import Path
import OpenAI
from .cha2hatena.gemini_client import BlogPost

logger = logging.getLogger(__name__)

def deepseek_errors(i, e, max_retries):
    if any(code in str(e) for code in [500, 502, 503]):
        if i < max_retries - 1:
            logger.warning(f"Deepseekの計算資源が逼迫しているようです。{5 * (i + 1)}秒後にリトライします。")
            time.sleep(5 * (i + 1))
        else:                
            logger.warning("DeepSeekは現在過負荷のようです。少し時間をおいて再実行する必要があります。")
            logger.warning("実行を中止します。")
            exit(1)
    elif 429 in str(e):
        logger.error("APIレート制限。しばらく経ってから再実行してください。")
        raise
    elif 401 in str(e):
        logger.error("エラー：APIキーが誤っているか、入力されていません。")
        logger.error(f"実行を中止します。詳細：{e}")
        exit(1)
    elif 402 in str(e):
        logger.error("残高が不足しているようです。アカウントを確認してください。")
        logger.error(f"実行を中止します。詳細：{e}")
        exit(1)
    elif 422 in str(e):
        logger.error("リクエストに無効なパラメータが含まれています。設定を見直してください。")
        logger.error(f"実行を中止します。詳細：{e}")
        exit(1)
    else:
        logger.error("要約取得中に予期せぬエラー発生。詳細はapp.logを確認してください。")
        logger.error("実行を中止します。")
        logger.info(f"詳細: {e}")
        raise


def deepseek_client(
    conversation: str,
    api_key: str,
    model: str = "deepseek-reasoner",
    temperature: float = 1.2,
    custom_prompt: str = "以下の内容を日本語で１０００字以内で要約し、個人用のブログ向け文章にしてください。",
) -> tuple[dict, dict]:
    
    logger.warning("Deepseekからの応答を待っています。")
    logger.debug(f"APIリクエスト中。APIキー: ...{api_key[-5:]}")

    client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com")

    STATEMENT = f"また、ブログ本文の最後には、「この記事は {model} により自動生成されています」と目立つように注記してください。"
    prompt = custom_prompt + STATEMENT + "\n\n" + conversation

    max_retries = 3
    for i in range(max_retries):
        try:
            response = client.chat.completions.create(
                model=model,
                temperature=temperature,
                messages=[{"role":"user", "content":prompt}],
                response_format={'type': 'json_object'},
                stream=False
            )
            break
        except Exception as e:
            # https://api-docs.deepseek.com/quick_start/error_codes
            deepseek_errors(i, e, max_retries)

    res_text = response.choices[0].message.content   
    
    try:
        data = json.loads(res_text)
        required_keys = {"title", "content", "categories"}
        if set(data.keys()) == required_keys:
            logger.warning("Deepseekが構造化出力に成功")
    except Exception as e:
        logger.error(f"Deepseekが構造化出力に失敗。\n要請：{required_keys} 出力：{data.keys()}")
        logger.error("outputs/_summary.txtへ結果を保存します。")
        output_dir = Path.cwd() / "outputs"
        Path.mkdir(exist_ok=True)
        filename= "_summary.txt"
        Path.write_text(output_dir / filename, encoding="utf-8")
        raise ValueError from e

    tokens = {}
    # "completion_tokens_details": {"reasoning_tokens":0   },
    if hasattr(response, 'usage') and response.usage:
        tokens = {
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens
        }
        if hasattr(response.usage,"completion_tokens_details"):
            tokens["reasoning_tokens"] = getattr(response.usage.completion_tokens_details, "reasoning_tokens", 0)

    return data, tokens
