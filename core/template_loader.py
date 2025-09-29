from docx import Document
import pandas as pd

def parse_docx_to_dataframe(docx_path):
    doc = Document(docx_path)
    data = {}
    current_field = None

    for para in doc.paragraphs:
        text = para.text.strip()
        if not text:
            continue

        if ":" in text:
            field, value = text.split(":", 1)
            field = field.strip()
            value = value.strip()
            data[field] = [field, value]
            current_field = field
        elif current_field:
            data[current_field].append(text)

    # 🔧 Normalize lengths
    max_length = max(len(v) for v in data.values())
    for key in data:
        while len(data[key]) < max_length:
            data[key].append("")  # Fill with blanks

    return pd.DataFrame.from_dict(data, orient="columns")
