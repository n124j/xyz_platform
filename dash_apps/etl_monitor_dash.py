"""
XYZ Platform — Plotly Dash ETL Monitor App

Mounted at: /django_plotly_dash/app/ETLMonitorApp/

Provides a Gantt-style pipeline run timeline and
DAG success-rate bar chart backed by the local DAGRun table.
"""

import random
from datetime import datetime, timedelta

import dash_bootstrap_components as dbc
import pandas as pd
import plotly.figure_factory as ff
import plotly.graph_objects as go
from dash import Input, Output, dcc, html
from django_plotly_dash import DjangoDash

app = DjangoDash(
    "ETLMonitorApp",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="XYZ ETL Monitor",
)

DAG_NAMES = [
    "portfolio_etl_dag",
    "market_data_dag",
    "risk_report_dag",
]

app.layout = dbc.Container(
    fluid=True,
    className="p-3",
    children=[
        dbc.Row(
            [
                dbc.Col(
                    [
                        html.Label(
                            "Date Range (days back)",
                            className="small fw-semibold text-muted",
                        ),
                        dcc.Slider(
                            id="days-sl",
                            min=1,
                            max=30,
                            step=1,
                            value=7,
                            marks={1: "1D", 7: "7D", 14: "14D", 30: "30D"},
                        ),
                    ],
                    md=6,
                ),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="gantt-chart"), md=12),
            ],
            className="mb-3",
        ),
        dbc.Row(
            [
                dbc.Col(dcc.Graph(id="success-rate-chart"), md=6),
                dbc.Col(dcc.Graph(id="duration-chart"), md=6),
            ]
        ),
    ],
)


def _synthetic_runs(days_back):
    """Generate synthetic run history (replaced by DAGRun.objects.all() in production)."""
    random.seed(42)
    rows = []
    now = datetime.utcnow()
    for dag in DAG_NAMES:
        for day_offset in range(days_back):
            run_start = now - timedelta(days=day_offset, hours=random.randint(0, 2))
            duration_m = random.uniform(3, 25)
            run_end = run_start + timedelta(minutes=duration_m)
            state = random.choices(["success", "failed", "running"], weights=[85, 10, 5])[0]
            rows.append(
                {
                    "DAG": dag,
                    "Start": run_start,
                    "Finish": run_end,
                    "State": state,
                    "Duration_m": duration_m,
                }
            )
    return pd.DataFrame(rows)


@app.callback(Output("gantt-chart", "figure"), Input("days-sl", "value"))
def update_gantt(days_back):
    df = _synthetic_runs(days_back)
    colors = {"success": "#198754", "failed": "#dc3545", "running": "#0d6efd"}

    tasks = []
    for _, row in df.iterrows():
        tasks.append(
            dict(
                Task=row["DAG"],
                Start=row["Start"].isoformat(),
                Finish=row["Finish"].isoformat(),
                Resource=row["State"],
            )
        )

    if not tasks:
        return go.Figure()

    fig = ff.create_gantt(
        tasks,
        colors=colors,
        index_col="Resource",
        show_colorbar=True,
        group_tasks=True,
        title=f"Pipeline Run Timeline — Last {days_back} Day(s)",
    )
    fig.update_layout(height=350, margin=dict(l=160, r=10, t=50, b=40))
    return fig


@app.callback(Output("success-rate-chart", "figure"), Input("days-sl", "value"))
def update_success_rate(days_back):
    df = _synthetic_runs(days_back)
    summary = df.groupby("DAG")["State"].apply(lambda s: (s == "success").sum() / len(s) * 100).reset_index()
    summary.columns = ["DAG", "SuccessRate"]

    fig = go.Figure(
        go.Bar(
            y=[d.replace("_dag", "").replace("_", " ").title() for d in summary["DAG"]],
            x=summary["SuccessRate"],
            orientation="h",
            marker_color=[
                "#198754" if v >= 90 else "#fd7e14" if v >= 70 else "#dc3545" for v in summary["SuccessRate"]
            ],
            text=[f"{v:.0f}%" for v in summary["SuccessRate"]],
            textposition="inside",
        )
    )
    fig.update_layout(
        title="DAG Success Rate (%)",
        plot_bgcolor="white",
        xaxis=dict(range=[0, 100], showgrid=True, gridcolor="#f0f0f0"),
        margin=dict(l=130, r=20, t=50, b=30),
        height=280,
    )
    return fig


@app.callback(Output("duration-chart", "figure"), Input("days-sl", "value"))
def update_duration(days_back):
    df = _synthetic_runs(days_back)
    success_df = df[df["State"] == "success"]

    fig = go.Figure()
    for dag in DAG_NAMES:
        sub = success_df[success_df["DAG"] == dag]
        fig.add_trace(
            go.Box(
                y=sub["Duration_m"],
                name=dag.replace("_dag", "").replace("_", " ").title(),
                boxmean=True,
            )
        )
    fig.update_layout(
        title="Run Duration Distribution (minutes)",
        plot_bgcolor="white",
        yaxis_title="Minutes",
        showlegend=False,
        margin=dict(l=50, r=10, t=50, b=40),
        height=280,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig
