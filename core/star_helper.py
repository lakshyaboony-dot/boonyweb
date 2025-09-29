# star_helper.py
import gspread
import pandas as pd
import datetime
from oauth2client.service_account import ServiceAccountCredentials


class StarHelper:
    def __init__(self, creds_path="core/creds.json"):
        from oauth2client.service_account import ServiceAccountCredentials
        import gspread
        scope = ["https://spreadsheets.google.com/feeds",
                 "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
        self.client = gspread.authorize(creds)

    def get_stars(self):
        import pandas as pd
        import datetime

        try:
            sh_user = self.client.open("boony_user_data").sheet1
            df_users = pd.DataFrame(sh_user.get_all_records())
            df_users = df_users[["User ID", "Full Name"]].dropna(subset=["User ID"])
            df_users["User ID"] = df_users["User ID"].astype(str).str.strip()
            df_users["Full Name"] = df_users["Full Name"].astype(str).str.strip()
        except:
            return {"star_day": "N/A", "star_week": "N/A"}

        try:
            sh_prog = self.client.open("boony_user_progress")
            all_dfs = []
            for ws in sh_prog.worksheets():
                data = ws.get_all_records()
                if not data:
                    continue
                df = pd.DataFrame(data)
                df["User ID"] = ws.title.strip()
                if "Date" in df.columns:
                    df["Date"] = pd.to_datetime(df["Date"], errors="coerce").dt.date
                else:
                    df["Date"] = None
                if "Total Credits" not in df.columns:
                    df["Total Credits"] = 0
                all_dfs.append(df)

            if not all_dfs:
                return {"star_day": "N/A", "star_week": "N/A"}

            df_progress = pd.concat(all_dfs, ignore_index=True)
            df_progress = df_progress.dropna(subset=["Date"])
        except:
            return {"star_day": "N/A", "star_week": "N/A"}

        today = datetime.date.today()
        yesterday = today - datetime.timedelta(days=1)
        week_start = yesterday - datetime.timedelta(days=yesterday.weekday())

        # --- Star of the Day ---
        df_yesterday = df_progress[df_progress["Date"] == yesterday]
        if not df_yesterday.empty:
            idx = df_yesterday["Total Credits"].idxmax()
            star_day_id = df_yesterday.loc[idx, "User ID"].strip()
            star_day_name = df_users.loc[df_users["User ID"] == star_day_id, "Full Name"].values
            star_day_name = star_day_name[0] if len(star_day_name) > 0 else star_day_id
            star_day_name = f"{star_day_name} ({star_day_id})"
        else:
            star_day_name = "No activity yesterday"

        # --- Star of the Week ---
        df_week = df_progress[(df_progress["Date"] >= week_start) & (df_progress["Date"] <= yesterday)]
        if not df_week.empty:
            df_week_sum = df_week.groupby("User ID")["Total Credits"].sum()
            star_week_id = df_week_sum.idxmax().strip()
            star_week_name = df_users.loc[df_users["User ID"] == star_week_id, "Full Name"].values
            star_week_name = star_week_name[0] if len(star_week_name) > 0 else star_week_id
            star_week_name = f"{star_week_name} ({star_week_id})"
        else:
            star_week_name = "No activity last week"

        return {"star_day": star_day_name, "star_week": star_week_name}
