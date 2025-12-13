def test_flow(__create_ai_client, __test_summarize_and_upload):
    preset = ["foo"]
    llm_conf = {"model": "gemini-2.5-flash"}
    secret = {
        "client_key": 4,
        "client_secret": 1,
        "resource_owner_key": 2,
        "resource_owner_secret": 3,
        "callback_uri": 1,
    }

    result, stats = __test_summarize_and_upload(preset, llm_conf, secret)

    assert result["title"] == "Test Title"
    assert stats["input_tokens"] == 100
