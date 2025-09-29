import pandas as pd

def parse_resume_data(file_path):
    """
    Reads the resume Excel file with 5 sheets and returns a dictionary of structured info.
    """
    xl = pd.ExcelFile(file_path)
    resume_data = {}

    for sheet in xl.sheet_names:
        df = xl.parse(sheet)
        df.dropna(how="all", inplace=True)
        sheet_info = {}

        for index, row in df.iterrows():
            for col in df.columns:
                val = str(row[col]).strip() if pd.notna(row[col]) else None
                if val:
                    sheet_info[f"{col}_{index+1}"] = val
        
        resume_data[sheet] = sheet_info

    return resume_data

