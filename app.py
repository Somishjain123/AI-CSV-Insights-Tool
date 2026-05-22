"""
AI-CSV-Insights-Tool — Streamlit Dashboard
A professional CSV analytics dashboard with automatic insights,
data cleaning, visualization, and export capabilities.
"""

import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import os
import io
import warnings

warnings.filterwarnings("ignore")

# ──────────────────────────────────────────────
# PAGE CONFIG & THEME
# ──────────────────────────────────────────────
st.set_page_config(
    page_title="AI CSV Insights Tool",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────
# CUSTOM CSS — polished dark/modern look
# ──────────────────────────────────────────────
st.markdown("""
<style>
/* ---------- global ---------- */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

/* ---------- KPI cards ---------- */
.kpi-card {
    background: linear-gradient(135deg, #1e1e2f 0%, #2d2d44 100%);
    border: 1px solid rgba(255,255,255,.08);
    border-radius: 16px;
    padding: 24px 20px;
    text-align: center;
    box-shadow: 0 4px 24px rgba(0,0,0,.25);
    transition: transform .2s, box-shadow .2s;
}
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 8px 32px rgba(99,102,241,.25); }
.kpi-value { font-size: 2rem; font-weight: 700; color: #818cf8; margin: 4px 0; }
.kpi-label { font-size: .85rem; color: #94a3b8; text-transform: uppercase; letter-spacing: 1px; }

/* ---------- section headers ---------- */
.section-header {
    background: linear-gradient(90deg, #6366f1, #8b5cf6);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    font-size: 1.6rem;
    font-weight: 700;
    margin: 32px 0 12px;
}

/* ---------- insight box ---------- */
.insight-box {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
    border-left: 4px solid #6366f1;
    border-radius: 8px;
    padding: 16px 20px;
    margin: 8px 0;
    color: #e2e8f0;
    font-size: .95rem;
    line-height: 1.6;
}

/* ---------- sidebar ---------- */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #0f172a 0%, #1e1b4b 100%);
}
section[data-testid="stSidebar"] .stMarkdown { color: #cbd5e1; }

/* ---------- hero banner ---------- */
.hero {
    background: linear-gradient(135deg, #312e81 0%, #4338ca 50%, #6366f1 100%);
    border-radius: 20px;
    padding: 40px 36px;
    text-align: center;
    margin-bottom: 28px;
    box-shadow: 0 8px 40px rgba(99,102,241,.3);
}
.hero h1 { color: #fff; font-size: 2.4rem; margin: 0; }
.hero p  { color: #c7d2fe; font-size: 1.1rem; margin-top: 8px; }

/* ---------- misc ---------- */
.stDataFrame { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════
# HELPER FUNCTIONS
# ══════════════════════════════════════════════

def render_kpi(label: str, value, icon: str = "📌") -> str:
    """Return HTML for a single KPI metric card."""
    return f"""
    <div class="kpi-card">
        <div style="font-size:1.6rem;">{icon}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-label">{label}</div>
    </div>"""


def get_missing_info(df: pd.DataFrame) -> pd.DataFrame:
    """Return a DataFrame summarising missing values per column."""
    missing = df.isnull().sum()
    pct = (missing / len(df) * 100).round(2)
    info = pd.DataFrame({"Missing Values": missing, "Percentage (%)": pct})
    return info[info["Missing Values"] > 0].sort_values("Missing Values", ascending=False)


def generate_insights(df: pd.DataFrame) -> list[str]:
    """Produce a list of human-readable automatic insights."""
    insights = []
    rows, cols = df.shape
    insights.append(f"The dataset contains **{rows:,} rows** and **{cols} columns**.")

    # Numeric summary
    num_cols = df.select_dtypes(include="number").columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

    if num_cols:
        highest_col = df[num_cols].mean().idxmax()
        lowest_col = df[num_cols].mean().idxmin()
        insights.append(
            f"The column with the **highest average** is `{highest_col}` "
            f"(mean ≈ {df[highest_col].mean():,.2f})."
        )
        insights.append(
            f"The column with the **lowest average** is `{lowest_col}` "
            f"(mean ≈ {df[lowest_col].mean():,.2f})."
        )
        total_sum = df[num_cols].sum().sum()
        insights.append(f"The **total numeric sum** across all columns is {total_sum:,.2f}.")

    if cat_cols:
        for c in cat_cols[:3]:
            top = df[c].mode()
            if not top.empty:
                freq = df[c].value_counts().iloc[0]
                insights.append(
                    f"Most frequent value in `{c}` → **{top.iloc[0]}** "
                    f"(appears {freq:,} times)."
                )

    # Data quality
    total_missing = df.isnull().sum().sum()
    total_cells = rows * cols
    quality_pct = ((total_cells - total_missing) / total_cells * 100)
    insights.append(
        f"**Data quality score**: {quality_pct:.1f}% — "
        f"{total_missing:,} missing values out of {total_cells:,} cells."
    )

    dupes = df.duplicated().sum()
    if dupes:
        insights.append(f"⚠️ There are **{dupes} duplicate rows** in the dataset.")
    else:
        insights.append("✅ No duplicate rows detected.")

    return insights


def save_chart(fig, name: str):
    """Save a matplotlib figure to the charts/ folder."""
    os.makedirs("charts", exist_ok=True)
    path = os.path.join("charts", f"{name}.png")
    fig.savefig(path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    return path


# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════

with st.sidebar:
    st.markdown("## 🧭 Navigation")
    st.markdown("---")
    uploaded_file = st.file_uploader("📂 Upload a CSV file", type=["csv"])

    use_sample = st.checkbox("Use sample dataset", value=False)

    st.markdown("---")
    st.markdown("### ⚙️ Settings")
    chart_palette = st.selectbox(
        "Chart colour palette",
        ["viridis", "magma", "plasma", "cividis", "coolwarm", "Set2", "muted"],
        index=0,
    )
    show_raw = st.checkbox("Show raw data table", value=True)

    st.markdown("---")
    st.markdown(
        "<p style='text-align:center;color:#64748b;font-size:.75rem;'>"
        "Built with ❤️ using Streamlit</p>",
        unsafe_allow_html=True,
    )


# ══════════════════════════════════════════════
# LOAD DATA
# ══════════════════════════════════════════════

def load_data():
    """Load CSV from upload or sample file, return DataFrame or None."""
    if uploaded_file is not None:
        try:
            df = pd.read_csv(uploaded_file)
            if df.empty:
                st.error("The uploaded CSV is empty.")
                return None
            return df
        except Exception as e:
            st.error(f"Failed to parse CSV: {e}")
            return None
    elif use_sample:
        sample_path = os.path.join("data", "sample_sales_data.csv")
        if os.path.exists(sample_path):
            return pd.read_csv(sample_path)
        else:
            st.error("Sample dataset not found in `data/` folder.")
            return None
    return None


# ══════════════════════════════════════════════
# HERO / LANDING
# ══════════════════════════════════════════════

st.markdown(
    '<div class="hero">'
    "<h1>📊 AI CSV Insights Tool</h1>"
    "<p>Upload any CSV and unlock instant analytics, visualizations & smart insights</p>"
    "</div>",
    unsafe_allow_html=True,
)

raw_df = load_data()

if raw_df is None:
    st.info("👈 Upload a CSV from the sidebar — or check **Use sample dataset** to explore a demo.")
    st.stop()

# Keep a working copy in session state so cleaning ops persist
if "df" not in st.session_state or st.session_state.get("_src") != id(raw_df):
    st.session_state.df = raw_df.copy()
    st.session_state._src = id(raw_df)

df: pd.DataFrame = st.session_state.df

# ──────────────────────────────────────────────
# SIDEBAR — file analytics
# ──────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 📋 File Info")
    fname = uploaded_file.name if uploaded_file else "sample_sales_data.csv"
    st.markdown(f"**File:** `{fname}`")
    st.markdown(f"**Rows:** {df.shape[0]:,}")
    st.markdown(f"**Columns:** {df.shape[1]}")
    mem = df.memory_usage(deep=True).sum()
    if mem < 1024:
        mem_str = f"{mem} B"
    elif mem < 1048576:
        mem_str = f"{mem/1024:.1f} KB"
    else:
        mem_str = f"{mem/1048576:.2f} MB"
    st.markdown(f"**Memory:** {mem_str}")
    st.success("✅ Dataset loaded successfully")


# ══════════════════════════════════════════════
# KPI CARDS
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">📈 Key Metrics</p>', unsafe_allow_html=True)

num_cols = df.select_dtypes(include="number").columns.tolist()
cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.markdown(render_kpi("Total Rows", f"{df.shape[0]:,}", "🗂️"), unsafe_allow_html=True)
with k2:
    st.markdown(render_kpi("Total Columns", df.shape[1], "📐"), unsafe_allow_html=True)
with k3:
    missing_total = int(df.isnull().sum().sum())
    st.markdown(render_kpi("Missing Values", f"{missing_total:,}", "⚠️"), unsafe_allow_html=True)
with k4:
    dupes = int(df.duplicated().sum())
    st.markdown(render_kpi("Duplicates", f"{dupes:,}", "♻️"), unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 1 — DATASET PREVIEW
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">🔍 Dataset Preview</p>', unsafe_allow_html=True)

preview_tab, types_tab = st.tabs(["First 10 Rows", "Column Data Types"])

with preview_tab:
    if show_raw:
        st.dataframe(df.head(10), use_container_width=True)
    else:
        st.info("Enable **Show raw data table** in the sidebar to see the preview.")

with types_tab:
    dtype_df = pd.DataFrame({
        "Column": df.columns,
        "Data Type": df.dtypes.astype(str).values,
        "Non-Null Count": df.notnull().sum().values,
        "Unique Values": df.nunique().values,
    })
    st.dataframe(dtype_df, use_container_width=True, hide_index=True)


# ══════════════════════════════════════════════
# 2 — DESCRIPTIVE STATISTICS
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">📐 Descriptive Statistics</p>', unsafe_allow_html=True)

if num_cols:
    st.dataframe(df[num_cols].describe().T.style.format("{:.2f}"), use_container_width=True)
else:
    st.warning("No numeric columns found for statistics.")


# ══════════════════════════════════════════════
# 3 — MISSING VALUE ANALYSIS
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">🕳️ Missing Value Analysis</p>', unsafe_allow_html=True)

missing_df = get_missing_info(df)
if missing_df.empty:
    st.success("🎉 No missing values — the dataset is complete!")
else:
    st.warning(f"Found missing values in **{len(missing_df)} column(s)**.")
    m1, m2 = st.columns([1, 1])
    with m1:
        st.dataframe(missing_df, use_container_width=True)
    with m2:
        fig_m, ax_m = plt.subplots(figsize=(6, max(3, len(missing_df) * 0.5)))
        fig_m.patch.set_facecolor("#0e1117")
        ax_m.set_facecolor("#0e1117")
        colors = sns.color_palette("magma", len(missing_df))
        ax_m.barh(missing_df.index.astype(str), missing_df["Missing Values"], color=colors)
        ax_m.set_xlabel("Count", color="#cbd5e1")
        ax_m.set_title("Missing Values by Column", color="#e2e8f0", fontsize=13, fontweight="bold")
        ax_m.tick_params(colors="#94a3b8")
        for spine in ax_m.spines.values():
            spine.set_visible(False)
        st.pyplot(fig_m)
        plt.close(fig_m)


# ══════════════════════════════════════════════
# 4 — AI-STYLE INSIGHTS
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">🤖 Automatic Insights</p>', unsafe_allow_html=True)

for insight in generate_insights(df):
    st.markdown(f'<div class="insight-box">{insight}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════
# 5 — DATA CLEANING
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">🧹 Data Cleaning</p>', unsafe_allow_html=True)

cl1, cl2, cl3, cl4 = st.columns(4)

with cl1:
    if st.button("🗑️ Drop Missing Rows", use_container_width=True):
        before = len(st.session_state.df)
        st.session_state.df = st.session_state.df.dropna()
        after = len(st.session_state.df)
        st.success(f"Removed {before - after} rows.")
        st.rerun()

with cl2:
    if st.button("📊 Fill Missing (Mean)", use_container_width=True):
        nc = st.session_state.df.select_dtypes(include="number").columns
        st.session_state.df[nc] = st.session_state.df[nc].fillna(st.session_state.df[nc].mean())
        st.success("Filled numeric missing values with column means.")
        st.rerun()

with cl3:
    if st.button("♻️ Remove Duplicates", use_container_width=True):
        before = len(st.session_state.df)
        st.session_state.df = st.session_state.df.drop_duplicates()
        after = len(st.session_state.df)
        st.success(f"Removed {before - after} duplicate rows.")
        st.rerun()

with cl4:
    if st.button("🔄 Reset Dataset", use_container_width=True):
        st.session_state.df = raw_df.copy()
        st.success("Dataset reset to original state.")
        st.rerun()


# ══════════════════════════════════════════════
# 6 — DATA VISUALIZATION
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">📊 Data Visualization</p>', unsafe_allow_html=True)

sns.set_palette(chart_palette)

# --- Column selectors ---
viz_col1, viz_col2 = st.columns(2)
with viz_col1:
    sel_num = st.multiselect(
        "Select numeric columns to plot",
        num_cols,
        default=num_cols[:3] if len(num_cols) >= 3 else num_cols,
    )
with viz_col2:
    sel_cat = st.multiselect(
        "Select categorical columns to plot",
        cat_cols,
        default=cat_cols[:2] if len(cat_cols) >= 2 else cat_cols,
    )

chart_type = st.selectbox(
    "Choose chart type",
    ["Histogram", "Bar Chart", "Line Chart", "Pie Chart", "Box Plot"],
)

BG = "#0e1117"
FG = "#e2e8f0"

def styled_fig(rows=1, cols=1, w=10, h=5):
    fig, axes = plt.subplots(rows, cols, figsize=(w, h))
    fig.patch.set_facecolor(BG)
    if isinstance(axes, np.ndarray):
        for a in axes.flat:
            a.set_facecolor(BG)
            a.tick_params(colors="#94a3b8")
            for s in a.spines.values(): s.set_edgecolor("#334155")
    else:
        axes.set_facecolor(BG)
        axes.tick_params(colors="#94a3b8")
        for s in axes.spines.values(): s.set_edgecolor("#334155")
    return fig, axes


# ---- Histogram ----
if chart_type == "Histogram" and sel_num:
    n = len(sel_num)
    fig, axes = styled_fig(1, n, w=5 * n, h=4)
    if n == 1:
        axes = [axes]
    for ax, col in zip(axes, sel_num):
        ax.hist(df[col].dropna(), bins=20, color="#818cf8", edgecolor="#0e1117", alpha=.85)
        ax.set_title(col, color=FG, fontsize=12, fontweight="bold")
        ax.set_xlabel(col, color="#94a3b8")
        ax.set_ylabel("Frequency", color="#94a3b8")
    fig.tight_layout()
    st.pyplot(fig)
    save_chart(fig, "histogram")
    plt.close(fig)

# ---- Bar Chart ----
elif chart_type == "Bar Chart" and sel_cat:
    for col in sel_cat:
        counts = df[col].value_counts().head(10)
        fig, ax = styled_fig(w=8, h=4)
        colors = sns.color_palette(chart_palette, len(counts))
        ax.bar(counts.index.astype(str), counts.values, color=colors, edgecolor="#0e1117")
        ax.set_title(f"Top values — {col}", color=FG, fontsize=13, fontweight="bold")
        ax.set_xlabel(col, color="#94a3b8")
        ax.set_ylabel("Count", color="#94a3b8")
        plt.xticks(rotation=45, ha="right")
        fig.tight_layout()
        st.pyplot(fig)
        save_chart(fig, f"bar_{col}")
        plt.close(fig)

# ---- Line Chart ----
elif chart_type == "Line Chart" and sel_num:
    fig, ax = styled_fig(w=10, h=4)
    for col in sel_num:
        ax.plot(df[col].dropna().values, label=col, linewidth=1.8)
    ax.set_title("Line Chart", color=FG, fontsize=13, fontweight="bold")
    ax.set_xlabel("Index", color="#94a3b8")
    ax.set_ylabel("Value", color="#94a3b8")
    ax.legend(facecolor="#1e293b", edgecolor="#334155", labelcolor="#e2e8f0")
    fig.tight_layout()
    st.pyplot(fig)
    save_chart(fig, "line_chart")
    plt.close(fig)

# ---- Pie Chart ----
elif chart_type == "Pie Chart" and sel_cat:
    for col in sel_cat:
        counts = df[col].value_counts().head(6)
        fig, ax = styled_fig(w=6, h=6)
        colors = sns.color_palette(chart_palette, len(counts))
        wedges, texts, autotexts = ax.pie(
            counts.values, labels=counts.index, autopct="%1.1f%%",
            colors=colors, startangle=140, textprops={"color": FG, "fontsize": 9},
        )
        ax.set_title(f"Distribution — {col}", color=FG, fontsize=13, fontweight="bold")
        fig.tight_layout()
        st.pyplot(fig)
        save_chart(fig, f"pie_{col}")
        plt.close(fig)

# ---- Box Plot ----
elif chart_type == "Box Plot" and sel_num:
    fig, ax = styled_fig(w=10, h=5)
    bp = ax.boxplot(
        [df[c].dropna() for c in sel_num],
        labels=sel_num, patch_artist=True,
    )
    colors = sns.color_palette(chart_palette, len(sel_num))
    for patch, c in zip(bp["boxes"], colors):
        patch.set_facecolor(c)
    ax.set_title("Box Plot", color=FG, fontsize=13, fontweight="bold")
    ax.set_ylabel("Value", color="#94a3b8")
    fig.tight_layout()
    st.pyplot(fig)
    save_chart(fig, "boxplot")
    plt.close(fig)

else:
    st.info("Select appropriate columns above to generate charts.")


# ══════════════════════════════════════════════
# 7 — CORRELATION HEATMAP
# ══════════════════════════════════════════════

if len(num_cols) >= 2:
    st.markdown('<p class="section-header">🔥 Correlation Heatmap</p>', unsafe_allow_html=True)
    corr = df[num_cols].corr()
    fig_h, ax_h = plt.subplots(figsize=(min(12, len(num_cols) * 1.5), min(10, len(num_cols) * 1.2)))
    fig_h.patch.set_facecolor(BG)
    ax_h.set_facecolor(BG)
    sns.heatmap(
        corr, annot=True, fmt=".2f", cmap="coolwarm",
        linewidths=.5, ax=ax_h,
        annot_kws={"color": "#e2e8f0", "fontsize": 9},
        cbar_kws={"shrink": 0.8},
    )
    ax_h.set_title("Feature Correlation Matrix", color=FG, fontsize=14, fontweight="bold")
    ax_h.tick_params(colors="#94a3b8")
    fig_h.tight_layout()
    st.pyplot(fig_h)
    save_chart(fig_h, "correlation_heatmap")
    plt.close(fig_h)


# ══════════════════════════════════════════════
# 8 — EXPORT CLEANED DATA
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">💾 Export Cleaned Data</p>', unsafe_allow_html=True)

exp1, exp2 = st.columns(2)

with exp1:
    csv_buffer = io.StringIO()
    df.to_csv(csv_buffer, index=False)
    st.download_button(
        label="⬇️ Download Cleaned CSV",
        data=csv_buffer.getvalue(),
        file_name="cleaned_data.csv",
        mime="text/csv",
        use_container_width=True,
    )

with exp2:
    if st.button("📁 Save to exports/ folder", use_container_width=True):
        os.makedirs("exports", exist_ok=True)
        out_path = os.path.join("exports", "cleaned_data.csv")
        df.to_csv(out_path, index=False)
        st.success(f"Saved to `{out_path}`")


# ══════════════════════════════════════════════
# 9 — COLUMN EXPLORER (bonus)
# ══════════════════════════════════════════════

st.markdown('<p class="section-header">🔬 Column Explorer</p>', unsafe_allow_html=True)

explore_col = st.selectbox("Pick a column to explore", df.columns)

ec1, ec2 = st.columns(2)
with ec1:
    st.markdown("**Summary**")
    if pd.api.types.is_numeric_dtype(df[explore_col]):
        stats = df[explore_col].describe()
        st.dataframe(stats.to_frame().style.format("{:.2f}"), use_container_width=True)
    else:
        st.write(df[explore_col].describe())

with ec2:
    st.markdown("**Value Distribution**")
    if pd.api.types.is_numeric_dtype(df[explore_col]):
        fig_e, ax_e = styled_fig(w=6, h=3.5)
        ax_e.hist(df[explore_col].dropna(), bins=20, color="#a78bfa", edgecolor="#0e1117")
        ax_e.set_title(explore_col, color=FG, fontsize=12, fontweight="bold")
        fig_e.tight_layout()
        st.pyplot(fig_e)
        plt.close(fig_e)
    else:
        vc = df[explore_col].value_counts().head(8)
        fig_e, ax_e = styled_fig(w=6, h=3.5)
        ax_e.barh(vc.index.astype(str), vc.values, color=sns.color_palette(chart_palette, len(vc)))
        ax_e.set_title(explore_col, color=FG, fontsize=12, fontweight="bold")
        ax_e.invert_yaxis()
        fig_e.tight_layout()
        st.pyplot(fig_e)
        plt.close(fig_e)


# ══════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════

st.markdown("---")
st.markdown(
    "<p style='text-align:center;color:#64748b;font-size:.8rem;'>"
    "AI CSV Insights Tool • Built with Streamlit, Pandas, Matplotlib & Seaborn"
    "</p>",
    unsafe_allow_html=True,
)
