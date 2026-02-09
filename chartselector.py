from typing import List, Dict, Any, Literal
 
# Define a consistent, modern color palette
GEMINI_COLORS = ['#4285F4', '#DB4437', '#F4B400', '#0F9D58', '#9B72F4', '#FF6384', '#4BC0C0']
 
def build_kpi_widget(metrics: List[Dict[str, str]]) -> Dict[str, Any]:
    """Builds a Key Performance Indicator (KPI) widget."""
    return {
        "widget_type": "kpi_showcase",
        "header": "Key Metrics",
        "icon": "key_metrics",
        "data": metrics
    }
 
def build_breakdown_widget(title: str, items: List[Dict[str, str]]) -> Dict[str, Any]:
    """Builds a list-style breakdown widget."""
    return {
        "widget_type": "breakdown_list",
        "header": title,
        "icon": "breakdown",
        "data": items
    }
 
def build_chart_widget(
    chart_type: Literal["bar", "line", "pie", "doughnut", "bubble", "radar"],
    title: str,
    labels: List[str] = None, # Labels are not always needed (e.g., bubble chart)
    datasets: List[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Builds a generic chart widget for various Chart.js types.
    Handles single and multi-dataset charts (for clustered bar / multi-line).
    """
    icon_map = {
        "bar": "bar_chart",
        "line": "line_chart",
        "pie": "pie_chart",
        "doughnut": "pie_chart",
        "bubble": "bar_chart",
        "radar": "pie_chart"
    }
 
    # Apply specific styling based on chart type
    if datasets:
        for i, ds in enumerate(datasets):
            color = GEMINI_COLORS[i % len(GEMINI_COLORS)]
           
            if chart_type in ["line", "radar"]:
                ds["borderColor"] = color
                ds["backgroundColor"] = f"{color}33" # Use semi-transparent version for fill
                ds["pointBackgroundColor"] = color
                ds["pointHoverBorderColor"] = color
                ds["borderWidth"] = 2 # CRITICAL: Sets the line thickness
                ds["fill"] = True
           
            elif chart_type == "bubble":
                 ds["backgroundColor"] = f"{color}B3" # Semi-transparent for bubbles
                 ds["borderColor"] = color
 
            else: # For bar, pie, doughnut
                if "backgroundColor" not in ds:
                    ds["backgroundColor"] = GEMINI_COLORS
                ds["borderWidth"] = 0
 
 
    return {
        "widget_type": "chart",
        "header": title,
        "icon": icon_map.get(chart_type, "bar_chart"),
        "chart_config": {
            "type": chart_type,
            "data": {
                "labels": labels,
                "datasets": datasets
            },
            "options": {
                "responsive": True,
                "maintainAspectRatio": False,
                "plugins": {
                    "legend": {
                        "position": "top",
                        "display": len(datasets) > 1 if datasets else False,
                    }
                },
                "scales": {} if chart_type in ["pie", "doughnut", "radar"] else {
                    "y": {"beginAtZero": True, "grid": {"color": "#e9ecef"}},
                    "x": {"grid": {"display": False}}
                },
                "cutout": "60%" if chart_type == "doughnut" else "0%",
                "elements": {
                    "line": { "tension": 0.4 }
                }
            }
        }
    }
 
def build_summary_widget(bullet_points: List[str]) -> Dict[str, Any]:
    """Builds a widget to display the initial summary bullet points."""
    return {
        "widget_type": "summary_list",
        "header": "Summary & Insights",
        "icon": "summary_icon", # We will use a default icon for this
        "data": bullet_points
    }