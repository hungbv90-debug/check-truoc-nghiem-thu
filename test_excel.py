import glob
from data_processor import QALogic
qa = QALogic()
files = glob.glob('*.xlsx')
for f in files:
    try:
        df = qa.read_excel(f)
        print(f"--- {f} ---")
        print("Columns:", list(df.columns)[:20])
        print("Head:")
        print(df.head(2))
    except Exception as e:
        print(f"--- {f} ---")
        print(f"Error: {e}")
