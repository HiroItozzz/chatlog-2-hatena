from ch2hatena.main import main
import sys

if __name__ == "__main__":
    if len(sys.argv) > 1:
        input_paths_raw = sys.argv[1:]
    else:
        print.info("エラー: 入力が正しくありません。実行を終了します")
        sys.exit(1)

    try:
        exit_code = main(input_paths_raw)  # メイン処理

        print("アプリケーションは正常に終了しました。")
        sys.exit(exit_code)

    except Exception as e:
        print(
            "エラーが発生しました。\n実行を終了します。",
            exc_info=True,
        )
        sys.exit(1)
    main()
