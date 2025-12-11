import io
import contextlib
import pandas as pd
import matplotlib.pyplot as plt

class PythonSandbox:
    def __init__(self):
        self.shared_context = {}

    def execute(self, code: str):
        output_buffer = io.StringIO()
        try:
            with contextlib.redirect_stdout(output_buffer):
                exec(code, globals(), self.shared_context)
            return {"success": True, "output": output_buffer.getvalue()}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def load_data(self, file_path: str):
        try:
            df = pd.read_csv(file_path)
            self.shared_context["df"] = df
            return f"Data loaded! Shape: {df.shape}. Columns: {list(df.columns)}"
        except Exception as e:
            return f"Error loading CSV: {e}"