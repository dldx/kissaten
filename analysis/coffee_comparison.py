import marimo

__generated_with = "0.19.11"
app = marimo.App()


@app.cell
def _():
    import marimo as mo
    import duckdb
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    import plotly.io as pio
    import colorsys

    # Cyberpunk palette from app.css (converted to HEX as Plotly doesn't support OKLCH)
    KISSATEN_COLORS = {
        "background": "#0b0f19",
        "foreground": "#e2e8f0",
        "primary": "#22d3ee",  # Neon Cyan
        "secondary": "#a855f7",  # Neon Purple
        "accent": "#10b981",  # Neon Green
        "uk": "#22d3ee",  # Cyan for UK
        "continent": "#a855f7",  # Purple for Continent
    }


    def hex_to_rgb(h):
        return tuple(int(h.lstrip("#")[i : i + 2], 16) for i in (0, 2, 4))


    def rgb_to_hex(rgb):
        return "#%02x%02x%02x" % tuple(int(x) for x in rgb)


    def get_shades(base_hex, n):
        if n == 0:
            return []
        rgb = hex_to_rgb(base_hex)
        h, l, s = colorsys.rgb_to_hls(*[x / 255.0 for x in rgb])
        shades = []
        for i in range(n):
            # Vary lightness and saturation slightly
            new_l = max(0.2, min(0.8, l * (0.6 + 0.8 * (i / max(1, n - 1)))))
            shades.append(
                rgb_to_hex([x * 255 for x in colorsys.hls_to_rgb(h, new_l, s)])
            )
        return shades


    # Define custom plotly template
    theme = go.layout.Template(
        layout=go.Layout(
            paper_bgcolor=KISSATEN_COLORS["background"],
            plot_bgcolor=KISSATEN_COLORS["background"],
            font=dict(
                family="Quicksand, sans-serif", color=KISSATEN_COLORS["foreground"]
            ),
            title=dict(font=dict(family="Cabin, sans-serif", size=24)),
            xaxis=dict(
                gridcolor="rgba(34, 211, 238, 0.1)",  # Faint cyan grid
                zerolinecolor="rgba(34, 211, 238, 0.2)",
            ),
            yaxis=dict(
                gridcolor="rgba(34, 211, 238, 0.1)",
                zerolinecolor="rgba(34, 211, 238, 0.2)",
            ),
        )
    )
    pio.templates["kissaten"] = theme
    pio.templates.default = "kissaten"
    return KISSATEN_COLORS, duckdb, get_shades, go, mo, pd, px


@app.cell
def _(df, mo, region_count):
    mo.md(rf"""
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Cabin:wght@700&family=Quicksand:wght@400;700&display=swap" rel="stylesheet">

    # ☕ Coffee Comparison: UK vs Continental Europe
    This notebook analyzes coffee beans from roasters in the UK versus those in Continental Europe using the Kissaten database.

    Based on {len(df)} beans from {region_count.loc["United Kingdom"]} UK roasters, plus {region_count.loc["Continental Europe"]} Continental roasters.
    """)
    return


@app.cell
def _(roaster_df):
    region_count = (
        roaster_df[["roaster", "roaster_location", "region_group"]]
        .groupby("region_group")
        .count()["roaster"]
    )
    return (region_count,)


@app.cell
def _(duckdb):
    # Connect to the database
    con = duckdb.connect("data/rw_kissaten.duckdb")
    return (con,)


@app.cell
def _(con):
    # Load combined data: beans + roaster location
    query = """
    SELECT 
        cb.*,
        r.location as roaster_location,
        rlc.code as roaster_country_code,
        rlc.region as roaster_region
    FROM coffee_beans cb
    JOIN roasters r ON cb.roaster = r.name
    LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
    WHERE rlc.region = 'Europe'
    """
    df = con.execute(query).df()

    # Categorize UK vs Continental Europe
    df["region_group"] = df["roaster_country_code"].apply(
        lambda x: "United Kingdom" if x == "GB" else "Continental Europe"
    )
    return (df,)


@app.cell
def _(mo):
    mo.md("""
    ## 1. Roast Level Breakdown
    """)
    return


@app.cell
def _(df, mo, px):
    def _():
        # Filter out NULL roast levels
        roast_df = df[df["roast_level"].notnull()].copy()

        # Define order
        roast_order = [
            "Extra-Light",
            "Light",
            "Medium-Light",
            "Medium",
            "Medium-Dark",
            "Dark",
        ]

        # Define coffee-themed colors for roast levels
        roast_colorsSource = {
            "Extra-Light": "#F5E6D3",
            "Light": "#D2B48C",
            "Medium-Light": "#BC8F8F",
            "Medium": "#8B4513",
            "Medium-Dark": "#5D2906",
            "Dark": "#3E1D03",
        }

        # Calculate counts and percentages for normalization per group
        counts = (
            roast_df.groupby(["region_group", "roast_level"])
            .size()
            .reset_index(name="count")
        )
        totals = counts.groupby("region_group")["count"].transform("sum")
        counts["percentage"] = (counts["count"] / totals) * 100

        fig_roast = px.bar(
            counts,
            y="region_group",
            x="percentage",
            color="roast_level",
            orientation="h",
            category_orders={"roast_level": roast_order},
            color_discrete_map=roast_colorsSource,
            title="<b>Roast Level Distribution</b>",
            subtitle="UK roasters tend to roast a little darker",
            template="kissaten",
            labels={
                "roast_level": "Roast Level",
                "percentage": "Percentage (%)",
                "count": "Number of Beans",
                "region_group": "",
            },
            hover_data={
                "percentage": ":.1f%",
                "count": True,
                "region_group": False,
            },
        )

        fig_roast.update_layout(
            xaxis_ticksuffix="%",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.01,
                xanchor="center",
                x=0.4,
                title_text="",
                traceorder="normal",
            ),
            height=400,
            margin_r=20,
            margin_l=120,
            margin_t=150,
        )

        return mo.ui.plotly(fig_roast)


    _()
    return


@app.cell
def _(mo):
    mo.md("""
    ## 2. Roaster Offering Strategy
    This section analyzes how roasters position their products:
    - **Both (Filter & Espresso)**: Roasters that explicitly offer separate roasts for Filter and Espresso.
    - **Omni Only**: Roasters that only offer "Omni" roasts (suitable for both brew methods).
    - **Mixed (Omni + others)**: Roasters that offer Omni roasts alongside some specific Filter or Espresso roasts.
    - **Filter Only / Espresso Only**: Roasters that specialize exclusively in one profile.
    """)
    return


@app.cell
def _(roaster_profiles):
    roaster_profiles
    return


@app.cell
def _(KISSATEN_COLORS, df, mo, pd, px):
    # Define roaster-level profiles
    # "Whether roasters offer both filter and espresso or only omni roast"

    roaster_profiles = (
        df.assign(roast_profile=lambda x: x.roast_profile.fillna("Unknown"))
        .groupby(["roaster", "region_group"])["roast_profile"]
        .agg(set)
        .reset_index()
    )


    def categorize_roaster(profiles):
        profiles = {p for p in profiles if p and pd.notnull(p)}
        if not profiles or (profiles == {"Unknown"}):
            return "Unknown"
        if "Filter" in profiles and "Espresso" in profiles:
            return "Both (Filter & Espresso)"
        if profiles == {"Omni"}:
            return "Omni Only"
        if "Omni" in profiles:
            return "Mixed (Omni + others)"
        if profiles == {"Filter", "Unknown"}:
            return "Filter Only"
        if profiles == {"Espresso", "Unknown"}:
            return "Espresso Only"
        return "Other"


    roaster_profiles["roaster_category"] = roaster_profiles["roast_profile"].apply(
        categorize_roaster
    )

    # Calculate counts and percentages for normalization
    profile_counts = (
        roaster_profiles[roaster_profiles["roaster_category"] != "Unknown"]
        .groupby(["region_group", "roaster_category"])
        .size()
        .reset_index(name="count")
    )
    profile_totals = profile_counts.groupby("region_group")["count"].transform(
        "sum"
    )
    profile_counts["percentage"] = (profile_counts["count"] / profile_totals) * 100

    fig_profile = px.bar(
        profile_counts,
        x="roaster_category",
        y="percentage",
        color="region_group",
        barmode="group",
        color_discrete_map={
            "United Kingdom": KISSATEN_COLORS["uk"],
            "Continental Europe": KISSATEN_COLORS["continent"],
        },
        title="<b>Roaster Offerings</b>",
        template="kissaten",
        labels={
            "roaster_category": "Offering Type",
            "percentage": "Percentage (%)",
            "count": "Number of Roasters",
        },
        hover_data=["count"],
    )
    fig_profile.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            title_text="",
            entrywidth=100,
            entrywidthmode="pixels",
        )
    )
    mo.ui.plotly(fig_profile)
    return (roaster_profiles,)


@app.cell
def _(mo, selected_country, selected_varietals):
    _vars = (
        ", ".join(selected_varietals.value)
        if selected_varietals.value
        else "All Varietals"
    )
    mo.md(f"""
    ## 6. Flavour Profiles
    A deep dive into the specific flavour profiles of **{selected_country} {selected_varietals}** beans.
    """)
    return


@app.cell(hide_code=True)
def _(con, mo, selected_country):
    varietals = mo.sql(
        f"""
        select variety_canonical from origins where country = '{selected_country.value}'
        """,
        output=False,
        engine=con,
    )
    return (varietals,)


@app.cell(hide_code=True)
def _(con, mo):
    countries_df = mo.sql(
        f"""
        SELECT DISTINCT country, country_codes.name 
        FROM origins
        JOIN country_codes ON origins.country = country_codes.alpha_2
        ORDER BY name
        """,
        engine=con,
    )
    return (countries_df,)


@app.cell
def _(countries_df, mo):
    selected_country = mo.ui.dropdown(
        options=dict(zip(countries_df["name"], countries_df["country"])),
        value="Panama",
    )
    selected_country
    return (selected_country,)


@app.cell
def _(mo, varietals):
    _options = varietals["variety_canonical"].explode().unique()
    selected_varietals = mo.ui.multiselect(
        options=_options,
        value=["Geisha"] if "Geisha" in _options else [],
    )
    selected_varietals
    return (selected_varietals,)


@app.cell(hide_code=True)
def _(
    KISSATEN_COLORS,
    con,
    get_shades,
    go,
    mo,
    pd,
    px,
    selected_country,
    selected_varietals,
):
    def _():
        # Query specifically for selected country/varietals and their flavour notes
        _varietal_filter = ""
        if selected_varietals.value:
            _v_list = "', '".join(selected_varietals.value)
            _varietal_filter = (
                f"AND (list_contains(o.variety_canonical, '{_v_list}'))"
            )

        geisha_query = f"""
        WITH filtered_beans AS (
            SELECT 
                cb.id,
                cb.tasting_notes,
                CASE WHEN rlc.code = 'GB' THEN 'United Kingdom' ELSE 'Continental Europe' END as region_group
            FROM coffee_beans cb
            JOIN origins o ON cb.id = o.bean_id
            JOIN roasters r ON cb.roaster = r.name
            LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
            WHERE (o.country = '{selected_country.value}')
              {_varietal_filter}
              AND rlc.region = 'Europe'
        )
        SELECT 
            gb.region_group,
            COALESCE(tnc.tertiary_category, tnc.secondary_category, tnc.primary_category, note) as canonical_note
        FROM filtered_beans gb,
        UNNEST(gb.tasting_notes) as t(note)
        LEFT JOIN tasting_notes_categories tnc ON t.note = tnc.tasting_note
        WHERE t.note IS NOT NULL
        """
        df_geisha = con.execute(geisha_query).df()

        if df_geisha.empty:
            return mo.md("No Panama Geisha data found for this comparison.")

        # Calculate counts and percentages
        n_counts = (
            df_geisha.groupby(["region_group", "canonical_note"])
            .size()
            .reset_index(name="count")
        )

        # Take Top 25 notes overall for readability in the area chart
        top_note_names = (
            n_counts.groupby("canonical_note")["count"]
            .sum()
            .nlargest(25)
            .index.tolist()
        )
        n_counts = n_counts[n_counts["canonical_note"].isin(top_note_names)]

        n_totals = n_counts.groupby("region_group")["count"].transform("sum")
        n_counts["percentage"] = (n_counts["count"] / n_totals) * 100

        # Ensure all notes exist in both groups for smooth area rendering
        notes = n_counts["canonical_note"].unique()
        groups_n = ["United Kingdom", "Continental Europe"]
        full_grid_n = pd.MultiIndex.from_product(
            [groups_n, notes], names=["region_group", "canonical_note"]
        ).to_frame(index=False)
        n_counts_full = full_grid_n.merge(
            n_counts, on=["region_group", "canonical_note"], how="left"
        ).fillna(0)

        # Calculate Continent vs UK deltas for the color map
        uk_pcts_n = n_counts_full[
            n_counts_full["region_group"] == "United Kingdom"
        ].set_index("canonical_note")["percentage"]
        cont_pcts_n = n_counts_full[
            n_counts_full["region_group"] == "Continental Europe"
        ].set_index("canonical_note")["percentage"]
        deltas_n = (cont_pcts_n - uk_pcts_n).to_dict()

        # Assign colors based on delta
        pos_notes = [n for n, d in deltas_n.items() if d >= 0]
        neg_notes = [n for n, d in deltas_n.items() if d < 0]

        pos_notes.sort(key=lambda x: deltas_n[x], reverse=True)
        neg_notes.sort(key=lambda x: deltas_n[x])

        color_map_n = {}
        pos_shades_n = get_shades(KISSATEN_COLORS["uk"], len(pos_notes))
        neg_shades_n = get_shades(KISSATEN_COLORS["secondary"], len(neg_notes))

        for i, n in enumerate(pos_notes):
            color_map_n[n] = pos_shades_n[i]
        for i, n in enumerate(neg_notes):
            color_map_n[n] = neg_shades_n[i]

        # Sort for stacking order
        n_order = (
            n_counts_full.groupby("canonical_note")["count"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )
        n_counts_full["canonical_note"] = pd.Categorical(
            n_counts_full["canonical_note"], categories=n_order, ordered=True
        )
        n_counts_full = n_counts_full.sort_values(
            ["region_group", "canonical_note"]
        )

        # Create the chart
        fig_geisha = px.area(
            n_counts_full,
            x="region_group",
            y="count",
            color="canonical_note",
            line_group="canonical_note",
            title=f"<b>{selected_country.value} {','.join(selected_varietals.value)} Flavour Trends</b>",
            template="kissaten",
            color_discrete_map=color_map_n,
            labels={
                "region_group": "Roaster Region",
                "count": "Normalized Share",
                "canonical_note": "Flavour Note",
            },
            category_orders={
                "region_group": ["United Kingdom", "Continental Europe"]
            },
            groupnorm="percent",
        )

        # Labels and annotations on the Continental side
        cont_n_data = n_counts_full[
            n_counts_full["region_group"] == "Continental Europe"
        ].copy()
        cont_n_data["percentage"] = (
            cont_n_data["count"] / cont_n_data["count"].sum()
        ) * 100
        cont_n_data = cont_n_data.sort_values("canonical_note", ascending=True)
        cont_n_data["cumsum"] = cont_n_data["percentage"].cumsum()
        cont_n_data["center"] = cont_n_data["cumsum"] - (
            cont_n_data["percentage"] / 2
        )

        for _, row in cont_n_data.iterrows():
            if row["percentage"] > 2.0:  # Threshold for visibility
                change_val_n = deltas_n.get(row["canonical_note"], 0)
                change_str_n = (
                    f"{change_val_n:+.1f}%" if abs(change_val_n) >= 0.1 else "≈"
                )
                label_text_n = f" {row['canonical_note']} ({change_str_n})"

                fig_geisha.add_annotation(
                    x="Continental Europe",
                    y=row["center"],
                    text=label_text_n,
                    showarrow=False,
                    xanchor="left",
                    xshift=10,
                    font=dict(size=10, color=KISSATEN_COLORS["foreground"]),
                    align="left",
                )

        # Add custom region preference legend
        fig_geisha.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=KISSATEN_COLORS["uk"]),
                name="Favorited on Continent",
                showlegend=True,
            )
        )
        fig_geisha.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=KISSATEN_COLORS["secondary"]),
                name="Favorited in UK",
                showlegend=True,
            )
        )

        # Disable legend for the actual method traces
        for trace_n in fig_geisha.data[:-2]:
            trace_n.showlegend = False

        fig_geisha.update_layout(
            yaxis_ticksuffix="%",
            height=900,
            margin=dict(r=150),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                title_text="",
                font=dict(size=12),
            ),
        )

        return mo.ui.plotly(fig_geisha)


    _()
    return


@app.cell
def _(mo, selected_country, selected_varietals):
    mo.md(f"""
    ## 7. Price Comparison
    Comparing the price distribution of the premium **{selected_country} {selected_varietals}** variety across regions.
    """)
    return


@app.cell
def _(KISSATEN_COLORS, con, mo, px, selected_country, selected_varietals):
    def _():
        # Get the USD to GBP rate
        fx_result = con.execute(
            "SELECT rate FROM currency_rates WHERE base_currency = 'USD' AND target_currency = 'GBP'"
        ).fetchone()
        usd_to_gbp = fx_result[0] if fx_result else 0.75

        # Query for filtered beans prices
        _varietal_filter = ""
        if selected_varietals.value:
            _v_list = "') OR list_contains(o.variety_canonical, '".join(
                selected_varietals.value
            )
            _varietal_filter = (
                f"AND (list_contains(o.variety_canonical, '{_v_list}'))"
            )

        geisha_price_query = f"""
        SELECT 
            cb.price_usd,
            cb.weight,
            CASE WHEN rlc.code = 'GB' THEN 'United Kingdom' ELSE 'Continental Europe' END as region_group
        FROM coffee_beans cb
        JOIN origins o ON cb.id = o.bean_id
        JOIN roasters r ON cb.roaster = r.name
        LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
        WHERE (o.country = '{selected_country.value}')
          {_varietal_filter}
          AND rlc.region = 'Europe'
          AND cb.price_usd IS NOT NULL 
          AND cb.weight IS NOT NULL 
          AND cb.weight > 0
        """
        df_geisha_price = con.execute(geisha_price_query).df()

        if df_geisha_price.empty:
            return mo.md("No price data found for Panama Geisha.")

        # Convert to GBP and normalize by weight (Price per 250g)
        df_geisha_price["price_gbp_250g"] = (
            (df_geisha_price["price_usd"] / df_geisha_price["weight"])
            * 250
            * usd_to_gbp
        )

        fig_geisha_price = px.histogram(
            df_geisha_price,
            x="price_gbp_250g",
            color="region_group",
            barmode="overlay",
            marginal="box",
            histnorm="percent",
            color_discrete_map={
                "United Kingdom": KISSATEN_COLORS["uk"],
                "Continental Europe": KISSATEN_COLORS["continent"],
            },
            title=f"<b>{selected_country.value} {','.join(selected_varietals.value)} Prices</b>",
            template="kissaten",
            labels={
                "price_gbp_250g": "Price (£ per 250g)",
                "region_group": "Roaster Region",
            },
            opacity=0.6,
            nbins=30,
        )

        fig_geisha_price.update_layout(
            xaxis_title="Price (£/250g)",
            yaxis_title="Percentage of beans (%)",
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                title_text="",
            ),
            xaxis_range=(0, df_geisha_price["price_gbp_250g"].max() * 1.1),
        )
        return mo.ui.plotly(fig_geisha_price)


    _()
    return


@app.cell
def _(mo):
    mo.md("""
    ## 3. Origin Distribution Comparison
    """)
    return


@app.cell
def _(KISSATEN_COLORS, con, get_shades, go, pd, px):
    def _():
        # Load origin data joined with roaster groups
        origin_query = """
        SELECT 
            COALESCE(cc_origin.name, o.country, 'Unknown') as origin_country_name,
            CASE WHEN rlc.code = 'GB' THEN 'United Kingdom' ELSE 'Continental Europe' END as region_group
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        JOIN roasters r ON cb.roaster = r.name
        LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
        LEFT JOIN country_codes cc_origin ON o.country = cc_origin.alpha_2
        WHERE rlc.region = 'Europe'
        """
        df_origin_raw = con.execute(origin_query).df()

        # Calculate counts and percentages
        counts = (
            df_origin_raw.groupby(["region_group", "origin_country_name"])
            .size()
            .reset_index(name="count")
        )
        totals = counts.groupby("region_group")["count"].transform("sum")
        counts["percentage"] = (counts["count"] / totals) * 100

        # Ensure all origins exist in both groups
        origins = counts["origin_country_name"].unique()
        groups = ["United Kingdom", "Continental Europe"]
        full_grid = pd.MultiIndex.from_product(
            [groups, origins], names=["region_group", "origin_country_name"]
        ).to_frame(index=False)
        counts_full = full_grid.merge(
            counts, on=["region_group", "origin_country_name"], how="left"
        ).fillna(0)

        # Calculate Continent vs UK deltas for the color map
        uk_pcts = counts_full[
            counts_full["region_group"] == "United Kingdom"
        ].set_index("origin_country_name")["percentage"]
        cont_pcts = counts_full[
            counts_full["region_group"] == "Continental Europe"
        ].set_index("origin_country_name")["percentage"]
        deltas = (cont_pcts - uk_pcts).to_dict()

        # Assign colors based on delta
        # Positive/Neutral = Cyan palette, Negative = Purple palette
        pos_origins = [o for o, d in deltas.items() if d >= 0]
        neg_origins = [o for o, d in deltas.items() if d < 0]

        # Sort for consistent shading
        pos_origins.sort(key=lambda x: deltas[x], reverse=True)
        neg_origins.sort(key=lambda x: deltas[x])

        # Generate color map
        color_map = {}
        # Use variations of the primary/secondary colors
        # For a high-quality feel, we'll use slightly varying shades
        pos_shades = get_shades(KISSATEN_COLORS["uk"], len(pos_origins))
        neg_shades = get_shades(KISSATEN_COLORS["secondary"], len(neg_origins))

        for i, o in enumerate(pos_origins):
            color_map[o] = pos_shades[i]
        for i, o in enumerate(neg_origins):
            color_map[o] = neg_shades[i]

        # Sort origins by total frequency for stacking order
        origin_order = (
            counts_full.groupby("origin_country_name")["count"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )
        counts_full["origin_country_name"] = pd.Categorical(
            counts_full["origin_country_name"],
            categories=origin_order,
            ordered=True,
        )
        counts_full = counts_full.sort_values(
            ["region_group", "origin_country_name"]
        )

        # Create the chart
        fig_origin = px.area(
            counts_full,
            x="region_group",
            y="count",
            color="origin_country_name",
            line_group="origin_country_name",
            title="<b>Coffee origins</b>",
            template="kissaten",
            color_discrete_map=color_map,
            labels={
                "region_group": "Roaster Region",
                "count": "Normalized Share",
                "origin_country_name": "Origin Country",
            },
            category_orders={
                "region_group": ["United Kingdom", "Continental Europe"]
            },
            groupnorm="percent",
        )

        # Calculate labels and annotations
        cont_data = counts_full[
            counts_full["region_group"] == "Continental Europe"
        ].copy()
        cont_data["percentage"] = (
            cont_data["count"] / cont_data["count"].sum()
        ) * 100
        cont_data = cont_data.sort_values("origin_country_name", ascending=True)
        cont_data["cumsum"] = cont_data["percentage"].cumsum()
        cont_data["center"] = cont_data["cumsum"] - (cont_data["percentage"] / 2)

        for _, row in cont_data.iterrows():
            if row["percentage"] > 1.2:
                change_val = deltas.get(row["origin_country_name"], 0)
                change_str = (
                    f"{change_val:+.1f}%" if abs(change_val) >= 0.1 else "≈"
                )
                label_text = f" {row['origin_country_name']} ({change_str})"

                fig_origin.add_annotation(
                    x="Continental Europe",
                    y=row["center"],
                    text=label_text,
                    showarrow=False,
                    xanchor="left",
                    xshift=10,
                    font=dict(size=10, color=KISSATEN_COLORS["foreground"]),
                    align="left",
                )

        # Add dummy traces for a custom legend
        fig_origin.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=KISSATEN_COLORS["uk"]),
                name="More common on the Continent",
                showlegend=True,
            )
        )
        fig_origin.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=KISSATEN_COLORS["secondary"]),
                name="More common in UK",
                showlegend=True,
            )
        )

        # Disable legend for the actual data traces (origins) to keep it clean
        for trace in fig_origin.data[:-2]:
            trace.showlegend = False
        return fig_origin.update_layout(
            yaxis_ticksuffix="%",
            height=900,
            margin=dict(r=120),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=0.99,
                xanchor="center",
                x=0.5,
                title_text="",
                font=dict(size=12),
            ),
        )


    _()
    return


@app.cell
def _(mo):
    mo.md("""
    ## 4. Varietal Choice Comparison
    """)
    return


@app.cell
def _(KISSATEN_COLORS, con, get_shades, go, pd, px):
    def _():
        # Load varietal data from origins table (Canonical names only)
        # variety_canonical is an array of strings
        varietal_query = """
        SELECT 
            UNNEST(o.variety_canonical) as varietal_name,
            CASE WHEN rlc.code = 'GB' THEN 'United Kingdom' ELSE 'Continental Europe' END as region_group
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        JOIN roasters r ON cb.roaster = r.name
        LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
        WHERE rlc.region = 'Europe' 
          AND o.variety_canonical IS NOT NULL 
          AND len(o.variety_canonical) > 0
        """
        df_varietal_raw = con.execute(varietal_query).df()

        # Calculate counts and percentages
        v_counts = (
            df_varietal_raw.groupby(["region_group", "varietal_name"])
            .size()
            .reset_index(name="count")
        )
        v_totals = v_counts.groupby("region_group")["count"].transform("sum")
        v_counts["percentage"] = (v_counts["count"] / v_totals) * 100

        # Ensure all varietals exist in both groups
        varietals = v_counts["varietal_name"].unique()
        groups_v = ["United Kingdom", "Continental Europe"]
        full_grid_v = pd.MultiIndex.from_product(
            [groups_v, varietals], names=["region_group", "varietal_name"]
        ).to_frame(index=False)
        v_counts_full = full_grid_v.merge(
            v_counts, on=["region_group", "varietal_name"], how="left"
        ).fillna(0)

        # Calculate Continent vs UK deltas for the color map
        uk_pcts_v = v_counts_full[
            v_counts_full["region_group"] == "United Kingdom"
        ].set_index("varietal_name")["percentage"]
        cont_pcts_v = v_counts_full[
            v_counts_full["region_group"] == "Continental Europe"
        ].set_index("varietal_name")["percentage"]
        deltas_v = (cont_pcts_v - uk_pcts_v).to_dict()

        # Assign colors based on delta
        pos_varietals = [v for v, d in deltas_v.items() if d >= 0]
        neg_varietals = [v for v, d in deltas_v.items() if d < 0]

        pos_varietals.sort(key=lambda x: deltas_v[x], reverse=True)
        neg_varietals.sort(key=lambda x: deltas_v[x])

        color_map_v = {}
        pos_shades_v = get_shades(KISSATEN_COLORS["uk"], len(pos_varietals))
        neg_shades_v = get_shades(KISSATEN_COLORS["secondary"], len(neg_varietals))

        for i, v in enumerate(pos_varietals):
            color_map_v[v] = pos_shades_v[i]
        for i, v in enumerate(neg_varietals):
            color_map_v[v] = neg_shades_v[i]

        # Sort for stacking order
        v_order = (
            v_counts_full.groupby("varietal_name")["count"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )
        v_counts_full["varietal_name"] = pd.Categorical(
            v_counts_full["varietal_name"], categories=v_order, ordered=True
        )
        v_counts_full = v_counts_full.sort_values(
            ["region_group", "varietal_name"]
        )

        # Create the chart
        fig_varietal = px.area(
            v_counts_full,
            x="region_group",
            y="count",
            color="varietal_name",
            line_group="varietal_name",
            title="<b>Coffee varietals</b>",
            template="kissaten",
            color_discrete_map=color_map_v,
            labels={
                "region_group": "Roaster Region",
                "count": "Normalized Share",
                "varietal_name": "Varietal",
            },
            category_orders={
                "region_group": ["United Kingdom", "Continental Europe"]
            },
            groupnorm="percent",
        )

        # Labels and annotations
        cont_v_data = v_counts_full[
            v_counts_full["region_group"] == "Continental Europe"
        ].copy()
        cont_v_data["percentage"] = (
            cont_v_data["count"] / cont_v_data["count"].sum()
        ) * 100
        cont_v_data = cont_v_data.sort_values("varietal_name", ascending=True)
        cont_v_data["cumsum"] = cont_v_data["percentage"].cumsum()
        cont_v_data["center"] = cont_v_data["cumsum"] - (
            cont_v_data["percentage"] / 2
        )

        for _, row in cont_v_data.iterrows():
            if row["percentage"] > 2.0:  # Higher threshold for varietals
                change_val_v = deltas_v.get(row["varietal_name"], 0)
                change_str_v = (
                    f"{change_val_v:+.1f}%" if abs(change_val_v) >= 0.1 else "≈"
                )
                label_text_v = f" {row['varietal_name']} ({change_str_v})"

                fig_varietal.add_annotation(
                    x="Continental Europe",
                    y=row["center"],
                    text=label_text_v,
                    showarrow=False,
                    xanchor="left",
                    xshift=10,
                    font=dict(size=10, color=KISSATEN_COLORS["foreground"]),
                    align="left",
                )

        fig_varietal.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=KISSATEN_COLORS["uk"]),
                name="More common on the Continent",
                showlegend=True,
            )
        )
        fig_varietal.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=KISSATEN_COLORS["secondary"]),
                name="More common in UK",
                showlegend=True,
            )
        )

        # Disable legend for the actual varietal traces
        for trace_v in fig_varietal.data[:-2]:
            trace_v.showlegend = False
        return fig_varietal.update_layout(
            yaxis_ticksuffix="%",
            height=900,
            margin=dict(r=120),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                title_text="",
                font=dict(size=12),
            ),
        )


    _()
    return


@app.cell
def _(mo):
    mo.md("""
    ## 5. Processing Method Comparison
    """)
    return


@app.cell
def _(KISSATEN_COLORS, con, get_shades, go, pd, px):
    def _():
        # Load processing method data from origins table (Canonical names only)
        process_query = """
        SELECT 
            o.process_common_name as process_name,
            CASE WHEN rlc.code = 'GB' THEN 'United Kingdom' ELSE 'Continental Europe' END as region_group
        FROM origins o
        JOIN coffee_beans cb ON o.bean_id = cb.id
        JOIN roasters r ON cb.roaster = r.name
        LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
        WHERE rlc.region = 'Europe' 
          AND o.process_common_name IS NOT NULL 
          AND o.process_common_name != ''
        """
        df_process_raw = con.execute(process_query).df()

        # Calculate counts and percentages
        p_counts = (
            df_process_raw.groupby(["region_group", "process_name"])
            .size()
            .reset_index(name="count")
        )
        p_totals = p_counts.groupby("region_group")["count"].transform("sum")
        p_counts["percentage"] = (p_counts["count"] / p_totals) * 100

        # Ensure all processes exist in both groups
        processes = p_counts["process_name"].unique()
        groups_p = ["United Kingdom", "Continental Europe"]
        full_grid_p = pd.MultiIndex.from_product(
            [groups_p, processes], names=["region_group", "process_name"]
        ).to_frame(index=False)
        p_counts_full = full_grid_p.merge(
            p_counts, on=["region_group", "process_name"], how="left"
        ).fillna(0)

        # Calculate Continent vs UK deltas for the color map
        uk_pcts_p = p_counts_full[
            p_counts_full["region_group"] == "United Kingdom"
        ].set_index("process_name")["percentage"]
        cont_pcts_p = p_counts_full[
            p_counts_full["region_group"] == "Continental Europe"
        ].set_index("process_name")["percentage"]
        deltas_p = (cont_pcts_p - uk_pcts_p).to_dict()

        # Assign colors based on delta
        # Positive/Neutral = Cyan palette, Negative = Purple palette
        pos_processes = [p for p, d in deltas_p.items() if d >= 0]
        neg_processes = [p for p, d in deltas_p.items() if d < 0]

        pos_processes.sort(key=lambda x: deltas_p[x], reverse=True)
        neg_processes.sort(key=lambda x: deltas_p[x])

        color_map_p = {}
        pos_shades_p = get_shades(KISSATEN_COLORS["uk"], len(pos_processes))
        neg_shades_p = get_shades(KISSATEN_COLORS["secondary"], len(neg_processes))

        for i, p in enumerate(pos_processes):
            color_map_p[p] = pos_shades_p[i]
        for i, p in enumerate(neg_processes):
            color_map_p[p] = neg_shades_p[i]

        # Sort for stacking order
        p_order = (
            p_counts_full.groupby("process_name")["count"]
            .sum()
            .sort_values(ascending=False)
            .index.tolist()
        )
        p_counts_full["process_name"] = pd.Categorical(
            p_counts_full["process_name"], categories=p_order, ordered=True
        )
        p_counts_full = p_counts_full.sort_values(["region_group", "process_name"])

        # Create the chart
        fig_process = px.area(
            p_counts_full,
            x="region_group",
            y="count",
            color="process_name",
            line_group="process_name",
            title="<b>Processing methods</b>",
            template="kissaten",
            color_discrete_map=color_map_p,
            labels={
                "region_group": "Roaster Region",
                "count": "Normalized Share",
                "process_name": "Process",
            },
            category_orders={
                "region_group": ["United Kingdom", "Continental Europe"]
            },
            groupnorm="percent",
        )

        # Labels and annotations
        cont_p_data = p_counts_full[
            p_counts_full["region_group"] == "Continental Europe"
        ].copy()
        cont_p_data["percentage"] = (
            cont_p_data["count"] / cont_p_data["count"].sum()
        ) * 100
        cont_p_data = cont_p_data.sort_values("process_name", ascending=True)
        cont_p_data["cumsum"] = cont_p_data["percentage"].cumsum()
        cont_p_data["center"] = cont_p_data["cumsum"] - (
            cont_p_data["percentage"] / 2
        )

        for _, row in cont_p_data.iterrows():
            if row["percentage"] > 2.0:
                change_val_p = deltas_p.get(row["process_name"], 0)
                change_str_p = (
                    f"{change_val_p:+.1f}%" if abs(change_val_p) >= 0.1 else "≈"
                )
                label_text_p = f" {row['process_name']} ({change_str_p})"

                fig_process.add_annotation(
                    x="Continental Europe",
                    y=row["center"],
                    text=label_text_p,
                    showarrow=False,
                    xanchor="left",
                    xshift=10,
                    font=dict(size=10, color=KISSATEN_COLORS["foreground"]),
                    align="left",
                )

        fig_process.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=KISSATEN_COLORS["uk"]),
                name="More common on the Continent",
                showlegend=True,
            )
        )
        fig_process.add_trace(
            go.Scatter(
                x=[None],
                y=[None],
                mode="markers",
                marker=dict(size=10, color=KISSATEN_COLORS["secondary"]),
                name="More common in UK",
                showlegend=True,
            )
        )

        # Disable legend for the actual method traces
        for trace_p in fig_process.data[:-2]:
            trace_p.showlegend = False

        return fig_process.update_layout(
            yaxis_ticksuffix="%",
            height=900,
            margin=dict(r=120),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
                title_text="",
                font=dict(size=12),
            ),
        )


    _()
    return


@app.cell
def _(mo):
    mo.md("""
    ## 8. Price Distribution
    Comparison of bean prices, converted to **GBP** for a common baseline.
    """)
    return


@app.cell
def _(KISSATEN_COLORS, con, px):
    # Get the USD to GBP rate
    fx_result = con.execute(
        "SELECT rate FROM currency_rates WHERE base_currency = 'USD' AND target_currency = 'GBP'"
    ).fetchone()
    usd_to_gbp = fx_result[0] if fx_result else 0.75  # Fallback if not found

    # Load prices, weight, and regions
    price_query = """
    SELECT 
        cb.price_usd,
        cb.weight,
        CASE WHEN rlc.code = 'GB' THEN 'United Kingdom' ELSE 'Continental Europe' END as region_group
    FROM coffee_beans cb
    JOIN roasters r ON cb.roaster = r.name
    LEFT JOIN roaster_location_codes rlc ON r.location = rlc.location
    WHERE rlc.region = 'Europe' 
      AND cb.price_usd IS NOT NULL 
      AND cb.weight IS NOT NULL 
      AND cb.weight > 0
    """
    df_price = con.execute(price_query).df()

    # Convert to GBP and normalize by weight (Price per 250g)
    df_price["price_gbp_250g"] = (
        (df_price["price_usd"] / df_price["weight"]) * 250 * usd_to_gbp
    )

    # Create histogram
    fig_price = px.histogram(
        df_price,
        x="price_gbp_250g",
        color="region_group",
        barmode="overlay",
        marginal="box",
        histnorm="percent",
        color_discrete_map={
            "United Kingdom": KISSATEN_COLORS["uk"],
            "Continental Europe": KISSATEN_COLORS["continent"],
        },
        title="<b>Retail prices</b>",
        subtitle="UK beans are slightly cheaper",
        template="kissaten",
        labels={
            "price_gbp_250g": "Price (£ per 250g)",
            "region_group": "Roaster Region",
            "count": "Percentage (%)",
        },
        opacity=0.6,
        nbins=200,
    )

    fig_price.update_layout(
        xaxis_title="Price (£/250g)",
        yaxis_title="Percentage of beans (%)",
        margin_t=150,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.0,
            xanchor="center",
            x=0.5,
            title_text="",
            entrywidth=100,
            entrywidthmode="pixels",
        ),
        hovermode="x unified",
        xaxis_range=(0, 50),
    )
    return


@app.cell
def _(mo):
    mo.md("""
    ## 9. Geographic Coverage
    """)
    return


@app.cell
def _(KISSATEN_COLORS, df, px):
    # Calculate bean counts per roaster
    bean_counts = df.groupby("roaster").size().reset_index(name="bean_count")

    # Get unique roasters with their location info and merge with counts
    roaster_df = df.drop_duplicates("roaster").copy()
    roaster_df = roaster_df.merge(bean_counts, on="roaster")

    fig_coverage = px.treemap(
        roaster_df,
        path=["region_group", "roaster"],
        values="bean_count",
        title="Geographic Coverage: Regions, Countries, and Roasters",
        template="kissaten",
        color="region_group",
        color_discrete_map={
            "United Kingdom": KISSATEN_COLORS["uk"],
            "Continental Europe": KISSATEN_COLORS["continent"],
        },
    )

    fig_coverage.update_traces(textinfo="label+value")

    fig_coverage.update_layout(
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="center",
            x=0.5,
            title_text="",
            entrywidth=100,
            entrywidthmode="pixels",
        )
    )
    return (roaster_df,)


@app.cell
def _(mo):
    mo.md("""
    ### Roaster List by Group
    """)
    return


@app.cell
def _(mo, roaster_df):
    # Show a searchable table of roasters
    table = mo.ui.table(
        roaster_df[["roaster", "roaster_location", "region_group"]].sort_values(
            "roaster"
        ),
        label="List of Covered Roasters",
        selection=None,
        pagination=True,
    )
    return (table,)


@app.cell
def _(table):
    table
    return


@app.cell
def _():
    # con.close()
    return


if __name__ == "__main__":
    app.run()
