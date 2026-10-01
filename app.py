    base = data[data["year"].isin(selected_years)] if selected_years else data.iloc[0:0]

    regions = sorted([x for x in base["region"].dropna().unique() if x != "Unknown"])
    selected_regions = st.multiselect("Region", regions, default=[])
    if selected_regions:
        base = base[base["region"].isin(selected_regions)]

    countries = sorted([x for x in base["country"].dropna().unique() if x != "Unknown"])
    country_options = ["All countries"] + countries
    selected_country = st.selectbox("Country", country_options, index=0)

    country_scope = base if selected_country == "All countries" else base[base["country"].eq(selected_country)]
    companies = sorted([x for x in country_scope["company"].dropna().unique() if x != "Unknown company"])
    company_options = ["All companies"] + companies
    selected_company = st.selectbox("Company", company_options, index=0)
    st.markdown('<div class="filter-caption">Company list changes automatically with the selected country.</div>', unsafe_allow_html=True)

    include_free = st.checkbox("Include free-of-charge rows", value=True)
    st.markdown("---")
    st.caption(f"Loaded {len(data):,} standardized rows from {data['source_file'].nunique()} file(s)")

filtered = country_scope.copy()
if selected_company != "All companies":
    filtered = filtered[filtered["company"].eq(selected_company)]
if not include_free:
    # 구분2 is typically 유상/무상; unknown structures are left untouched.
    filtered = filtered[~filtered["sales_type"].str.contains("무상|FOC|FREE", case=False, regex=True, na=False)]

metric_valid = filtered[metric].notna()
metric_df = filtered.loc[metric_valid].copy()

# -----------------------------
# Header
# -----------------------------
scope_parts = []
if selected_country != "All countries": scope_parts.append(selected_country)
if selected_company != "All companies": scope_parts.append(selected_company)
scope_text = " · ".join(scope_parts) if scope_parts else "Global portfolio"

st.markdown('<div class="dashboard-title">Global Sales Intelligence</div>', unsafe_allow_html=True)
st.markdown(
    f'<div class="dashboard-subtitle">{scope_text} &nbsp;|&nbsp; {metric_label} &nbsp;|&nbsp; {min(selected_years) if selected_years else "—"}–{max(selected_years) if selected_years else "—"}</div>',
    unsafe_allow_html=True,
)

if load_errors:
    with st.expander("Some files could not be loaded"):
        for err in load_errors:
            st.write(err)

if metric == "sales_usd":
    coverage = filtered["currency"].eq("USD").mean() if len(filtered) else 0
    if coverage < 0.85:
        st.warning(f"USD view covers {coverage:.0%} of the currently filtered rows. Use KRW for a fully comparable total across mixed currencies.")

# -----------------------------
# KPI strip
# -----------------------------
sales_total = metric_df[metric].sum(min_count=1)
qty_total = filtered["qty"].sum()
company_count = filtered["company"].replace("Unknown company", np.nan).nunique()
country_count = filtered["country"].replace("Unknown", np.nan).nunique()
sku_count = filtered["item_code"].replace("", np.nan).nunique()

k1, k2, k3, k4, k5 = st.columns(5)
k1.metric("Sales", compact_money(sales_total, metric), yoy_delta(metric_df, metric))
k2.metric("Quantity", f"{qty_total:,.0f}")
k3.metric("Active companies", f"{company_count:,}")
k4.metric("Countries", f"{country_count:,}")
k5.metric("Active SKUs", f"{sku_count:,}")

# -----------------------------
# Main tabs
# -----------------------------
t_overview, t_country, t_customer, t_product, t_quality = st.tabs(
    ["Overview", "Country", "Company", "Product Mix", "Data Quality"]
)

with t_overview:
    left, right = st.columns([1.45, 1])
    yearly = metric_df.groupby("year", as_index=False)[metric].sum(min_count=1).dropna()
    fig = px.bar(yearly, x="year", y=metric, text_auto=".3s")
    fig.update_traces(marker_color="#2E6BFF", hovertemplate=f"Year %{{x}}<br>{axis_money(metric)}%{{y:,.0f}}<extra></extra>")
    fig.update_yaxes(tickprefix=axis_money(metric))
    left.plotly_chart(style_figure(fig, "Sales by year"), use_container_width=True, config=PLOTLY_CONFIG)

    top_country = metric_df.groupby("country", as_index=False)[metric].sum(min_count=1).sort_values(metric, ascending=False).head(10)
    fig = px.bar(top_country.sort_values(metric), x=metric, y="country", orientation="h")
    fig.update_traces(marker_color="#142B4A", hovertemplate=f"%{{y}}<br>{axis_money(metric)}%{{x:,.0f}}<extra></extra>")
    fig.update_xaxes(tickprefix=axis_money(metric))
    right.plotly_chart(style_figure(fig, "Top countries"), use_container_width=True, config=PLOTLY_CONFIG)

    left, right = st.columns([1.45, 1])
    monthly = metric_df.dropna(subset=["year", "month"]).groupby(["year", "month"], as_index=False)[metric].sum(min_count=1)
    fig = px.line(monthly, x="month", y=metric, color="year", markers=True)
    fig.update_layout(legend_title_text="Year")
    fig.update_xaxes(dtick=1)
    fig.update_yaxes(tickprefix=axis_money(metric))
    left.plotly_chart(style_figure(fig, "Monthly trend"), use_container_width=True, config=PLOTLY_CONFIG)

    top_company = metric_df.groupby(["country", "company"], as_index=False)[metric].sum(min_count=1).sort_values(metric, ascending=False).head(12)
    top_company["label"] = top_company["company"].str.slice(0, 34)
    fig = px.bar(top_company.sort_values(metric), x=metric, y="label", orientation="h", hover_data=["country", "company"])
    fig.update_traces(marker_color="#6C8FF8")
    fig.update_xaxes(tickprefix=axis_money(metric))
    right.plotly_chart(style_figure(fig, "Top companies"), use_container_width=True, config=PLOTLY_CONFIG)

with t_country:
    if selected_country == "All countries":
        st.info("Select a country in the sidebar to open the country-level commercial view.")
    else:
        cscope = filtered.copy()
        a, b = st.columns([1.35, 1])
        company_sales = cscope[cscope[metric].notna()].groupby("company", as_index=False)[metric].sum(min_count=1).sort_values(metric, ascending=False)
        fig = px.bar(company_sales.head(15).sort_values(metric), x=metric, y="company", orientation="h")
        fig.update_traces(marker_color="#2E6BFF")
        fig.update_xaxes(tickprefix=axis_money(metric))
        a.plotly_chart(style_figure(fig, f"{selected_country} · company contribution"), use_container_width=True, config=PLOTLY_CONFIG)

        company_year = cscope[cscope[metric].notna()].groupby(["year", "company"], as_index=False)[metric].sum(min_count=1)
        top_names = company_sales.head(7)["company"].tolist()
        company_year = company_year[company_year["company"].isin(top_names)]
        fig = px.line(company_year, x="year", y=metric, color="company", markers=True)
        fig.update_yaxes(tickprefix=axis_money(metric))
        b.plotly_chart(style_figure(fig, "Company trend"), use_container_width=True, config=PLOTLY_CONFIG)

        st.markdown("### Company performance")
        table = cscope.groupby("company", as_index=False).agg(
            Sales=(metric, "sum"),
            Quantity=("qty", "sum"),
            SKUs=("item_code", "nunique"),
            First_Sale=("date", "min"),
            Last_Sale=("date", "max"),
        ).sort_values("Sales", ascending=False)
        table["Share %"] = np.where(table["Sales"].sum() != 0, table["Sales"] / table["Sales"].sum() * 100, 0)
        st.dataframe(
            table,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Sales": st.column_config.NumberColumn("Sales", format="$%.0f" if metric == "sales_usd" else "₩%.0f"),
                "Quantity": st.column_config.NumberColumn("Qty", format="%.0f"),
                "Share %": st.column_config.ProgressColumn("Share", min_value=0, max_value=100, format="%.1f%%"),
                "First_Sale": st.column_config.DateColumn("First sale"),
                "Last_Sale": st.column_config.DateColumn("Last sale"),
            },
        )

with t_customer:
    if selected_company == "All companies":
        st.info("Select a company in the sidebar. The company list is already filtered by the selected country.")
    else:
        s = filtered.copy()
        a, b = st.columns([1.4, 1])
        trend = s[s[metric].notna()].dropna(subset=["year", "month"]).groupby(["year", "month"], as_index=False)[metric].sum(min_count=1)
        fig = px.line(trend, x="month", y=metric, color="year", markers=True)
        fig.update_xaxes(dtick=1)
        fig.update_yaxes(tickprefix=axis_money(metric))
        a.plotly_chart(style_figure(fig, "Monthly sales pattern"), use_container_width=True, config=PLOTLY_CONFIG)

        prod = s[s[metric].notna()].groupby("level5", as_index=False)[metric].sum(min_count=1).sort_values(metric, ascending=False).head(10)
        fig = px.bar(prod.sort_values(metric), x=metric, y="level5", orientation="h")
        fig.update_traces(marker_color="#6C8FF8")
        fig.update_xaxes(tickprefix=axis_money(metric))
        b.plotly_chart(style_figure(fig, "Top product markers / L5"), use_container_width=True, config=PLOTLY_CONFIG)

        st.markdown("### Product detail")
        ptab = s.groupby(["item_code", "item_name", "level4", "level5"], as_index=False).agg(
            Sales=(metric, "sum"), Quantity=("qty", "sum"), Last_Sale=("date", "max")
        ).sort_values("Sales", ascending=False)
        st.dataframe(ptab, use_container_width=True, hide_index=True)

with t_product:
    hierarchy = [c for c in ["level1", "level2", "level3", "level4", "level5"] if filtered[c].ne("Unknown").any()]
    if not hierarchy:
        st.info("No product hierarchy columns were detected in the current selection.")
    else:
        tree_df = filtered[filtered[metric].notna()].copy()
        # Avoid huge treemaps: aggregate first and keep top branches.
        agg = tree_df.groupby(hierarchy, as_index=False)[metric].sum(min_count=1)
        if len(agg) > 500:
            agg = agg.nlargest(500, metric)
        fig = px.treemap(agg, path=hierarchy, values=metric)
        fig.update_traces(root_color="#F2F4F7")
        st.plotly_chart(style_figure(fig, "Product portfolio structure"), use_container_width=True, config=PLOTLY_CONFIG)

        left, right = st.columns(2)
        l4 = filtered[filtered[metric].notna()].groupby("level4", as_index=False)[metric].sum(min_count=1).sort_values(metric, ascending=False).head(12)
        fig = px.bar(l4.sort_values(metric), x=metric, y="level4", orientation="h")
        fig.update_traces(marker_color="#142B4A")
        fig.update_xaxes(tickprefix=axis_money(metric))
        left.plotly_chart(style_figure(fig, "Top Level 4 categories"), use_container_width=True, config=PLOTLY_CONFIG)
