# /// script
# dependencies = [
#     "marimo",
#     "duckdb>=1.0.0",
#     "pandas>=2.0.0",
#     "pyod>=3.6.2",
#     "scikit-learn>=1.0.0",
#     "plotly>=5.0.0",
#     "pillow==12.3.0",
# ]
# requires-python = ">=3.10"
# ///

import marimo

__generated_with = "0.23.15"
app = marimo.App(width="medium")


@app.cell
def _():
    from pathlib import Path

    import duckdb
    import marimo as mo
    from pyod.utils.ad_engine import ADEngine

    def find_bean_screenshot(
        roaster: str, scraped_at, bean_url: str
    ) -> bytes | None:
        import re
        import hashlib
        from urllib.parse import urlparse
        import tarfile

        if not roaster or not bean_url:
            return None

        # 1. Normalize roaster name matching base scraper's dir name
        name = roaster.lower().replace(" ", "_")
        roaster_dir = re.sub(r"[^a-z0-9&_\-éūëöáíóúñûē']", "_", name)

        # 2. Extract and format date (YYYYMMDD)
        session_date = ""
        if hasattr(scraped_at, "strftime"):
            session_date = scraped_at.strftime("%Y%m%d")
        else:
            match = re.search(r"(\d{4})-(\d{2})-(\d{2})", str(scraped_at))
            if match:
                session_date = "".join(match.groups())

        # 3. Compute the archive filename
        parsed = urlparse(bean_url)
        path_parts = [p for p in parsed.path.split("/") if p]
        if path_parts:
            slug = path_parts[-1].replace(".html", "").replace(".php", "")
            slug = re.sub(r"[^a-z0-9_-]", "_", slug.lower())
        else:
            slug = hashlib.md5(bean_url.encode()).hexdigest()[:8]
        cache_filename = f"{slug}.tar.gz"

        # 4. Search under project data/cache directory
        project_root = Path(__file__).parent.parent
        cache_dirs_to_try = [
            project_root
            / "data"
            / "cache"
            / "roasters"
            / roaster_dir
            / session_date,
            Path("data") / "cache" / "roasters" / roaster_dir / session_date,
        ]

        cache_path = None
        for base_dir in cache_dirs_to_try:
            if base_dir.exists():
                p = base_dir / cache_filename
                if p.exists():
                    cache_path = p
                    break

        if not cache_path:
            # Fallback search under any folder of the same roaster
            for parent_dir in [
                project_root / "data" / "cache" / "roasters" / roaster_dir,
                Path("data") / "cache" / "roasters" / roaster_dir,
            ]:
                if parent_dir.exists():
                    for p in parent_dir.glob(f"**/{cache_filename}"):
                        cache_path = p
                        break
                if cache_path:
                    break

        if not cache_path or not cache_path.exists():
            return None

        # 5. Extract screenshot bytes from archive
        try:
            with tarfile.open(cache_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name == "screenshot.png":
                        f = tar.extractfile(member)
                        if f is not None:
                            return f.read()
        except Exception:
            pass

        return None

    return ADEngine, Path, duckdb, find_bean_screenshot, mo


@app.cell
def _(mo):
    mo.md(r"""
    # ☕ Coffee Bean Price Anomaly Detector
    This interactive notebook loads coffee price options from our DuckDB database,
    standardizes the prices to USD to prevent currency scale/bias, and runs
    **PyOD's ADEngine** consensus anomaly detection.
    """)
    return


@app.cell
def _(Path, duckdb):
    db_path = Path(__file__).parent.parent / "data" / "rw_kissaten.duckdb"

    # Fallback to local cwd path if running in a sandbox or separate directory
    if not db_path.exists():
        db_path = Path("data/rw_kissaten.duckdb")

    conn = duckdb.connect(str(db_path), read_only=True)

    query = """
        SELECT
            po.id as option_id,
            po.bean_id as bean_id,
            cb.name as bean_name,
            cb.roaster as roaster,
            po.weight,
            po.price,
            po.currency,
            po.price_per_kg_usd,
            cb.url as bean_url,
            cb.scraped_at as scraped_at,
            coalesce(o.variety_canonical[1], 'Unknown') as varietal_common_name
        FROM price_options po
        JOIN coffee_beans cb ON po.bean_id = cb.id
        LEFT JOIN (
            SELECT DISTINCT ON (bean_id) *
            FROM origins
            ORDER BY bean_id, id
        ) o ON cb.id = o.bean_id
    """
    df_raw = conn.execute(query).df()

    # Prevent currency scale/bias by standardizing prices to USD
    df_raw["price_usd"] = (df_raw["weight"] / 1000.0) * df_raw[
        "price_per_kg_usd"
    ]

    # Compute robust varietal medians with shrinkage fallback (Option A)
    global_median_price_per_kg = df_raw["price_per_kg_usd"].median()

    varietal_counts = df_raw.groupby("varietal_common_name")[
        "price_per_kg_usd"
    ].transform("count")
    varietal_medians = df_raw.groupby("varietal_common_name")[
        "price_per_kg_usd"
    ].transform("median")

    # Apply shrinkage fallback for small groups (less than 5 samples -> global median)
    df_raw["effective_varietal_median"] = varietal_medians.where(
        varietal_counts >= 5, global_median_price_per_kg
    )

    # Calculate relative price features
    df_raw["price_per_kg_usd_relative"] = (
        df_raw["price_per_kg_usd"] / df_raw["effective_varietal_median"]
    )
    df_raw["price_usd_relative"] = (df_raw["weight"] / 1000.0) * df_raw[
        "price_per_kg_usd_relative"
    ]

    # Extract unique roasters for dropdown
    roasters = ["All"] + sorted(df_raw["roaster"].dropna().unique().tolist())
    return df_raw, roasters


@app.cell
def _(mo, roasters):
    # Filter by Roaster dropdown
    roaster_filter = mo.ui.dropdown(
        options=roasters, value="All", label="Filter by Roaster:"
    )

    # Threshold slider for dynamic flagging
    score_threshold = mo.ui.slider(
        start=0.0,
        stop=0.50,
        step=0.01,
        value=0.15,
        label="IForest Score Threshold:",
    )

    mo.vstack(
        [
            mo.md("### ⚙️ Interactive Filtering & Tuning"),
            mo.hstack([roaster_filter, score_threshold], justify="start"),
        ]
    )
    return roaster_filter, score_threshold


@app.cell
def _(ADEngine, df_raw):
    from sklearn.preprocessing import RobustScaler

    X_unscaled = df_raw[
        ["weight", "price_per_kg_usd_relative", "price_usd_relative"]
    ].values  # noqa: N806
    X_features = RobustScaler().fit_transform(X_unscaled)  # noqa: N806

    # Start ADEngine consensus run
    engine = ADEngine()
    state = engine.start(X_features)
    state = engine.plan(state)
    state = engine.run(state)
    state = engine.analyze(state)

    # Identify the best detector via highest Spearman correlation
    best_det_name = state.analysis.get("best_detector", "IForest")

    # We always use the IForest results for the reactive anomaly scores to match the slider's
    # fixed scale [0.0, 0.50] and the slider's "IForest Score Threshold" label, while still
    # displaying the dynamically chosen best consensus detector in the dashboard.
    iforest_res = next(
        r for r in state.results if r["detector_name"] == "IForest"
    )

    # Return metrics & scores to make them reactive
    scores = iforest_res["scores_train"]
    agreement = state.quality.get("agreement", 0.0)
    stability = state.quality.get("stability", 0.0)
    return agreement, best_det_name, scores, stability


@app.cell
def _(df_raw, roaster_filter, score_threshold, scores):
    # Create reactive dataframe copies
    df_processed = df_raw.copy()
    df_processed["anomaly_score"] = scores
    df_processed["is_anomaly"] = (
        df_processed["anomaly_score"] >= score_threshold.value
    ).astype(int)

    # Filter dataframe by selected roaster
    if roaster_filter.value != "All":
        df_display = df_processed[
            df_processed["roaster"] == roaster_filter.value
        ]
    else:
        df_display = df_processed
    return df_display, df_processed


@app.cell
def _(agreement, best_det_name, df_processed, mo, stability):
    total_flagged = df_processed["is_anomaly"].sum()
    pct_flagged = (total_flagged / len(df_processed)) * 100

    metrics_md = mo.md(
        f"""
        ### 📊 Consensus Results
        - **Agreement**: `{agreement:.4f}`
        - **Stability**: `{stability:.4f}`
        - **Selected Detector**: **{best_det_name}**
        - **Total Flagged**: **{total_flagged}** / {len(df_processed)} ({pct_flagged:.1f}%)
        """
    )
    metrics_md
    return


@app.cell
def _(df_display, mo):
    import plotly.express as px

    # Create a copy to avoid mutating the reactive display dataframe
    df_plot = df_display.copy()
    df_plot["Status"] = df_plot["is_anomaly"].map({0: "Normal", 1: "Anomaly"})

    fig = px.scatter(
        df_plot,
        x="weight",
        y="price_per_kg_usd",
        color="Status",
        color_discrete_map={"Normal": "#1f77b4", "Anomaly": "#d62728"},
        custom_data=["option_id"],
        hover_data={
            "option_id": True,
            "bean_name": True,
            "roaster": True,
            "weight": True,
            "price": True,
            "currency": True,
            "price_per_kg_usd": ":.2f",
            "anomaly_score": ":.4f",
        },
        labels={
            "weight": "Package Weight (g)",
            "price_per_kg_usd": "Standardized Price (USD/kg)",
            "Status": "Detection Status",
        },
        title="☕ Price vs. Weight Outliers",
    )

    fig.update_layout(
        plot_bgcolor="rgba(240, 240, 240, 0.5)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=40, b=40),
    )

    plot_widget = mo.ui.plotly(fig)

    mo.vstack(
        [
            mo.md("### 📈 Visualizing Price vs. Weight Outliers"),
            plot_widget,
        ]
    )
    return (plot_widget,)


@app.cell
def _(df_display, mo, plot_widget):
    # Filter display to selected points using option_id if any points are selected in the Plotly widget
    if plot_widget.points:
        selected_option_ids = []
        for pt in plot_widget.points:
            selected_option_ids.append(pt["option_id"])

        if selected_option_ids:
            df_table = df_display[
                df_display["option_id"].isin(selected_option_ids)
            ].sort_values(by="anomaly_score", ascending=False)
            label_text = (
                f"🔍 Selected Points ({len(df_table)} items selected on plot)"
            )
        else:
            df_table = df_display[df_display["is_anomaly"] == 1].sort_values(
                by="anomaly_score", ascending=False
            )
            label_text = "🔍 Flagged Anomalies"
    else:
        df_table = df_display[df_display["is_anomaly"] == 1].sort_values(
            by="anomaly_score", ascending=False
        )
        label_text = "🔍 Flagged Anomalies"

    columns_to_show = [
        "option_id",
        "bean_name",
        "roaster",
        "varietal_common_name",
        "weight",
        "price",
        "currency",
        "price_per_kg_usd",
        "price_usd",
        "anomaly_score",
        "bean_url",
    ]
    table_widget = mo.ui.table(df_table[columns_to_show], label=label_text)

    mo.vstack([mo.md("### 🕵️‍♂️ Investigation Hub"), table_widget])
    return (table_widget,)


@app.cell
def _(df_processed, find_bean_screenshot, mo, table_widget):
    selected_rows = table_widget.value
    detail_view = mo.md(
        "*Select a row in the table above to view detailed diagnostics.*"
    )

    if len(selected_rows) > 0:
        row = selected_rows.iloc[0]
        full_row = df_processed[
            df_processed["option_id"] == row["option_id"]
        ].iloc[0]

        screenshot_bytes = find_bean_screenshot(
            full_row["roaster"], full_row["scraped_at"], full_row["bean_url"]
        )

        if screenshot_bytes:
            import base64
            from io import BytesIO
            from PIL import Image

            try:
                # Open the image from bytes
                img = Image.open(BytesIO(screenshot_bytes))

                # Convert RGBA or Palette mode to RGB for standard JPEG compression
                if img.mode in ("RGBA", "P"):
                    img = img.convert("RGB")

                # Resize to a max width of 1600px to drastically reduce memory/data footprint
                max_width = 1600
                if img.width > max_width:
                    ratio = max_width / float(img.width)
                    new_height = int(float(img.height) * ratio)
                    img = img.resize(
                        (max_width, new_height), Image.Resampling.LANCZOS
                    )

                # Compress as optimized JPEG
                compressed_io = BytesIO()
                img.save(
                    compressed_io, format="JPEG", quality=90, optimize=True
                )
                compressed_bytes = compressed_io.getvalue()

                b64_data = base64.b64encode(compressed_bytes).decode("utf-8")
                img_src = f"data:image/jpeg;base64,{b64_data}"
                screenshot_view = mo.vstack(
                    [
                        mo.md(
                            "##### 📸 Scraped Page Screenshot (Optimised & Compressed)"
                        ),
                        mo.image(
                            src=img_src,
                            alt="Screenshot of the bean page",
                            style={
                                "max-width": "100%",
                                "border": "1px solid #ccc",
                            },
                        ),
                    ]
                )
            except Exception as e:
                # Fallback to standard PNG encoding if PIL fails
                b64_data = base64.b64encode(screenshot_bytes).decode("utf-8")
                img_src = f"data:image/png;base64,{b64_data}"
                screenshot_view = mo.vstack(
                    [
                        mo.md(
                            f"##### 📸 Scraped Page Screenshot (Fallback due to error: {e})"
                        ),
                        mo.image(
                            src=img_src,
                            alt="Screenshot of the bean page",
                            style={
                                "max-width": "100%",
                                "border": "1px solid #ccc",
                            },
                        ),
                    ]
                )
        else:
            screenshot_view = mo.md(
                "*No screenshot cache found for this bean.*"
            )

        # Fetch all options matching this bean_id
        same_bean_options = df_processed[
            df_processed["bean_id"] == full_row["bean_id"]
        ].sort_values("weight")

        options_rows = []
        for _, opt in same_bean_options.iterrows():
            is_current = (
                " 👉 **(Selected)**"
                if opt["option_id"] == row["option_id"]
                else ""
            )
            status = "🚨 **Anomaly**" if opt["is_anomaly"] else "✅ Normal"
            options_rows.append(
                f"| {opt['weight']}g | {opt['price']:.2f} {opt['currency']} | ${opt['price_usd']:.2f} | ${opt['price_per_kg_usd']:.2f} | {opt['anomaly_score']:.4f} | {status}{is_current} |"
            )

        options_table_md = "\n".join(
            [
                "##### 📦 All Price Options for this Bean",
                "| Weight | Price | Package Price (USD) | Price per kg (USD) | Anomaly Score | Status |",
                "|---|---|---|---|---|---|",
                *options_rows,
            ]
        )

        detail_view = mo.vstack(
            [
                mo.md(
                    f"""
                #### 💡 Diagnostic Report: Option #{row["option_id"]}
                - **Bean**: {row["bean_name"]}
                - **Roaster**: {row["roaster"]}
                - **Varietal**: {row["varietal_common_name"]}
                - **Product URL**: [{row["bean_url"]}]({row["bean_url"]})
                - **Weight / Price**: {row["weight"]}g for {row["price"]} {row["currency"]}
                - **Calculated Price per kg (USD)**: `${row["price_per_kg_usd"]:.2f}`
                - **Calculated Package Price (USD)**: `${row["price_usd"]:.2f}`
                - **Consensus Anomaly Score**: `{row["anomaly_score"]:.4f}`
                """
                ),
                mo.md("<br>"),
                mo.md(options_table_md),
                mo.md("<br>"),
                screenshot_view,
            ]
        )

    # Generate CSV of all flagged anomalies across the whole dataset for download
    df_anoms_all = df_processed[df_processed["is_anomaly"] == 1]
    csv_data = df_anoms_all.to_csv(index=False).encode("utf-8")
    download_btn = mo.download(
        data=csv_data,
        filename="price_options_anomalies.csv",
        label="📥 Download CSV of all Flagged Anomalies",
    )

    mo.vstack([detail_view, mo.md("<br>"), download_btn])
    return (selected_rows,)


@app.cell
def _(mo, selected_rows):
    mo.ui.table(selected_rows)
    return


if __name__ == "__main__":
    app.run()
