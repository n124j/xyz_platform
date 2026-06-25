"""
XYZ Platform — Plotly Dash Portfolio Dashboard App

Mounted into Django via django-plotly-dash at:
  /django_plotly_dash/app/PortfolioDashApp/

Provides interactive:
  - Asset allocation sunburst / pie chart
  - AUM waterfall (contributions vs withdrawals)
  - Rolling return vs benchmark line chart
  - Performance attribution bar chart
"""
import dash
from dash import dcc, html, Input, Output, callback
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
import numpy as np
from django_plotly_dash import DjangoDash

app = DjangoDash(
    "PortfolioDashApp",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="XYZ Portfolio Dashboard",
)

# ─── Synthetic sample data (replaced by DB queries via Django ORM) ─────────
def _sample_aum_series(days=252):
    np.random.seed(42)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=days)
    returns = np.random.normal(0.0003, 0.008, days)
    aum = 5_000_000_000 * (1 + returns).cumprod()
    benchmark = 5_000_000_000 * (1 + np.random.normal(0.00025, 0.007, days)).cumprod()
    return pd.DataFrame({"date": dates, "aum": aum, "benchmark": benchmark})


ALLOCATION = {
    "Equity": {
        "US Large Cap": 22.5, "US Small Cap": 5.0,
        "International Developed": 12.0, "Emerging Markets": 4.5,
    },
    "Fixed Income": {
        "US Treasuries": 10.0, "IG Corporate": 8.0,
        "High Yield": 4.0, "Municipal": 3.0,
    },
    "Alternatives": {"Hedge Funds": 8.0, "Private Equity": 6.0, "Real Estate": 4.0},
    "Cash": {"Money Market": 7.0, "Short-term Bonds": 6.0},
}

ATTRIBUTION = pd.DataFrame({
    "asset_class": ["US Equity", "Intl Equity", "Fixed Income", "Alternatives"],
    "allocation_effect": [0.42, -0.18, 0.08, 0.35],
    "selection_effect":  [0.85, 0.22, -0.12, 0.65],
    "total_effect":      [1.27, 0.04, -0.04, 1.00],
})

# ─── Layout ────────────────────────────────────────────────────────────────
app.layout = dbc.Container(
    fluid=True,
    className="p-3",
    children=[
        dbc.Row([
            dbc.Col([
                html.Label("Period", className="small fw-semibold text-muted"),
                dcc.Dropdown(
                    id="period-dd",
                    options=[
                        {"label": "YTD", "value": 65},
                        {"label": "6 Months", "value": 126},
                        {"label": "1 Year", "value": 252},
                        {"label": "3 Years", "value": 756},
                    ],
                    value=252,
                    clearable=False,
                    className="mb-3",
                ),
            ], md=2),
            dbc.Col([
                html.Label("Benchmark", className="small fw-semibold text-muted"),
                dcc.Dropdown(
                    id="benchmark-dd",
                    options=[
                        {"label": "S&P 500", "value": "sp500"},
                        {"label": "MSCI World", "value": "msci_world"},
                        {"label": "60/40 Blend", "value": "blend_6040"},
                    ],
                    value="sp500",
                    clearable=False,
                    className="mb-3",
                ),
            ], md=2),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="aum-trend-chart"), md=8),
            dbc.Col(dcc.Graph(id="allocation-sunburst"), md=4),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="attribution-chart"), md=6),
            dbc.Col(dcc.Graph(id="rolling-return-chart"), md=6),
        ]),
    ],
)


# ─── Callbacks ─────────────────────────────────────────────────────────────
@app.callback(
    Output("aum-trend-chart", "figure"),
    Input("period-dd", "value"),
    Input("benchmark-dd", "value"),
)
def update_aum_chart(days, benchmark):
    df = _sample_aum_series(days)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["aum"] / 1e9, mode="lines",
        name="XYZ Portfolio", line=dict(color="#0d6efd", width=2),
        hovertemplate="%{x|%b %d, %Y}<br>AUM: $%{y:.2f}B<extra></extra>",
    ))
    fig.add_trace(go.Scatter(
        x=df["date"], y=df["benchmark"] / 1e9, mode="lines",
        name=benchmark.upper().replace("_", " "), line=dict(color="#fd7e14", width=1.5, dash="dash"),
        hovertemplate="%{x|%b %d, %Y}<br>Benchmark: $%{y:.2f}B<extra></extra>",
    ))
    fig.update_layout(
        title="AUM vs Benchmark (USD Billions)",
        xaxis_title=None, yaxis_title="AUM ($B)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        hovermode="x unified", plot_bgcolor="white",
        margin=dict(l=40, r=10, t=40, b=30),
        height=320,
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


@app.callback(Output("allocation-sunburst", "figure"), Input("period-dd", "value"))
def update_allocation(days):
    labels, parents, values = [], [], []
    for asset_class, sub in ALLOCATION.items():
        labels.append(asset_class)
        parents.append("")
        values.append(sum(sub.values()))
        for name, val in sub.items():
            labels.append(name)
            parents.append(asset_class)
            values.append(val)

    fig = go.Figure(go.Sunburst(
        labels=labels, parents=parents, values=values,
        branchvalues="total",
        hovertemplate="<b>%{label}</b><br>Weight: %{value:.1f}%<extra></extra>",
        marker=dict(colors=["#0d6efd","#198754","#6f42c1","#fd7e14"] + [""] * len(labels)),
    ))
    fig.update_layout(
        title="Asset Allocation", margin=dict(l=0, r=0, t=40, b=0), height=320
    )
    return fig


@app.callback(Output("attribution-chart", "figure"), Input("period-dd", "value"))
def update_attribution(days):
    df = ATTRIBUTION
    fig = go.Figure()
    fig.add_trace(go.Bar(name="Allocation Effect", x=df["asset_class"], y=df["allocation_effect"],
                         marker_color="#0d6efd"))
    fig.add_trace(go.Bar(name="Selection Effect", x=df["asset_class"], y=df["selection_effect"],
                         marker_color="#198754"))
    fig.update_layout(
        title="Performance Attribution (bps)", barmode="group",
        plot_bgcolor="white", legend=dict(orientation="h"),
        margin=dict(l=40, r=10, t=40, b=30), height=280,
        yaxis_title="Effect (bps)",
    )
    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0", zeroline=True, zerolinecolor="#aaa")
    return fig


@app.callback(Output("rolling-return-chart", "figure"), Input("period-dd", "value"))
def update_rolling_return(days):
    df = _sample_aum_series(days)
    df["portfolio_return"] = df["aum"].pct_change().rolling(21).mean() * 252 * 100
    df["benchmark_return"] = df["benchmark"].pct_change().rolling(21).mean() * 252 * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["portfolio_return"], name="Portfolio (21D Ann.)",
                             line=dict(color="#0d6efd", width=2),
                             hovertemplate="%{x|%b %d}<br>%{y:.2f}%<extra>Portfolio</extra>"))
    fig.add_trace(go.Scatter(x=df["date"], y=df["benchmark_return"], name="Benchmark",
                             line=dict(color="#fd7e14", width=1.5, dash="dash"),
                             hovertemplate="%{x|%b %d}<br>%{y:.2f}%<extra>Benchmark</extra>"))
    fig.add_hline(y=0, line_dash="dot", line_color="#aaa")
    fig.update_layout(
        title="21-Day Rolling Annualised Return", plot_bgcolor="white",
        legend=dict(orientation="h"), margin=dict(l=40, r=10, t=40, b=30),
        height=280, yaxis_title="Annualised Return (%)",
    )
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig
