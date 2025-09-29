import os
import pandas as pd
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from core.resource_helper import resource_path

LOCAL_PROGRESS = resource_path("data/syllabus/boony_user_progress.xlsx")


def _get_client():
    creds_path = resource_path("core/creds.json")
    scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    return gspread.authorize(creds)


def update_progress(user_id, day, activity, value, last_stage=None, last_statement=None):
    """
    Update progress for Listen/Speak/Vocabulary (both local Excel + Google Sheet).
    - user_id: str
    - day: e.g. "Day-1"
    - activity: one of "Listen", "Speak", "Vocabulary"
    - value: int (credits to add)
    - last_stage: optional str (Listen / Speak / Vocabulary)
    - last_statement: optional int (which statement index)
    """

    today_str = pd.Timestamp.today().strftime("%Y-%m-%d")
    expected_day = str(day).strip()
    if not expected_day.startswith("Day-"):
        expected_day = f"Day-{expected_day}"

    # ---------- LOCAL SAVE ----------
    try:
        if os.path.exists(LOCAL_PROGRESS):
            df = pd.read_excel(LOCAL_PROGRESS, sheet_name=user_id)
        else:
            df = pd.DataFrame(columns=[
                "Date", "Day", "Listen", "Speak", "Vocabulary",
                "Total Credits", "LastStage", "LastStatement"
            ])

        # Ensure all required columns exist
        for col in ["Date", "day", "Listen", "Speak", "Vocabulary",
                    "Total Credits", "LastStage", "LastStatement"]:
            if col not in df.columns:
                df[col] = None

        # find row
        row_idx = df.index[df["day"].astype(str).str.strip() == expected_day].tolist()

        if row_idx:
            idx = row_idx[0]
            df.at[idx, activity] = int(df.at[idx, activity] or 0) + value
            df.at[idx, "Date"] = today_str
            if last_stage is not None:
                df.at[idx, "LastStage"] = last_stage
            if last_statement is not None:
                df.at[idx, "LastStatement"] = int(last_statement)
        else:
            # create new row if not exists
            new_row = {
                "Date": today_str,
                "day": expected_day,
                "Listen": 0,
                "Speak": 0,
                "Vocabulary": 0,
                "Total Credits": 0,
                "LastStage": last_stage or "",
                "LastStatement": last_statement or ""
            }
            new_row[activity] = value
            new_row["Total Credits"] = value
            df = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)

        # recalc total credits
        df["Total Credits"] = df[["Listen", "Speak", "Vocabulary"]].fillna(0).sum(axis=1).astype(int)

        with pd.ExcelWriter(LOCAL_PROGRESS, engine="openpyxl", mode="a", if_sheet_exists="replace") as writer:
            df.to_excel(writer, sheet_name=user_id, index=False)

        print(f"💾 Local Update → {user_id}, {expected_day}, {activity} +{value}, "
              f"LastStage={last_stage}, LastStatement={last_statement}")
    except Exception as e:
        print("❌ Local update failed:", e)

    # ---------- GOOGLE SHEET SAVE ----------
    try:
        client = _get_client()
        sheet = client.open("boony_user_progress").worksheet(user_id)
        headers = sheet.row_values(1)
        if "day" not in headers:
            raise Exception("Google Sheet missing 'day' column!")

        cell = sheet.find(expected_day)  # search exact day
        if cell:
            row_idx = cell.row
            updates = []
            if activity in ["Listen", "Speak", "Vocabulary"]:
                current_val = sheet.cell(row_idx, headers.index(activity) + 1).value
                current_val = int(current_val) if str(current_val).strip().isdigit() else 0
                new_val = current_val + value
                updates.append({
                    "range": (row_idx, headers.index(activity) + 1),
                    "values": [[new_val]]
                })

            if last_stage is not None:
                updates.append({
                    "range": (row_idx, headers.index("LastStage") + 1),
                    "values": [[last_stage]]
                })
            if last_statement is not None:
                updates.append({
                    "range": (row_idx, headers.index("LastStatement") + 1),
                    "values": [[int(last_statement)]]
                })

            updates.append({
                "range": (row_idx, headers.index("Date") + 1),
                "values": [[today_str]]
            })

            from gspread.utils import rowcol_to_a1

            sheet.batch_update([
                {"range": rowcol_to_a1(r['range'][0], r['range'][1]), "values": r["values"]}
                for r in updates
            ])
            print(f"☁️ Google Update → {user_id}, {expected_day}, {activity} +{value}")
        else:
            # create new row if not exists
            new_row = [today_str, expected_day, 0, 0, 0, 0, "", ""]
            col_pos = {h: i for i, h in enumerate(headers)}
            new_row[col_pos[activity]] = value
            new_row[col_pos["Total Credits"]] = value
            if last_stage:
                new_row[col_pos["LastStage"]] = last_stage
            if last_statement:
                new_row[col_pos["LastStatement"]] = int(last_statement)
            sheet.append_row(new_row)
            print(f"➕ Google Row Created → {user_id}, {expected_day}, {activity} +{value}")
    except Exception as e:
        print("❌ Google update failed:", e)
