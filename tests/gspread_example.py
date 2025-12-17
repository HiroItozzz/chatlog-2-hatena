import os

import gspread
from dotenv import load_dotenv

load_dotenv()

SPREADSHEET_ID = os.getenv("SPREADSHEET_ID")

new_data = {"sample": "data1", "sample_2": "data2"}


def to_spreadsheet(new_data: dict) -> None:
    SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    if SPREADSHEET_ID:
        gc = gspread.oauth(scopes=SCOPES, credentials_filename="credentials.json")
        try:
            # スプレッドシートを開く（存在チェック）
            sh = gc.open_by_key(SPREADSHEET_ID)
            worksheet = sh.sheet1

            # 行数をチェック（新規か追記か判定）
            if worksheet.row_count == 0:
                # 新規作成時: ヘッダーを追加してからデータを挿入
                worksheet.update([list(new_data.keys())] + [list(new_data.values())])
                print("新規作成: ヘッダーとデータを追加しました")
            else:
                # 追記時: 一番下に追加（効率的）
                worksheet.append_row(list(new_data.values()))
                print("追記: 新しい行を追加しました")

        except gspread.exceptions.SpreadsheetNotFound:
            # スプレッドシートが存在しない場合、新規作成
            sh = gc.create("chatlog_record")
            worksheet = sh.sheet1
            worksheet.update([list(new_data.keys())] + [list(new_data.values())])
            print("新規スプレッドシートを作成し、データを追加しました")

        print(sh.sheet1.get("A1"))
