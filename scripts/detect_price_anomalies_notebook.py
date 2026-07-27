# /// script
# dependencies = [
#     "marimo",
#     "duckdb==1.5.5",
#     "pandas==3.0.5",
#     "pyod==3.6.2",
#     "scikit-learn==1.9.0",
#     "plotly==6.9.0",
#     "pillow==12.3.0",
#     "numpy==2.4.6",
# ]
# requires-python = ">=3.10"
# ///

import marimo

__generated_with = "0.23.15"
app = marimo.App(width="full")


@app.cell(hide_code=True)
def _():
    from pathlib import Path

    import duckdb
    import json
    import marimo as mo
    import os
    import numpy as np
    import pandas as pd
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

    import plotly.express as px

    return (
        ADEngine,
        Path,
        duckdb,
        find_bean_screenshot,
        json,
        mo,
        np,
        os,
        pd,
        px,
    )


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # ☕ Coffee Bean Price Outlier Detector

    This interactive notebook serves as our command center for detecting anomalous coffee pricing (such as scraping bugs, currency parsing issues, weight mislabeling, or genuinely rare premium lots).

    ---

    ### 🎯 Purpose
    By parsing, normalizing, and auditing our global coffee bean database, this system flags pricing inconsistencies before they reach production. It combines machine learning with human-in-the-loop annotations to create a highly accurate, robust price auditor.

    ---

    ### ⚙️ How Outlier Detection Works

    Our pipeline processes price data in three primary stages:

    1. **Robust Context Standardization**
       * **Base Standardization**: Converts all package prices to USD to eliminate currency scale and bias.
       * **Contextual Features**: Standard pricing models suffer from package-size bias. Instead, we calculate price-per-kg deviations relative to three robust context baselines:
         * *Varietal Context* (e.g., standardizing Bourbon vs. expensive Geshas)
         * *Origin Context* (e.g., adjusting for typical regional differences)
         * *Roaster Context* (e.g., normalizing high-end vs. budget roasters)
       * **Symmetric Log-Transformation**: Relative pricing is log-transformed, treating overpriced and underpriced beans symmetrically on a robustly scaled space.

    2. **Multi-Detector Ensemble (`PyOD` & `ADEngine`)**
       * We run a suite of state-of-the-art anomaly detection models via PyOD's `ADEngine` to evaluate the scaled features.
       * Raw scores from individual detectors are scaled to `[0, 1]` for fair comparison and aggregation.

    3. **Active Human-in-the-Loop Alignment**
       * **Initial State**: If no feedback is provided, the models are combined using equal consensus weights.
       * **Adaptive Learning**: As you annotate outliers in the *Investigation Hub* below, the ensemble evaluates the performance (ROC-AUC) of each detector against your ground-truth labels.
       * **Optimized Ensemble**: The system automatically redistributes voting weights toward the best-performing models on your labeled dataset, producing a highly stable, personalized consensus anomaly score.
    """)
    return


@app.cell(hide_code=True)
def _(Path, duckdb):
    db_path = Path(__file__).parent.parent / "data" / "rw_kissaten.duckdb"

    # Fallback to local cwd path if running in a sandbox or separate directory
    if not db_path.exists():
        db_path = Path("data/rw_kissaten.duckdb")

    conn = duckdb.connect(str(db_path), read_only=True)
    return (conn,)


@app.cell(hide_code=True)
def _(conn, mo):
    df_raw = mo.sql(
        f"""
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
            cb.date_added as date_added,
            o.variety_canonical as variety_canonical_array,
            coalesce(o.country, 'Unknown') as origin_country
        FROM price_options po
        JOIN coffee_beans cb ON po.bean_id = cb.id
        LEFT JOIN (
            SELECT DISTINCT ON (bean_id) *
            FROM origins
            ORDER BY bean_id, id
        ) o ON cb.id = o.bean_id
        """,
        engine=conn,
    )
    return (df_raw,)


@app.cell(hide_code=True)
def _(df_raw, np):
    # Prevent currency scale/bias by standardizing prices to USD
    df_raw["price_usd"] = (df_raw["weight"] / 1000.0) * df_raw[
        "price_per_kg_usd"
    ]

    # Normalize varietal blends: sort and join variety_canonical array
    # e.g., ['Bourbon', 'Caturra'] -> 'Bourbon + Caturra'
    def clean_varietal_blend(variety_array):
        if (
            not isinstance(variety_array, (list, np.ndarray))
            or len(variety_array) == 0
        ):
            return "Unknown"
        cleaned = sorted([v.strip() for v in variety_array if v and v.strip()])
        return " + ".join(cleaned) if cleaned else "Unknown"

    df_raw["varietal_common_name"] = df_raw["variety_canonical_array"].apply(
        clean_varietal_blend
    )

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

    # Compute robust origin medians with shrinkage fallback
    origin_counts = df_raw.groupby("origin_country")[
        "price_per_kg_usd"
    ].transform("count")
    origin_medians = df_raw.groupby("origin_country")[
        "price_per_kg_usd"
    ].transform("median")
    df_raw["effective_origin_median"] = origin_medians.where(
        origin_counts >= 5, global_median_price_per_kg
    )
    df_raw["price_per_kg_usd_relative_origin"] = (
        df_raw["price_per_kg_usd"] / df_raw["effective_origin_median"]
    )

    # Compute robust roaster medians with shrinkage fallback
    roaster_counts = df_raw.groupby("roaster")["price_per_kg_usd"].transform(
        "count"
    )
    roaster_medians = df_raw.groupby("roaster")["price_per_kg_usd"].transform(
        "median"
    )
    df_raw["effective_roaster_median"] = roaster_medians.where(
        roaster_counts >= 5, global_median_price_per_kg
    )
    df_raw["price_per_kg_usd_relative_roaster"] = (
        df_raw["price_per_kg_usd"] / df_raw["effective_roaster_median"]
    )

    # 3. Log-transform relative features to ensure symmetry between overpriced and underpriced beans
    epsilon = 1e-4
    df_raw["price_per_kg_usd_relative_log"] = np.log(
        df_raw["price_per_kg_usd_relative"] + epsilon
    )
    df_raw["price_per_kg_usd_relative_origin_log"] = np.log(
        df_raw["price_per_kg_usd_relative_origin"] + epsilon
    )
    df_raw["price_per_kg_usd_relative_roaster_log"] = np.log(
        df_raw["price_per_kg_usd_relative_roaster"] + epsilon
    )

    # Extract unique roasters for dropdown
    roasters = ["All"] + sorted(df_raw["roaster"].dropna().unique().tolist())
    return (roasters,)


@app.cell(hide_code=True)
def _(Path, mo, roasters):
    # Filter by Roaster dropdown
    roaster_filter = mo.ui.dropdown(
        options=roasters, value="All", label="Filter by Roaster:"
    )

    # Threshold slider for dynamic flagging
    score_threshold = mo.ui.slider(
        start=0.0,
        stop=1.00,
        step=0.01,
        value=0.80,
        label="Anomaly Score Threshold:",
    )

    # Checkbox to filter out already labeled beans/options
    filter_labeled = mo.ui.checkbox(
        value=False,
        label="Hide Already Labeled Options",
    )

    # Checkbox to only show outliers in investigation hub table
    filter_outliers_only = mo.ui.checkbox(
        value=True,
        label="Show Outliers Only in Table",
    )

    # Checkbox to dampen rare/premium mini-lots
    damp_premium = mo.ui.checkbox(
        value=False,
        label="Dampen Rare/Premium Mini-Lots (<=125g)",
    )

    # Path for JSON label storage - resolve relative to project root
    LABELS_FILE_PATH = str(
        Path(__file__).parent.parent / "data" / "outlier_labels.json"
    )

    mo.vstack(
        [
            mo.md("### ⚙️ Interactive Filtering & Tuning"),
            mo.hstack([roaster_filter], justify="start"),
        ]
    )
    return (
        LABELS_FILE_PATH,
        damp_premium,
        filter_labeled,
        filter_outliers_only,
        roaster_filter,
        score_threshold,
    )


@app.cell
def _():
    return


@app.cell(hide_code=True)
def _(ADEngine, LABELS_FILE_PATH, df_raw, get_trigger, json, np, os):
    from sklearn.preprocessing import RobustScaler, MinMaxScaler
    from sklearn.metrics import roc_auc_score

    # Register get_trigger reactive dependency to re-run models upon annotation saves
    _ = get_trigger()

    # 1. Scale input features
    # To prevent absolute package size/weight scale bias from dominating the model
    # (especially since IQR of weight is near 0 and RobustScaler can explode large weights),
    # we assess price anomalies relative to multiple robust context baselines:
    # 1) relative to varietal, 2) relative to origin, and 3) relative to roaster.
    # We use log-transformed relative features to treat underpricing and overpricing symmetrically.
    X_unscaled = df_raw[
        [
            "price_per_kg_usd_relative_log",
            "price_per_kg_usd_relative_origin_log",
            "price_per_kg_usd_relative_roaster_log",
        ]
    ].values  # noqa: N806
    X_features = RobustScaler().fit_transform(X_unscaled)  # noqa: N806

    # 2. Run ADEngine session to fetch individual detector scores
    engine = ADEngine()
    state = engine.start(X_features)
    state = engine.plan(state)
    state = engine.run(state)
    state = engine.analyze(state)

    # Identify the best detector via highest Spearman correlation (for display)
    best_det_name = state.analysis.get("best_detector", "IForest")

    # 3. Extract individual detector outputs and normalize to [0, 1]
    detector_scores = {}
    for res in state.results:
        name = res["detector_name"]
        raw_scores = np.array(res["scores_train"])
        # Standardize detector scores to [0, 1] scale for fair consensus combination
        detector_scores[name] = (
            MinMaxScaler().fit_transform(raw_scores.reshape(-1, 1)).ravel()
        )

    # 4. Load active human labels from JSON
    has_labels = False
    weights = {
        name: 1.0 / len(detector_scores) for name in detector_scores.keys()
    }
    y_true_dict = {}

    if os.path.exists(LABELS_FILE_PATH):
        try:
            with open(LABELS_FILE_PATH, "r") as _f:
                _labels_db = json.load(_f)

            # Build map of stable keys and legacy option_ids to binary ground truth values.
            # 1 for anomaly, 0 for normal/incorrect_outlier/expected.
            stable_labels_map = {}
            for key, labeled_info in _labels_db.items():
                label_str = labeled_info.get("label", "").lower()
                val = 1 if label_str in ("correct_outlier", "outlier") else 0
                if "#" in key:
                    stable_labels_map[key] = val
                else:
                    y_true_dict[key] = val
                    try:
                        y_true_dict[int(key)] = val
                    except ValueError:
                        pass

            # Dynamically map stable labels to transient option_ids in the active dataset
            for _, _row in df_raw.iterrows():
                _row_url = _row.get("bean_url", "")
                _row_weight = int(_row.get("weight", 0))
                _row_opt_id = _row["option_id"]
                _stable_key = f"{_row_url}#{_row_weight}"
                if _stable_key in stable_labels_map:
                    y_true_dict[_row_opt_id] = stable_labels_map[_stable_key]
                    y_true_dict[str(_row_opt_id)] = stable_labels_map[
                        _stable_key
                    ]

            # Intersect with raw df
            df_labeled_subset = df_raw[
                df_raw["option_id"].isin(y_true_dict.keys())
            ].copy()
            df_labeled_subset["y_true"] = df_labeled_subset["option_id"].map(
                y_true_dict
            )

            y_labeled = df_labeled_subset["y_true"].values

            # We need at least one positive and one negative sample to calculate ROC-AUC
            if len(y_labeled) > 0 and len(np.unique(y_labeled)) > 1:
                has_labels = True
                raw_weights = {}
                auc_scores = {}

                # Get index of labeled rows in the original dataframe
                labeled_indices = (
                    df_raw["option_id"]
                    .isin(df_labeled_subset["option_id"])
                    .values
                )

                for name, scores in detector_scores.items():
                    labeled_scores = scores[labeled_indices]
                    try:
                        auc = roc_auc_score(y_labeled, labeled_scores)
                        auc_scores[name] = auc
                        # Weight proportional to ROC-AUC above random guessing (0.5)
                        raw_weights[name] = max(0.0, auc - 0.5)
                    except Exception:
                        auc_scores[name] = 0.5
                        raw_weights[name] = 0.0

                total_w = sum(raw_weights.values())
                if total_w > 0:
                    weights = {k: v / total_w for k, v in raw_weights.items()}
                else:
                    # Fallback if no detector outperforms random guessing
                    weights = {
                        name: 1.0 / len(detector_scores)
                        for name in detector_scores.keys()
                    }

                # Find the detector with the highest ROC-AUC score
                if auc_scores:
                    best_det_name = max(auc_scores, key=auc_scores.get)
        except Exception:
            pass

    # 5. Compute final optimized consensus anomaly scores
    final_scores = np.zeros(len(df_raw))
    for name, scores in detector_scores.items():
        final_scores += weights[name] * scores

    # 6. Return metrics & scores to make them reactive
    # We use the normalized scores of the selected best detector (highest scoring or unsupervised best)
    # which scale from [0, 1] to match our universal threshold slider.
    selected_scores = detector_scores[best_det_name]

    agreement = state.quality.get("agreement", 0.0)
    stability = state.quality.get("stability", 0.0)
    return (
        agreement,
        best_det_name,
        final_scores,
        has_labels,
        stability,
        weights,
        y_true_dict,
    )


@app.cell(hide_code=True)
def _(damp_premium, df_raw, final_scores, roaster_filter, score_threshold):
    # Create reactive dataframe copies
    df_processed = df_raw.copy()
    df_processed["anomaly_score"] = final_scores

    # Dampen rare/premium mini-lots if enabled
    if damp_premium.value:

        def adjust_score(row):
            score = row["anomaly_score"]
            name_lower = row["bean_name"].lower()
            has_premium_kw = any(
                kw in name_lower
                for kw in [
                    "mokka",
                    "mokkita",
                    "eugenoides",
                    "laurina",
                    "geisha",
                    "gesha",
                    "pacamara",
                    "sl34",
                    "chiroso",
                    "comp",
                    "edition",
                    "competition",
                ]
            )
            if row["weight"] <= 125 and has_premium_kw:
                return score * 0.75
            return score

        df_processed["anomaly_score"] = df_processed.apply(
            adjust_score, axis=1
        )

    df_processed["aligned_score"] = df_processed["anomaly_score"]
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


@app.cell(hide_code=True)
def _(
    agreement,
    best_det_name,
    df_processed,
    has_labels,
    mo,
    np,
    pd,
    px,
    score_threshold,
    stability,
    weights,
    y_true_dict,
):
    total_flagged = df_processed["is_anomaly"].sum()
    pct_flagged = (total_flagged / len(df_processed)) * 100

    if has_labels:
        weights_list = "\n".join(
            [f"- **{name}**: `{w * 100:.1f}%`" for name, w in weights.items()]
        )
        alignment_md = mo.md(f"""
    ### 🎯 Ensemble Alignment (Active)
    Detector weights optimized from your feedback:
    {weights_list}
        """)
    else:
        alignment_md = mo.md("""
    ### 🔄 Ensemble Alignment (Unsupervised)
    Equal consensus weights. Annotate outliers below to optimize.
        """)

    precision_recall_md = ""
    curve_widget = None

    if len(y_true_dict) > 0:
        y_true = []
        y_pred = []
        for _, eval_row in df_processed.iterrows():
            eval_opt_id = str(eval_row["option_id"])
            if eval_opt_id in y_true_dict:
                y_true.append(y_true_dict[eval_opt_id])
                y_pred.append(eval_row["is_anomaly"])

        if len(y_true) > 0:
            tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
            fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
            fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
            tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)

            precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
            f1_score = (
                2 * (precision * recall) / (precision + recall)
                if (precision + recall) > 0
                else 0.0
            )

            precision_recall_md = mo.md(f"""
    ### 🎯 Validation Metrics (From Labeled Feedback)
    - **Precision**: `{precision * 100:.1f}%` ({tp} / {tp + fp} correct flags)
    - **Recall**: `{recall * 100:.1f}%` (captured {tp} / {tp + fn} known outliers)
    - **F1-Score**: `{f1_score * 100:.1f}%` (overall harmonic balance)

    *Annotated dataset summary*: Total: **{len(y_true)}** (True Positives: **{tp}**, False Positives: **{fp}**, False Negatives: **{fn}**, True Negatives: **{tn}**)
            """)

        # Generate Precision-Recall-F1 vs. Threshold curves from labeled data
        labeled_mask = df_processed["option_id"].isin(y_true_dict.keys())
        df_labeled = df_processed[labeled_mask].copy()

        if len(df_labeled) > 0:
            df_labeled["y_true"] = df_labeled["option_id"].map(y_true_dict)

            thresholds = np.linspace(0.0, 1.0, 101)
            curve_rows = []

            y_true_arr = df_labeled["y_true"].values
            scores_arr = df_labeled["anomaly_score"].values

            for t in thresholds:
                y_pred_arr = (scores_arr >= t).astype(int)

                tp_c = sum((y_true_arr == 1) & (y_pred_arr == 1))
                fp_c = sum((y_true_arr == 0) & (y_pred_arr == 1))
                fn_c = sum((y_true_arr == 1) & (y_pred_arr == 0))

                p_c = tp_c / (tp_c + fp_c) if (tp_c + fp_c) > 0 else 1.0
                r_c = tp_c / (tp_c + fn_c) if (tp_c + fn_c) > 0 else 0.0
                f1_c = (
                    2 * (p_c * r_c) / (p_c + r_c) if (p_c + r_c) > 0 else 0.0
                )

                curve_rows.append(
                    {
                        "Threshold": t,
                        "Precision": p_c,
                        "Recall": r_c,
                        "F1-Score": f1_c,
                    }
                )

            df_curves = pd.DataFrame(curve_rows)
            df_melted = df_curves.melt(
                id_vars=["Threshold"],
                value_vars=["Precision", "Recall", "F1-Score"],
                var_name="Metric",
                value_name="Value",
            )

            fig_curve = px.line(
                df_melted,
                x="Threshold",
                y="Value",
                color="Metric",
                color_discrete_map={
                    "Precision": "#1f77b4",
                    "Recall": "#2ca02c",
                    "F1-Score": "#9467bd",
                },
                line_dash_map={
                    "Precision": "-",
                    "Recall": "-",
                    "F1-Score": "dash",
                },
                labels={
                    "Threshold": "Anomaly Score Threshold",
                    "Value": "Score",
                },
            )

            fig_curve.add_vline(
                x=score_threshold.value,
                line_width=2,
                line_dash="dash",
                line_color="#d62728",
                annotation_text=f"Current: {score_threshold.value:.2f}",
                annotation_position="top right",
            )

            fig_curve.update_layout(
                plot_bgcolor="rgba(240, 240, 240, 0.5)",
                paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=40, r=40, t=40, b=40),
                height=320,
                yaxis=dict(range=[-0.05, 1.05]),
            )

            curve_widget = mo.ui.plotly(fig_curve)

    consensus_metrics_md = mo.md(
        f"""
    ### 📊 Consensus Results

    - **Agreement**: `{agreement:.4f}`
    - **Stability**: `{stability:.4f}`
    - **Selected Detector**: **{best_det_name}**
    - **Total Flagged**: **{total_flagged}** / {len(df_processed)} ({pct_flagged:.1f}%)"""
    )

    metrics_md = mo.vstack(
        [consensus_metrics_md, precision_recall_md, alignment_md]
    )

    # Render metrics side-by-side with the curves if we have labels
    if curve_widget is not None:
        layout = mo.vstack(
            [
                metrics_md,
                mo.hstack(
                    [
                        mo.md("### 🎯 Tradeoff Curves vs. Threshold"),
                        score_threshold,
                    ],
                    justify="space-between",
                ),
                curve_widget,
            ]
        )
    else:
        layout = metrics_md

    layout
    return


@app.cell(hide_code=True)
def _(df_display, mo, px):
    # Create a copy to avoid mutating the reactive display dataframe
    df_plot = df_display.copy()
    df_plot["Status"] = df_plot["is_anomaly"].map(
        {0: "Expected", 1: "Outlier"}
    )

    fig = px.scatter(
        df_plot,
        x="weight",
        y="price_per_kg_usd",
        color="Status",
        color_discrete_map={"Expected": "#1f77b4", "Outlier": "#d62728"},
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


@app.cell(hide_code=True)
def _(df_display, mo, plot_widget, px):
    df_hist_plot = df_display.copy()

    hist_selected_option_ids = (
        [pt["option_id"] for pt in plot_widget.points]
        if plot_widget.points
        else []
    )

    if hist_selected_option_ids:
        # Filter to normal points and selected anomalies
        is_normal = df_hist_plot["is_anomaly"] == 0
        is_selected_anomaly = df_hist_plot["option_id"].isin(
            hist_selected_option_ids
        ) & (df_hist_plot["is_anomaly"] == 1)
        df_hist_plot = df_hist_plot[is_normal | is_selected_anomaly].copy()

        df_hist_plot["Status"] = df_hist_plot["option_id"].apply(
            lambda oid: (
                "Selected Outlier"
                if oid in hist_selected_option_ids
                else "Expected"
            )
        )
        color_discrete_map = {
            "Expected": "#1f77b4",
            "Selected Outlier": "#d62728",
        }
    else:
        df_hist_plot["Status"] = df_hist_plot["is_anomaly"].map(
            {0: "Expected", 1: "Outlier"}
        )
        color_discrete_map = {"Expected": "#1f77b4", "Outlier": "#d62728"}

    fig_hist = px.histogram(
        df_hist_plot,
        x="price_per_kg_usd",
        color="Status",
        color_discrete_map=color_discrete_map,
        nbins=500,
        barmode="overlay",
        histnorm="probability density",
        hover_data={
            "bean_name": True,
            "roaster": True,
            "price_per_kg_usd": ":.2f",
        },
        labels={
            "price_per_kg_usd": "Price (USD/kg)",
            "Status": "Detection Status",
        },
        title="📊 Price per kg Distribution",
    )

    fig_hist.update_layout(
        plot_bgcolor="rgba(240, 240, 240, 0.5)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=40, b=40),
    )

    hist_widget = mo.ui.plotly(fig_hist)

    mo.vstack(
        [
            mo.md("### 📊 Distribution of Price per kg"),
            hist_widget,
        ]
    )
    return df_hist_plot, hist_widget


@app.cell(hide_code=True)
def _(
    damp_premium,
    df_display,
    df_hist_plot,
    filter_labeled,
    filter_outliers_only,
    hist_widget,
    mo,
    np,
    plot_widget,
    y_true_dict,
):
    # Filter out already labeled options if filter is enabled
    df_table_filtered = df_display
    if filter_labeled.value:
        # y_true_dict contains labeled option_ids (both integer and string forms)
        # We can exclude any rows whose option_id is in y_true_dict keys
        df_table_filtered = df_table_filtered[
            ~df_table_filtered["option_id"].isin(y_true_dict.keys())
        ]

    # Apply outliers filter if option is enabled
    if filter_outliers_only.value:
        df_table_filtered = df_table_filtered[
            df_table_filtered["is_anomaly"] == 1
        ]

    # Filter display to selected points using option_id if any points are selected in the Plotly widgets
    selected_scatter_ids = (
        [pt["option_id"] for pt in plot_widget.points if "option_id" in pt]
        if plot_widget.points
        else []
    )

    selected_hist_ids = []
    if hist_widget.points:
        # Extract the price_per_kg_usd values from the points (key "x" in Plotly selection events)
        x_values = [pt["x"] for pt in hist_widget.points if "x" in pt]
        if x_values:
            prices = df_hist_plot["price_per_kg_usd"].values
            mask = np.zeros(len(df_hist_plot), dtype=bool)
            for x_val in x_values:
                # Use a precision tolerance of 1e-4 to find matching rows
                mask |= np.abs(prices - x_val) < 1e-4
            selected_hist_ids = df_hist_plot[mask]["option_id"].tolist()

    if selected_scatter_ids and selected_hist_ids:
        common_ids = list(
            set(selected_scatter_ids).intersection(set(selected_hist_ids))
        )
        df_table = df_table_filtered[
            df_table_filtered["option_id"].isin(common_ids)
        ]
        label_text = f"🔍 Combined Selection ({len(df_table)} items match both scatter & histogram selection)"
    elif selected_scatter_ids:
        df_table = df_table_filtered[
            df_table_filtered["option_id"].isin(selected_scatter_ids)
        ]
        label_text = f"🔍 Scatter Selection ({len(df_table)} items selected on scatter plot)"
    elif selected_hist_ids:
        df_table = df_table_filtered[
            df_table_filtered["option_id"].isin(selected_hist_ids)
        ]
        label_text = f"🔍 Histogram Selection ({len(df_table)} items selected on histogram)"
    else:
        df_table = df_table_filtered[df_table_filtered["is_anomaly"] == 1]
        label_text = "🔍 Flagged Outliers"

    df_table = df_table.sort_values(by="anomaly_score", ascending=False)

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
    table_widget = mo.ui.table(
        df_table[columns_to_show], label=label_text, selection="multi"
    )

    mo.vstack(
        [
            mo.md("### 🕵️‍♂️ Investigation Hub"),
            mo.hstack(
                [filter_labeled, filter_outliers_only, damp_premium], gap=2
            ),
            table_widget,
        ]
    )
    return (table_widget,)


@app.cell(hide_code=True)
def _(mo):
    # Reactive dictionary states to store drafts and feedbacks per option_id
    get_drafts, set_drafts = mo.state({})
    get_feedbacks, set_feedbacks = mo.state({})
    get_trigger, set_trigger = mo.state(0)
    get_status, set_status = mo.state("")
    return get_status, get_trigger, set_status, set_trigger


@app.cell(hide_code=True)
def _(
    LABELS_FILE_PATH,
    df_processed,
    get_status,
    json,
    mo,
    os,
    set_status,
    set_trigger,
    table_widget,
):
    _selected_rows = table_widget.value
    feedback_ui = mo.md("*Select rows above to annotate them in batch.*")

    notes_input = None
    label_radio = None
    save_btn = None
    remove_btn = None

    def save_annotation(_):
        if not label_radio or not label_radio.value:
            set_status("⚠️ Please select either Outlier or Expected first.")
            return

        _selected_rows_inner = table_widget.value
        if len(_selected_rows_inner) > 0:
            import datetime

            _labels_db = {}
            if os.path.exists(LABELS_FILE_PATH):
                try:
                    with open(LABELS_FILE_PATH, "r") as _f:
                        _labels_db = json.load(_f)
                except Exception:
                    pass

            for _, _row_inner in _selected_rows_inner.iterrows():
                _option_id = str(_row_inner["option_id"])
                _full_row = df_processed[
                    df_processed["option_id"] == _row_inner["option_id"]
                ].iloc[0]

                _url = _full_row.get("bean_url", "")
                _weight = int(_full_row.get("weight", 0))
                _stable_key = f"{_url}#{_weight}" if _url else _option_id

                _labels_db[_stable_key] = {
                    "bean_id": str(_full_row["bean_id"]),
                    "bean_name": _full_row["bean_name"],
                    "bean_url": _url,
                    "roaster": _full_row["roaster"],
                    "varietal": _full_row["varietal_common_name"],
                    "origin": _full_row["origin_country"],
                    "price_per_kg_usd": float(_full_row["price_per_kg_usd"]),
                    "weight": _weight,
                    "anomaly_score": float(_full_row["anomaly_score"]),
                    "label": label_radio.value,
                    "notes": notes_input.value if notes_input else "",
                    "annotated_at": datetime.datetime.now().isoformat(),
                }

                # Clean up duplicate legacy option_id entry if saving over it
                if _option_id in _labels_db and _stable_key != _option_id:
                    del _labels_db[_option_id]

            os.makedirs(os.path.dirname(LABELS_FILE_PATH), exist_ok=True)
            with open(LABELS_FILE_PATH, "w") as _f:
                json.dump(_labels_db, _f, indent=2)

            if len(_selected_rows_inner) == 1:
                _single_id = str(_selected_rows_inner.iloc[0]["option_id"])
                set_status(
                    f"🎉 Annotation for Option #{_single_id} saved successfully!"
                )
            else:
                set_status(
                    f"🎉 Annotations for {len(_selected_rows_inner)} options saved successfully!"
                )
            set_trigger(lambda t: t + 1)

    def remove_annotation(_):
        _selected_rows_inner = table_widget.value
        if len(_selected_rows_inner) > 0:
            _labels_db = {}
            if os.path.exists(LABELS_FILE_PATH):
                try:
                    with open(LABELS_FILE_PATH, "r") as _f:
                        _labels_db = json.load(_f)
                except Exception:
                    pass

            removed_count = 0
            for _, _row_inner in _selected_rows_inner.iterrows():
                _option_id = str(_row_inner["option_id"])
                _url = _row_inner.get("bean_url", "")
                _weight = int(_row_inner.get("weight", 0))
                _stable_key = f"{_url}#{_weight}"

                if _stable_key in _labels_db:
                    del _labels_db[_stable_key]
                    removed_count += 1
                if _option_id in _labels_db:
                    del _labels_db[_option_id]
                    removed_count += 1

            if removed_count > 0:
                with open(LABELS_FILE_PATH, "w") as _f:
                    json.dump(_labels_db, _f, indent=2)

            if removed_count == 1:
                set_status("🗑️ Label removed!")
            elif removed_count > 1:
                set_status(f"🗑️ {removed_count} labels removed!")
            else:
                set_status(
                    "ℹ️ No active labels to remove for selected options."
                )
            set_trigger(lambda t: t + 1)

    if len(_selected_rows) > 0:
        # If we have multiple selections, find if there's a consensus on existing label and notes
        _existing_label = None
        _existing_notes = None

        _labels_db = {}
        if os.path.exists(LABELS_FILE_PATH):
            try:
                with open(LABELS_FILE_PATH, "r") as _f:
                    _labels_db = json.load(_f)
            except Exception:
                pass

        _labels_set = set()
        _notes_set = set()

        for _, _row_inner in _selected_rows.iterrows():
            _option_id = str(_row_inner["option_id"])
            _url = _row_inner.get("bean_url", "")
            _weight = int(_row_inner.get("weight", 0))
            _stable_key = f"{_url}#{_weight}"

            # Look up by stable key first, fallback to transient option_id
            matched_info = None
            if _stable_key in _labels_db:
                matched_info = _labels_db[_stable_key]
            elif _option_id in _labels_db:
                matched_info = _labels_db[_option_id]

            if matched_info:
                raw_label = matched_info.get("label", "").lower()
                if raw_label in ("correct_outlier", "outlier"):
                    _labels_set.add("outlier")
                elif raw_label in ("incorrect_outlier", "normal", "expected"):
                    _labels_set.add("expected")
                else:
                    _labels_set.add("")
                _notes_set.add(matched_info.get("notes", ""))
            else:
                _labels_set.add("")
                _notes_set.add("")

        if len(_labels_set) == 1:
            _lbl = list(_labels_set)[0]
            _existing_label = _lbl if _lbl else None

        if len(_notes_set) == 1:
            _existing_notes = list(_notes_set)[0]

        label_radio = mo.ui.radio(
            options={"outlier": "Outlier", "expected": "Expected"},
            value=_existing_label,
            label="Label:",
        )

        notes_input = mo.ui.text(
            value=_existing_notes if _existing_notes else "",
            placeholder="Why is this outlier correct/incorrect?",
            label="Notes:",
            full_width=True,
        )

        save_btn = mo.ui.button(
            label="💾 Save",
            kind="info",
            on_click=save_annotation,
        )

        remove_btn = mo.ui.button(
            label="❌ Remove Label",
            kind="warn",
            on_click=remove_annotation,
        )

        if len(_selected_rows) == 1:
            _first_row = _selected_rows.iloc[0]
            _option_id = str(_first_row["option_id"])
            _title_text = f"**Annotating Option #{_option_id}** ({_first_row['bean_name']} - {_first_row['roaster']})"
        else:
            _title_text = f"**Batch Annotating {len(_selected_rows)} Options**"

        feedback_ui = mo.vstack(
            [
                mo.md(_title_text),
                label_radio,
                notes_input,
                mo.hstack(
                    [
                        save_btn,
                        remove_btn,
                    ],
                    align="center",
                    justify="start",
                    gap=1,
                ),
                mo.md(get_status()),
            ],
        )

    mo.vstack(
        [
            mo.md("### 🏷️ Annotate Outliers for Ensemble Alignment"),
            feedback_ui,
        ]
    )
    return


@app.cell(hide_code=True)
def _(df_processed, find_bean_screenshot, line_chart_view, mo, table_widget):
    selected_rows = table_widget.value
    detail_view = mo.md(
        "*Select a row in the table above to view detailed diagnostics.*"
    )

    if len(selected_rows) > 0:
        row = selected_rows.iloc[-1]
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
            status = "🚨 **Outlier**" if opt["is_anomaly"] else "✅ Expected"
            options_rows.append(
                f"| {opt['weight']}g | {opt['price']:.2f} {opt['currency']} | ${opt['price_usd']:.2f} | ${opt['price_per_kg_usd']:.2f} | {opt['anomaly_score']:.4f} | {status}{is_current} |"
            )

        options_table_md = "\n".join(
            [
                "| Weight | Price | Package Price (USD) | Price per kg (USD) | Anomaly Score | Status |",
                "|---|---|---|---|---|---|",
                *options_rows,
            ]
        )

        header_text = f"#### 💡 Diagnostic Report: Option #{row['option_id']}"
        if len(selected_rows) > 1:
            header_text += (
                f" *(Showing last of {len(selected_rows)} selected items)*"
            )

        detail_view = mo.vstack(
            [
                mo.md(
                    f"""
                {header_text}
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
                mo.vstack([mo.md(options_table_md), line_chart_view]),
                mo.md("<br>"),
                screenshot_view,
            ]
        )

    # Generate CSV of all flagged anomalies across the whole dataset for download
    df_anoms_all = df_processed[df_processed["is_anomaly"] == 1]
    csv_data = df_anoms_all.to_csv(index=False).encode("utf-8")
    download_btn = mo.download(
        data=csv_data,
        filename="price_options_outliers.csv",
        label="📥 Download CSV of all Flagged Outliers",
    )

    mo.vstack([detail_view, mo.md("<br>"), download_btn])
    return


@app.cell(hide_code=True)
def roaster_bar_chart(df_processed, mo, px):
    df_bar = df_processed.copy()

    # Calculate roaster statistics (Total, Outliers, and Outlier Percentage)
    roaster_stats = (
        df_bar.groupby(["roaster", "is_anomaly"]).size().unstack(fill_value=0)
    )
    if 1 not in roaster_stats.columns:
        roaster_stats[1] = 0
    if 0 not in roaster_stats.columns:
        roaster_stats[0] = 0

    roaster_stats["total"] = roaster_stats[0] + roaster_stats[1]
    roaster_stats["outliers"] = roaster_stats[1]
    roaster_stats["outlier_pct"] = (
        roaster_stats[1] / roaster_stats["total"]
    ) * 100.0
    roaster_stats = roaster_stats.reset_index()

    fig_roasters_scatter = px.scatter(
        roaster_stats,
        x="total",
        y="outlier_pct",
        size="outliers",
        hover_name="roaster",
        hover_data={"total": True, "outliers": True, "outlier_pct": ":.2f"},
        title="🏢 Roaster Price Integrity Landscape",
        labels={
            "total": "Total Beans Scraped",
            "outlier_pct": "% Outliers",
            "outliers": "Number of Outliers",
        },
        size_max=25,
    )

    fig_roasters_scatter.update_traces(
        marker=dict(
            color="#d62728",
            opacity=0.75,
            line=dict(width=1.5, color="DarkSlateGrey"),
        )
    )

    fig_roasters_scatter.update_layout(
        plot_bgcolor="rgba(240, 240, 240, 0.5)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(title="Total Beans Scraped"),
        yaxis=dict(title="% Outliers (Rate)", range=[-5, 105]),
        height=450,
    )

    roaster_chart_widget = mo.ui.plotly(fig_roasters_scatter)

    mo.vstack(
        [
            mo.md("### 🏢 Roaster Price Integrity Landscape"),
            roaster_chart_widget,
        ]
    )
    return


@app.cell
def _():
    return


@app.cell
def time_series_trend(df_display, mo, px, roaster_filter):
    df_time = df_display.copy()
    df_time["Month"] = df_time["date_added"].dt.to_period("M").astype(str)
    df_time["Status"] = df_time["is_anomaly"].map(
        {0: "Expected", 1: "Outlier"}
    )

    df_time_grouped = (
        df_time.groupby(["Month", "Status"]).size().reset_index(name="count")
    )
    df_time_grouped = df_time_grouped.sort_values(by="Month")

    # Handle empty or filtered-down state nicely
    current_roaster_name = (
        roaster_filter.value if roaster_filter.value else "All"
    )

    fig_time = px.bar(
        df_time_grouped,
        x="Month",
        y="count",
        color="Status",
        color_discrete_map={"Expected": "#1f77b4", "Outlier": "#d62728"},
        title=f"📈 Price Outliers Trend Over Time: {current_roaster_name}",
        labels={
            "Month": "Month",
            "count": "Number of Beans",
            "Status": "Status",
        },
        hover_data={"Month": True, "count": True, "Status": True},
    ).update_xaxes(categoryorder="category ascending")

    fig_time.update_layout(
        barmode="stack",
        barnorm="percent",
        plot_bgcolor="rgba(240, 240, 240, 0.5)",
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=40, b=40),
        xaxis=dict(title="Month", type="category"),
        yaxis=dict(title="Number of Beans"),
        height=350,
    )

    time_chart_widget = mo.ui.plotly(fig_time)

    mo.vstack(
        [
            mo.md(f"### 📈 Outlier Trend Over Time ({current_roaster_name})"),
            time_chart_widget,
        ]
    )
    return


@app.cell(hide_code=True)
def _(df_processed, mo, px, table_widget):
    chart_selected_rows = table_widget.value
    line_chart_view = mo.md(
        "*Select a row in the table above to view the price vs. weight profile.*"
    )

    if len(chart_selected_rows) > 0:
        chart_selected_row = chart_selected_rows.iloc[-1]
        chart_full_row = df_processed[
            df_processed["option_id"] == chart_selected_row["option_id"]
        ].iloc[0]

        # Fetch all options matching this bean_id
        chart_bean_options = df_processed[
            df_processed["bean_id"] == chart_full_row["bean_id"]
        ].sort_values("weight")

        # Create line chart of price_usd vs weight for this bean
        fig_line = px.line(
            chart_bean_options,
            x="weight",
            y="price_usd",
            markers=True,
            title=f"📈 Price vs. Weight Profile",
            labels={
                "weight": "Package Weight (g)",
                "price_usd": "Package Price (USD)",
            },
        ).add_scatter(
            x=chart_bean_options["weight"],
            y=chart_bean_options["price_per_kg_usd"],
            name="Price per kg (USD)",
        )
        # Highlight the currently selected option with a different marker color/size/symbol
        selected_option_mask = (
            chart_bean_options["option_id"] == chart_selected_row["option_id"]
        )
        selected_opt = chart_bean_options[selected_option_mask]

        if not selected_opt.empty:
            fig_line.add_scatter(
                x=selected_opt["weight"],
                y=selected_opt["price_usd"],
                mode="markers",
                marker=dict(color="#d62728", size=12, symbol="star"),
                name="Selected Option",
                showlegend=True,
            )

        fig_line.update_layout(
            plot_bgcolor="rgba(240, 240, 240, 0.5)",
            paper_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=40, r=40, t=40, b=40),
            height=300,
        )

        line_chart_view = mo.ui.plotly(fig_line)
    return (line_chart_view,)


if __name__ == "__main__":
    app.run()
