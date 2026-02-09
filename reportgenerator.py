import os
import json
import pandas as pd
import anthropic
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    raise ValueError("ANTHROPIC_API_KEY not found in environment variables. Please set it in a .env file.")

client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

def get_report_json_structure():
    """Returns the template JSON structure the LLM needs to fill for SSRS-style reports."""
    return {
        "header": {
            "title": "Report Title",
            "subtitle": "Report Subtitle"
        },
        "filters": [],
        "tables": []
    }

def generate_report_config(df: pd.DataFrame):
    """
    Generate SSRS-style report JSON config from a DataFrame.
    Uses LLM for intelligence, falls back to automatic config if LLM fails.
    """
    # --- Prepare filter candidates ---
    filters = []
    for col in df.columns:
        if df[col].dtype == 'object' or df[col].nunique() < 20:
            filters.append({
                "id": f"filter-{col}",
                "label": col,
                "column_name": col,
                "options": df[col].dropna().unique().tolist()
            })
    filters = filters[:2]  # Limit to 2 filters

    # --- Prepare table structure ---
    table_columns = []
    for col in df.columns:
        col_type = df[col].dtype
        agg = "GROUP" if col_type == 'object' else "SUM"
        table_columns.append({
            "column_name": col,
            "label": col,
            "aggregation": agg
        })

    table = {
        "id": "table1",
        "title": "Main Table",
        "columns": table_columns,
        "group_by": [c["column_name"] for c in table_columns if c["aggregation"] == "GROUP"],
        "sort_by": {
            "column_name": df.columns[0],
            "order": "DESC"
        }
    }

    report_config = {
        "header": {
            "title": "Tabular Report",
            "subtitle": "Generated report"
        },
        "filters": filters,
        "tables": [table]
    }

    # --- Optional: LLM-based enhancement ---
    try:
        data_sample_csv = df.head(20).to_csv(index=False)
        column_info = "\n".join([f"- {col} ({dtype})" for col, dtype in df.dtypes.items()])
        json_structure = json.dumps(get_report_json_structure(), indent=2)

        prompt = f"""
        You are a business intelligence analyst. Populate this JSON structure for an SSRS-style report.
        Analyze the schema and first 20 rows of data.

        Data Schema:
        {column_info}

        Data Sample (CSV):
        ```csv
        {data_sample_csv}
        ```

        JSON Structure:
        {json_structure}
        """

        print("🤖 Sending request to LLM for Report JSON...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text

        json_string = message.strip().split('```json\n')[1].split('\n```')[0]
        llm_report_config = json.loads(json_string)
        print("✅ Successfully generated report JSON via LLM.")
        return llm_report_config

    except Exception as e:
        print(f"⚠️ LLM generation failed, using default config. Error: {e}")
        return report_config

# ADD THIS FUNCTION - Similar to dashboard generator
def get_report_data_with_filters(df: pd.DataFrame, filters: dict = None):
    """Apply filters to dataframe and return filtered data for reporting"""
    filtered_df = df.copy()
    
    if filters:
        for column_name, value in filters.items():
            if column_name in filtered_df.columns and value != "All":
                filtered_df = filtered_df[filtered_df[column_name] == value]
    
    return {
        "columns": filtered_df.columns.tolist(),
        "rows": filtered_df.to_dict('records')
    }