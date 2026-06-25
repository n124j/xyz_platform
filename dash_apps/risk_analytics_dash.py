"""
XYZ Platform — Plotly Dash Risk Analytics App

Mounted at: /django_plotly_dash/app/RiskAnalyticsApp/

Provides:
  - Value at Risk (VaR) fan chart
  - Correlation heatmap
  - Drawdown chart
  - Efficient frontier scatter
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.figure_factory as ff
import dash_bootstrap_components as dbc
from dash import dcc, html, Input, Output
from django_plotly_dash import DjangoDash

app = DjangoDash(
    "RiskAnalyticsApp",
    external_stylesheets=[dbc.themes.BOOTSTRAP],
    title="XYZ Risk Analytics",
)

TICKERS = ["AAPL", "MSFT", "JPM", "GS", "TLT", "GLD", "BRK.B", "AMZN"]


def _simulate_returns(n_assets=8, n_days=252):
    np.random.seed(7)
    cov = np.random.uniform(0.0001, 0.0004, (n_assets, n_assets))
    cov = (cov + cov.T) / 2
    np.fill_diagonal(cov, np.random.uniform(0.0004, 0.002, n_assets))
    means = np.random.uniform(-0.0002, 0.001, n_assets)
    returns = np.random.multivariate_normal(means, cov, n_days)
    return pd.DataFrame(returns, columns=TICKERS[:n_assets])


def _var_fan(portfolio_returns, confidence_levels=(0.90, 0.95, 0.99)):
    horizon = np.arange(1, 22)
    mu = portfolio_returns.mean()
    sigma = portfolio_returns.std()
    result = {}
    for cl in confidence_levels:
        z = abs(np.percentile(portfolio_returns, (1 - cl) * 100))
        result[cl] = [-z * np.sqrt(h) * 100 for h in horizon]
    return horizon, result


app.layout = dbc.Container(
    fluid=True,
    className="p-3",
    children=[
        dbc.Row([
            dbc.Col([
                html.Label("Account / Portfolio", className="small fw-semibold text-muted"),
                dcc.Dropdown(
                    id="scope-dd",
                    options=[{"label": f"Account {i+1:04d}", "value": f"ACC{i+1:04d}"} for i in range(5)],
                    value="ACC0001", clearable=False, className="mb-3",
                ),
            ], md=3),
            dbc.Col([
                html.Label("Lookback (Trading Days)", className="small fw-semibold text-muted"),
                dcc.Slider(id="lookback-sl", min=63, max=504, step=63, value=252,
                           marks={63:"3M", 126:"6M", 252:"1Y", 378:"18M", 504:"2Y"},
                           className="mt-2"),
            ], md=5),
        ]),
        dbc.Row([
            dbc.Col(dcc.Graph(id="var-fan-chart"), md=6),
            dbc.Col(dcc.Graph(id="drawdown-chart"), md=6),
        ], className="mb-3"),
        dbc.Row([
            dbc.Col(dcc.Graph(id="corr-heatmap"), md=6),
            dbc.Col(dcc.Graph(id="efficient-frontier"), md=6),
        ]),
    ],
)


@app.callback(Output("var-fan-chart", "figure"), Input("scope-dd", "value"), Input("lookback-sl", "value"))
def update_var_fan(scope, lookback):
    rets = _simulate_returns(n_days=lookback)
    portfolio_rets = rets.mean(axis=1).values
    horizon, fan = _var_fan(portfolio_rets)

    fig = go.Figure()
    colors = {"0.9": "rgba(253,126,20,.25)", "0.95": "rgba(220,53,69,.4)", "0.99": "rgba(114,46,209,.5)"}
    labels = {0.90: "90% VaR", 0.95: "95% VaR", 0.99: "99% VaR"}

    for cl in (0.90, 0.95, 0.99):
        fig.add_trace(go.Scatter(
            x=list(horizon), y=fan[cl], mode="lines+markers",
            name=labels[cl], fill="tozeroy",
            line=dict(width=2),
            hovertemplate=f"Horizon: %{{x}}D<br>{labels[cl]}: %{{y:.2f}}%<extra></extra>",
        ))

    fig.update_layout(
        title="Value at Risk — Multi-horizon Fan Chart", plot_bgcolor="white",
        xaxis_title="Horizon (Trading Days)", yaxis_title="VaR (% NAV)",
        legend=dict(orientation="h"), margin=dict(l=40, r=10, t=40, b=40), height=300,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


@app.callback(Output("drawdown-chart", "figure"), Input("scope-dd", "value"), Input("lookback-sl", "value"))
def update_drawdown(scope, lookback):
    np.random.seed(42)
    rets = pd.Series(np.random.normal(0.0004, 0.009, lookback))
    cum = (1 + rets).cumprod()
    peak = cum.cummax()
    drawdown = (cum - peak) / peak * 100

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=list(range(lookback)), y=drawdown, fill="tozeroy",
        line=dict(color="#dc3545", width=1.5),
        fillcolor="rgba(220,53,69,.15)",
        hovertemplate="Day %{x}<br>Drawdown: %{y:.2f}%<extra></extra>",
    ))
    max_dd = drawdown.min()
    fig.add_annotation(text=f"Max DD: {max_dd:.2f}%", xref="paper", yref="paper",
                       x=0.02, y=0.05, showarrow=False, font=dict(color="#dc3545", size=12))
    fig.update_layout(
        title="Portfolio Drawdown (%)", plot_bgcolor="white",
        xaxis_title="Trading Days", yaxis_title="Drawdown (%)",
        margin=dict(l=40, r=10, t=40, b=40), height=300,
    )
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig


@app.callback(Output("corr-heatmap", "figure"), Input("lookback-sl", "value"))
def update_corr(lookback):
    rets = _simulate_returns(n_days=lookback)
    corr = rets.corr().round(2)
    z = corr.values.tolist()
    labels = TICKERS[:8]

    fig = ff.create_annotated_heatmap(
        z=z, x=labels, y=labels, annotation_text=[[f"{v:.2f}" for v in row] for row in z],
        colorscale="RdBu", reversescale=True, zmin=-1, zmax=1,
    )
    fig.update_layout(
        title="Asset Correlation Matrix", margin=dict(l=80, r=10, t=60, b=60), height=320
    )
    return fig


@app.callback(Output("efficient-frontier", "figure"), Input("lookback-sl", "value"))
def update_frontier(lookback):
    rets = _simulate_returns(n_days=lookback)
    n_portfolios = 3000
    np.random.seed(0)
    weights = np.random.dirichlet(np.ones(8), n_portfolios)
    mean_rets = rets.mean().values * 252
    cov_ann = rets.cov().values * 252

    port_rets = weights @ mean_rets * 100
    port_vols = np.sqrt(np.einsum("ij,jk,ik->i", weights, cov_ann, weights)) * 100
    sharpes = port_rets / port_vols

    fig = go.Figure(go.Scatter(
        x=port_vols, y=port_rets, mode="markers",
        marker=dict(size=4, color=sharpes, colorscale="Viridis", showscale=True,
                    colorbar=dict(title="Sharpe")),
        hovertemplate="Vol: %{x:.2f}%<br>Return: %{y:.2f}%<extra></extra>",
    ))
    fig.update_layout(
        title="Efficient Frontier (Simulated)", plot_bgcolor="white",
        xaxis_title="Annualised Volatility (%)", yaxis_title="Annualised Return (%)",
        margin=dict(l=50, r=10, t=40, b=40), height=320,
    )
    fig.update_xaxes(showgrid=True, gridcolor="#f0f0f0")
    fig.update_yaxes(showgrid=True, gridcolor="#f0f0f0")
    return fig
