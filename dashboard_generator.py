import os
import json
import pandas as pd
import anthropic
from dotenv import load_dotenv

# --- Configuration ---
load_dotenv()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

if not ANTHROPIC_API_KEY:
    print("⚠️ WARNING: ANTHROPIC_API_KEY not found in environment variables. LLM-based dashboard generation will be disabled.")
    client = None
else:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

# --- LLM Logic to Generate Dashboard JSON ---
def get_dashboard_json_structure():
    """Returns the JSON structure the LLM needs to fill, with dynamic KPI instructions."""
    return """
    {
        "header": {
            "title": "A relevant, concise title for the dashboard based on the data.",
            "subtitle": "A short, descriptive subtitle."
        },
        "filters": [
            {
                "id": "filter1",
                "label": "Label for the first filter (e.g., 'Filter by Category')",
                "column_name": "The actual column name from the data to filter on.",
                "options": ["List", "of", "unique", "values", "from that column."]
            },
            {
                "id": "filter2",
                "label": "Label for the second filter (e.g., 'Filter by Region')",
                "column_name": "The actual column name for the second filter.",
                "options": ["List", "of", "unique", "values", "for the second filter."]
            }
        ],
        "kpi_cards": [
            {
                "id": "kpi1",
                "label": "Primary KPI Label",
                "calculation": "SUM",
                "column_name": "The column to sum (e.g., 'total_order_amount').",
                "prefix": "$"
            },
            {
                "id": "kpi2",
                "label": "Second KPI Label",
                "calculation": "AVERAGE",
                "column_name": "The column to average (e.g., 'total_order_amount').",
                "prefix": "$"
            },
            {
                "id": "kpi3",
                "label": "Third KPI Label",
                "calculation": "COUNT",
                "column_name": "The column to count (e.g., 'order_id').",
                "prefix": ""
            },
            {
                "id": "kpi4",
                "label": "Fourth KPI Label",
                "calculation": "COUNT_DISTINCT",
                "column_name": "The column for distinct count (e.g., 'customer_id').",
                "prefix": ""
            }
        ],
        "charts": [
            { "chart_id": "chart1", "title": "Chart Title", "type": "line", "data": { "label_column": "col", "value_column": "col", "dataset_label": "Label" }},
            { "chart_id": "chart2", "title": "Chart Title", "type": "doughnut", "data": { "label_column": "col", "value_column": "col", "dataset_label": "Label" }},
            { "chart_id": "chart3", "title": "Chart Title", "type": "bar", "data": { "label_column": "col", "value_column": "col", "dataset_label": "Label" }},
            { "chart_id": "chart4", "title": "Chart Title", "type": "bar", "data": { "label_column": "col", "value_column": "col", "dataset_label": "Label" }}
        ]
    }
    """

def generate_dashboard_config(df: pd.DataFrame):
    """Uses an LLM to analyze a DataFrame and generate a JSON config for the dashboard."""

    if client is None:
        # Fallback local dashboard config if Anthropic key is missing
        print("⚠️ ANTHROPIC_API_KEY missing. Returning fallback dashboard config.")
        filters = []
        for col in df.columns:
            if df[col].dtype == 'object' or df[col].nunique() < 20:
                filters.append({
                    "id": f"filter-{col}",
                    "label": col,
                    "column_name": col,
                    "options": df[col].dropna().unique().tolist()
                })
        filters = filters[:2]

        kpi_cards = []
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        for i, col in enumerate(numeric_cols[:4], start=1):
            kpi_cards.append({
                "id": f"kpi{i}",
                "label": f"{col} summary",
                "calculation": "SUM",
                "column_name": col,
                "prefix": "" if df[col].dtype != 'float' else ""
            })

        chart_items = []
        if len(df.columns) >= 2:
            chart_items.append({
                "chart_id": "chart1",
                "title": "Fallback chart",
                "type": "bar",
                "data": {"label_column": df.columns[0], "value_column": df.columns[1], "dataset_label": "Fallback"}
            })

        return {
            "header": {"title": "Fallback Dashboard", "subtitle": "No LLM key; basic layout generated."},
            "filters": filters,
            "kpi_cards": kpi_cards,
            "charts": chart_items
        }

    data_sample_csv = df.head(20).to_csv(index=False)
    column_info = "\n".join([f"- {col} ({dtype})" for col, dtype in df.dtypes.items()])
    json_structure = get_dashboard_json_structure()

    prompt = f"""
    You are a world-class data analyst. Your task is to act as a backend engine that creates a configuration JSON for a business intelligence dashboard.
    
    Analyze the provided CSV data sample and its schema. Based on your analysis, populate the given JSON structure to create a meaningful and insightful dashboard.

    **Data Schema (Columns and Types):**
    {column_info}

    **Data Sample (first 20 rows):**
    ```csv
    {data_sample_csv}
    ```

    **Instructions:**
    1.  **Analyze the data:** Identify key metrics, categorical dimensions, and time series data.
    2.  **Identify Filters:** Identify up to two key categorical columns useful for filtering. For each, provide a list of its unique values in the `filters` section.
    3.  **Define KPIs:** CRITICAL: For each KPI card, specify the `calculation` method ('SUM', 'AVERAGE', 'COUNT', 'COUNT_DISTINCT') and the `column_name` to apply it to. If it's a monetary value, set `prefix` to '$'.
    4.  **Configure Charts:** Map the data columns to the four charts, choosing appropriate columns for the specified chart types.
    5.  **Strict JSON Output:** Your final output MUST be ONLY the populated JSON object, enclosed in ```json ... ```. Do not include any other text or commentary.

    **JSON Structure to Populate:**
    {json_structure}
    """
    try:
        print("🤖 Sending request to LLM (with dynamic KPI instructions)...")
        message = client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}]
        ).content[0].text
        
        json_string = message.strip().split('```json\n')[1].split('\n```')[0]
        dashboard_config = json.loads(json_string)
        print("✅ Successfully generated and parsed dashboard JSON with dynamic KPIs.")
        return dashboard_config
    except (json.JSONDecodeError, IndexError) as e:
        print(f"Error: Failed to parse LLM response as JSON. Error: {e}")
        print("LLM Response was:\n", message)
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None