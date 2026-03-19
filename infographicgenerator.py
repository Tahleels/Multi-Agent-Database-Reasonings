import json
import logging
import os
from typing import Optional, Dict, Any
from datetime import datetime
import anthropic
from langchain_anthropic import ChatAnthropic
from dotenv import load_dotenv
import chartselector as cs
 
load_dotenv()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
 
class InfographicGenerator:
    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        if not self.api_key:
            print("⚠️ WARNING: Missing ANTHROPIC_API_KEY. Infographic LLM generation will be disabled.")
            self.llm = None
        else:
            self.llm = ChatAnthropic(
                model="claude-sonnet-4-20250514",
                temperature=0.1,
                anthropic_api_key=self.api_key,
            )
        self.system_prompt = self._get_system_prompt()
 
    def _get_system_prompt(self) -> str:
        return """
        You are a precise AI Infographic Planner. Your task is to convert a data summary into a structured JSON plan for an infographic. You MUST follow all rules exactly.
 
        **CRITICAL RULES:**
        1. Your response MUST be a single, valid JSON object. Do not include any text before or after the JSON.
        2. The `widgets` array MUST NOT BE EMPTY.
        3. **The `widgets` array MUST CONTAIN AT LEAST ONE object where `widget_type` is "chart". This is a mandatory requirement.**
 
        **AVAILABLE WIDGETS & CHART TYPES:**
        1.  `widget_type`: **"kpi_showcase"** - For 2-4 key summary numbers.
        2.  `widget_type`: **"breakdown_list"** - For a detailed list of categories.
        3.  `widget_type`: **"chart"** - For visual graphs.
            - `chart_type`: Must be one of **"bar", "line", "pie", "doughnut", "bubble", "radar"**.
            - For **Clustered Bar** or **Multi-Line** charts, provide multiple objects in the `datasets` array.
            - **Bubble Chart** `data` objects must be in the format `{"x": 10, "y": 20, "r": 5}`.
 
        **EXAMPLE DATA STRUCTURES:**
        - **KPI:** `{"widget_type": "kpi_showcase", "data": [{"label": "Total Orders", "value": "50"}]}`
        - **List:** `{"widget_type": "breakdown_list", "data": [{"label": "Completed", "value": "12 Orders"}]}`
        - **Bar/Line Chart:** `{"widget_type": "chart", "chart_type": "bar", "title": "Title", "data": {"labels": ["A", "B"], "datasets": [{"label": "Count", "data": [10, 20]}]}}`
        - **Bubble Chart:** `{"widget_type": "chart", "chart_type": "bubble", "title": "Title", "data": {"datasets": [{"label": "Metrics", "data": [{"x": 15, "y": 25, "r": 8}]}]}}`
        """
 
    def generate_infographic_layout(self, summary_points: list, rows: list) -> Optional[Dict[str, Any]]:
        """
        summary_points = the model's insights
        rows = actual SQL data
        """

        # ---------------------------------------------------------
        # ⭐ REPLACE INSIGHTS WITH REAL DATA-DRIVEN SUMMARY
        # ---------------------------------------------------------
        import pandas as pd
        df = pd.DataFrame(rows)

        auto_summary = []

        # 📌 1. Row + Column count
        auto_summary.append(f"Dataset contains {len(df)} rows.")
        auto_summary.append(f"The dataset has {len(df.columns)} fields.")

        # 📌 2. Most Common Values for Categorical Fields
        for col in df.columns:
            if df[col].dtype == "object":
                top = df[col].value_counts().nlargest(1)
                if not top.empty:
                    auto_summary.append(
                        f"Most common {col}: {top.index[0]} ({top.iloc[0]} occurrences)."
                    )

        # 📌 3. Stats for Numeric Fields
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                auto_summary.append(
                    f"Field '{col}' → min: {df[col].min()}, max: {df[col].max()}, avg: {round(df[col].mean(), 2)}"
                )

        # 👑 Final summary_points used for the infographic
        summary_points = auto_summary
        summary = "\n".join(summary_points)

        logger.info("Generating infographic plan for summary...")

        if self.llm is None:
            logger.info("No LLM available; returning fallback infographic layout.")
            final_infographic = {
                "title": "Fallback Infographic",
                "subtitle": "Generated without Anthropic API key",
                "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "widgets": [
                    cs.build_summary_widget(auto_summary)
                ]
            }

            # Add a simple numeric chart widget when possible
            numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
            if len(df.columns) >= 1 and numeric_cols:
                label_col = df.columns[0]
                value_col = numeric_cols[0]
                labels = df[label_col].astype(str).tolist()[:10]
                values = df[value_col].tolist()[:10]
                final_infographic["widgets"].append(
                    cs.build_chart_widget(
                        chart_type="bar",
                        title=f"{value_col} by {label_col}",
                        labels=labels,
                        datasets=[{"label": value_col, "data": values}]
                    )
                )

            return final_infographic

        # ---------------------------------------------------------
        # ⭐ DO NOT TOUCH BELOW — your original logic stays same
        # ---------------------------------------------------------

        raw_plan = ""
        try:
            prompt = f"""You are given the actual dataset and the insights. Use BOTH to generate a highly meaningful infographic.

                            =====================
                            DATASET (use this for charts, KPIs, breakdowns):
                            {json.dumps(rows[:50], indent=2)}

                            =====================
                            INSIGHTS (auto-generated):
                            {summary}

                            =====================
                            REQUIREMENTS:
                            - Use REAL DATA (categories, prices, counts, numeric analysis)
                            - Do NOT produce metadata-only summaries (like “5 fields”)
                            - Generate useful business charts:
                                - Category distribution
                                - Price distribution
                                - Top items
                                - Avg values
                            - widgets MUST NOT be empty
                            - MUST include >=1 chart widget
                            - Respond with ONLY valid JSON
                            """

            messages = [("system", self.system_prompt), ("human", prompt)]
            response = self.llm.invoke(messages)
            raw_plan = response.content.strip()
            if raw_plan.startswith("```json"):
                raw_plan = raw_plan[7:-3].strip()

            layout_plan = json.loads(raw_plan)

        except Exception as e:
            logger.error(f"Failed to parse layout plan: {e}")
            logger.error(f"Raw LLM output: {raw_plan}")
            return None

        # --- VALIDATION STEP ---
        has_chart = any(widget.get("widget_type") == "chart" for widget in layout_plan.get("widgets", []))
        if not has_chart:
            logger.warning("LLM plan contains no chart. Aborting.")
            return None

        final_infographic = {
            "title": layout_plan.get("title", "Data Report"),
            "subtitle": layout_plan.get("subtitle", "A Maxnet AI-generated overview."),
            "generated_at": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            "widgets": []
        }

        # Add summary widget
        if summary_points:
            summary_widget = cs.build_summary_widget(summary_points)
            final_infographic["widgets"].append(summary_widget)

        # Build remaining widgets
        for widget_plan in layout_plan.get("widgets", []):
            widget_type = widget_plan.get("widget_type")
            try:
                widget_json = None
                if widget_type == "kpi_showcase":
                    widget_json = cs.build_kpi_widget(widget_plan["data"])
                elif widget_type == "breakdown_list":
                    widget_json = cs.build_breakdown_widget(
                        title=widget_plan.get("title", "Detailed Breakdown"),
                        items=widget_plan["data"]
                    )
                elif widget_type == "chart":
                    widget_json = cs.build_chart_widget(
                        chart_type=widget_plan["chart_type"],
                        title=widget_plan["title"],
                        labels=widget_plan.get("data", {}).get("labels"),
                        datasets=widget_plan.get("data", {}).get("datasets")
                    )
                if widget_json:
                    final_infographic["widgets"].append(widget_json)
                else:
                    logger.warning(f"Unknown widget type: {widget_type}")
            except KeyError as e:
                logger.error(f"Missing key {e} in widget: {widget_type}")

        # Save JSON
        try:
            save_dir = r'E:\chatbot_flask\infographic_jsons'
            os.makedirs(save_dir, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            file_path = os.path.join(save_dir, f'infographic_layout_{timestamp}.json')
            with open(file_path, 'w') as f:
                json.dump(final_infographic, f, indent=2)
            logger.info(f"Saved infographic JSON to {file_path}")
        except Exception as e:
            logger.error(f"Failed to save infographic JSON: {e}")

        return final_infographic

 


#==========================================================================================================================


