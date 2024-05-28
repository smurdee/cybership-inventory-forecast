import streamlit as st
import pandas as pd

st.title("Cybershit Inventory Forecasting raAAAH 🦅")
st.divider()

st.markdown("## Some data visualisation")

st.markdown("### Upload ur csv")

with st.container(border = True):
    # upload csv or use default
    csv_upload = st.file_uploader("Upload CSV", type=["csv"])

    # convert uplaoded file to dataframe
    if csv_upload is not None:
        df = pd.read_csv(csv_upload)
        st.write(f"Using `{csv_upload.name}`")
    else:
        st.write("Using default daily_quantities.csv")
        df = pd.read_csv("daily_quantities.csv")

    df['timestamp'] = pd.to_datetime(df['timestamp'])

st.markdown("### Parameters for plots")

with st.container(border = True):
    # item ID selection for forecasting
    unique_item_ids = df["item_id"].unique()
    item_id = st.selectbox("Select `item_id`", unique_item_ids)

    # pick forecast period & percentile
    period = st.slider("Moving avg Period (`period`)", 1, 90, 30)

    # filter dataframe based on selected item ID and drop item_id column
    df = df[df["item_id"] == item_id]
    df = df.sort_values("timestamp")
    df = df.drop("item_id", axis=1)

    # drop all demand=0 rows till the first demand>0
    for row in df.itertuples():
        if row.demand > 0:
            break
        df = df.drop(row.Index)
    df = df.reset_index(drop=True)

    # add columns that is the moving averages of demand
    df[f"{period}D_ma"] = df["demand"].rolling(window=period).mean()

    # add columns for the percentiles of demand
    df[f"{period}D_max"] = df["demand"].rolling(window=period).quantile(1)

    # extra columns for the MA
    df[f"14D_ma"] = df["demand"].rolling(window=14).mean()
    df[f"30D_ma"] = df["demand"].rolling(window=30).mean()
    df[f"60D_ma"] = df["demand"].rolling(window=60).mean()
    df[f"90D_ma"] = df["demand"].rolling(window=90).mean()

    # extra columns for the percentiles
    df[f"14D_max"] = df["demand"].rolling(window=14).quantile(1)
    df[f"30D_max"] = df["demand"].rolling(window=30).quantile(1)
    df[f"60D_max"] = df["demand"].rolling(window=60).quantile(1)
    df[f"90D_max"] = df["demand"].rolling(window=90).quantile(1)


with st.expander(f"{item_id} Dataset preview", expanded=False):
    # dataframe preview
    st.dataframe(df[['timestamp', 'demand', f"{period}D_ma", f"{period}D_max"]])

with st.container(border = True):
    # offer choices of lines to be showed
    lines = ["demand", f"{period}D_ma", f"{period}D_max"]
    selected_lines = st.multiselect("line plots", lines, default=lines)

    # plot the selected lines
    st.line_chart(data = df, x="timestamp", y=selected_lines)

st.divider()

st.markdown("## Industry standard inventory forecasting method")
st.caption("I'm referring to this [article](https://www.dhl.com/discover/en-my/small-business-advice/growing-your-business/inventory-forecasting-guide-for-small-businesses) for the following method")

with st.container(border = True):
    st.markdown("### 1. Lead time demand (LTD)")
    st.caption('"the measure of customer demand between the time you place an order for a product to when you receive it"')
    lead_time = st.number_input("Input `lead_time` (average time taken for vendor to ship product to you + you processing the shipment and storing it in the warehouse)", min_value=1, max_value=90, value=2)

    with st.container(border = True):
        st.markdown(f"Lead time demand (LTD) = average lifetime daily unit sales x average lead time")
        st.markdown(f"`LTD` for {item_id} = {df['demand'].mean().round(2)} x {lead_time} = {int(df['demand'].mean() * lead_time)}")
        ltd = (df['demand'].mean() * lead_time)
    
    st.markdown(f"This means that there is an estimated {int(ltd)} orders placed while you wait for your next stock to arrive.")

with st.container(border = True):
    st.markdown("### 2. Safety stock")
    st.caption('"the additional quantity of product you keep stored in your warehouse to avoid a situation where you run out of stock"')
    max_lead_time = st.number_input("Input `max_lead_time` (maximum time taken for vendor to ...)", min_value=1, max_value=90, value=5)
    
    with st.container(border = True):
        st.markdown("Safety stock formula = (maximum daily sales x maximum lead time) - (average daily sales x average lead time)")
        st.markdown(f"`safety_stock` for {item_id} = ({df['demand'].max()} x {max_lead_time}) - {int(ltd)} = {int((df['demand'].max() * max_lead_time) - (ltd))}")
        safety_stock = ((df['demand'].max() * max_lead_time) - (ltd))
    
    st.markdown(f"This means you will need {int(safety_stock)} {item_id} to ensure you have enough inventory in case something unforeseen happens")

with st.container(border=True):
    st.markdown("### 3. Reorder point")
    st.caption('"the level of inventory at which a company should replenish its stock"')

    with st.container(border=True):
        st.markdown("Reorder point formula = safety stock + (avg daily unit sales x avg lead time)")
        st.markdown(f"`ROP` for {item_id} = {int(safety_stock)} + {int(ltd)} = {int((safety_stock + (df['demand'].mean() * lead_time)).round(2))}")
        rop = (safety_stock + (df['demand'].mean() * lead_time))
    
    st.markdown(f"This means you have to replenish your stock when you reach {int(rop)} {item_id}s in inventory to avoid running out too quickly.")

st.markdown(f"#### theoretical TLDR: for {item_id}, you gotta restock when you have {int(rop)} {item_id}s in inventory.")

st.divider()

st.markdown("## Modifying industry std inventory forecasting for dropshippers/3PLs")
st.caption("But smurdee, my clients are all dropshipping/3PL bozos with inconsistent/irregular sale patterns, how do I tell these plebs how much to keep in inventory while taking into account they're all broke mfs?")

with st.container(border=True):
    st.markdown("### Hypothesis and implications that can be applied to aforementioned calculations:")

    with st.container(border=True):
        st.markdown("#### 1. Dropshippers/3PLs have seasonal sales cycles")
        st.markdown("Okay, so we need to figure out if the sales are at an uptrend or a downtrend at the moment. How do we classify stock as such?")
        st.markdown("Taking influence from crypto, we use moving averages to determine trends for example:")
        st.markdown("- 14D_MA > 30D_MA: uptrend")
        st.markdown("- 14D_MA < 30D_MA: downtrend")
    
        with st.container(border=True, ):
            st.markdown("For example, instead of using maximum daily sales in the `safety_stock` calculations, we can use 14D_max in an uptrend or 30D_max in a downtrend, to replace the maximum daily sales number.")
            st.markdown("Similarly, we can use 14D_MA or 30D_MA to replace the average daily sales number.")

    with st.container(border=True):
        st.markdown("#### 2. Dropshippers/3PLs have varying risk levels and budgetary constraints")
        st.markdown("Give your clients, 4 options to choose from: ultra low, low, medium, high, ultra high inventory risk levels.")
        st.markdown("- ultra low: maximum daily sales = lifetime maximum daily sales")
        st.markdown("- low: use 60D_MA vs 90D_MA for measuring trend direction")
        st.markdown("- medium: use 30D_MA vs 60D_MA for measuring trend direction")
        st.markdown("- high: use 14D_MA vs 30D_MA for measuring trend direction")

st.divider()

st.markdown("## Using trend and risk level to modify industry std inventory forecasting")

with st.container(border=True):
    risk_level = st.select_slider("Select `risk_level`", options=["ultra low", "low", "medium", "high"], value="medium")

    if risk_level == "ultra low":
        max_daily_sales = df['demand'].max()
        avg_daily_sales = df['demand'].mean()
        st.markdown(f"`max_daily_sales` = `lifetime_max_daily_sales` = {max_daily_sales}")
        st.markdown(f"`avg_daily_sales` = {avg_daily_sales.round(2)}")

    elif risk_level == "low":
        e_60D_MA = df['60D_ma'][len(df)-1]
        e_90D_MA = df['90D_ma'][len(df)-1]

        trend = "uptrend" if e_60D_MA > e_90D_MA else "downtrend"
        if trend == "uptrend":
            st.markdown(f"`60D_MA` = {e_60D_MA.round(2)} > `90D_MA` = {e_90D_MA.round(2)}")
            st.markdown(f"`trend`: {trend}")
            max_daily_sales = int(df['60D_max'][len(df)-1])
            avg_daily_sales = df['60D_ma'][len(df)-1]


        elif trend == "downtrend":
            st.markdown(f"`60D_MA` = {e_60D_MA.round(2)} < `90D_MA` = {e_90D_MA.round(2)}")
            st.markdown(f"`trend`: {trend}")
            max_daily_sales = int(df['90D_max'][len(df)-1])
            avg_daily_sales = df['90D_ma'][len(df)-1]

        st.markdown(f"`max_daily_sales` = {int(max_daily_sales)}")
        st.markdown(f"`avg_daily_sales` = {avg_daily_sales.round(2)}")
    
    elif risk_level == "medium":
        e_30D_MA = df['30D_ma'][len(df)-1]
        e_60D_MA = df['60D_ma'][len(df)-1]

        trend = "uptrend" if e_30D_MA > e_60D_MA else "downtrend"
        if trend == "uptrend":
            st.markdown(f"`30D_MA` = {e_30D_MA.round(2)} > `60D_MA` = {e_60D_MA.round(2)}")
            st.markdown(f"`trend`: {trend}")
            max_daily_sales = int(df['30D_max'][len(df)-1])
            avg_daily_sales = df['30D_ma'][len(df)-1]


        elif trend == "downtrend":
            st.markdown(f"`30D_MA` = {e_30D_MA.round(2)} < `60D_MA` = {e_60D_MA.round(2)}")
            st.markdown(f"`trend`: {trend}")
            max_daily_sales = int(df['60D_max'][len(df)-1])
            avg_daily_sales = df['60D_ma'][len(df)-1]

        st.markdown(f"`max_daily_sales` = {int(max_daily_sales)}")
        st.markdown(f"`avg_daily_sales` = {avg_daily_sales.round(2)}")

    elif risk_level == "high":
        e_14D_MA = df['14D_ma'][len(df)-1]
        e_30D_MA = df['30D_ma'][len(df)-1]

        trend = "uptrend" if e_14D_MA > e_30D_MA else "downtrend"
        if trend == "uptrend":
            st.markdown(f"`14D_MA` = {e_14D_MA.round(2)} > `30D_MA` = {e_30D_MA.round(2)}")
            st.markdown(f"`trend`: {trend}")
            max_daily_sales = int(df['14D_max'][len(df)-1])
            avg_daily_sales = df['14D_ma'][len(df)-1]


        elif trend == "downtrend":
            st.markdown(f"`14D_MA` = {e_30D_MA.round(2)} < `30D_MA` = {e_30D_MA.round(2)}")
            st.markdown(f"`trend`: {trend}")
            max_daily_sales = int(df['30D_max'][len(df)-1])
            avg_daily_sales = df['30D_ma'][len(df)-1]

        st.markdown(f"`max_daily_sales` = {int(max_daily_sales)}")
        st.markdown(f"`avg_daily_sales` = {avg_daily_sales.round(2)}")
    


with st.container(border=True):
    st.markdown("### 1. Lead time demand (LTD)")
    with st.container(border = True):
        st.markdown(f"Lead time demand (LTD) = average lifetime daily unit sales x average lead time")
        st.markdown(f"`LTD` for {item_id} = {avg_daily_sales.round(2)} x {lead_time} = {int(avg_daily_sales * lead_time)}")
        ltd = (avg_daily_sales * lead_time)
        
        st.markdown(f"This means that there is an estimated {int(ltd)} orders placed while you wait for your next stock to arrive.")

with st.container(border = True):
    st.markdown("### 2. Safety stock")
    
    with st.container(border = True):
        st.markdown("Safety stock formula = (maximum daily sales x maximum lead time) - (average daily sales x average lead time)")
        st.markdown(f"`safety_stock` for {item_id} = ({max_daily_sales} x {max_lead_time}) - {int(ltd)} = {int((max_daily_sales * max_lead_time) - (avg_daily_sales * lead_time))}")
        safety_stock = (max_daily_sales * max_lead_time) - (avg_daily_sales * lead_time)
    
    st.markdown(f"This means you will need {int(safety_stock)} {item_id} to ensure you have enough inventory in case something unforeseen happens")

with st.container(border=True):
    st.markdown("### 3. Reorder point")

    with st.container(border=True):
        st.markdown("Reorder point formula = safety stock + (avg daily unit sales x avg lead time)")
        st.markdown(f"`ROP` for {item_id} = {int(safety_stock)} + {int(ltd)} = {int((safety_stock + (avg_daily_sales * lead_time)))}")
        rop = (safety_stock + (avg_daily_sales * lead_time))
    
    st.markdown(f"This means you have to replenish your stock when you reach {int(rop)} {item_id}s in inventory to avoid running out too quickly.")

st.markdown(f"#### Now, for {item_id}, you gotta restock when you have {int(rop)} {item_id}s in inventory.")