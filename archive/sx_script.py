import pandas as pd
import numpy as np
from sklearn.linear_model import LinearRegression
from datetime import timedelta
from quart import Quart, jsonify, request, render_template
from prisma import Prisma
import logging
import asyncio
from concurrent.futures import ThreadPoolExecutor
from asyncio import Semaphore

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Quart(__name__)
prisma = Prisma()
semaphore = Semaphore(100)
executor = ThreadPoolExecutor(max_workers=100)


async def predict_next_period(data, period=60):
    async with semaphore:
        logger.debug("Starting prediction for the next period.")
        df = pd.DataFrame(data)
        df["date"] = pd.to_datetime(df["date"])
        df.set_index("date", inplace=True)

        series = df["quantity"]

        # Check if data is empty
        if series.empty:
            raise ValueError("The data series is empty.")

        # Create a numerical index for linear regression
        series = series.reset_index()
        series.columns = ["date", "value"]
        series["day"] = (series["date"] - series["date"].min()).dt.days

        # Ensure no NaN values in 'day' column
        if series["day"].isnull().any():
            raise ValueError("NaN values found in the 'day' column.")

        # Fit linear regression model
        X = series["day"].values.reshape(-1, 1)
        y = series["value"].values
        model = await asyncio.get_event_loop().run_in_executor(
            executor, LinearRegression().fit, X, y
        )

        # Predict the next period
        max_day = series["day"].max()
        if max_day is None:
            raise ValueError("Max day value is None.")

        future_days = np.arange(max_day + 1, max_day + 1 + period).reshape(-1, 1)
        forecast = model.predict(future_days)
        forecast_dates = [
            series["date"].max() + timedelta(days=i) for i in range(1, period + 1)
        ]

        forecast_series = pd.Series(forecast, index=forecast_dates)

        # Calculate the cumulative sold units for the forecast period
        cumulative_sold_units = forecast_series.cumsum()

        logger.debug("Prediction completed.")
        return forecast_series, cumulative_sold_units


def estimate_stock_runout(cumulative_sold_units, current_stock):
    logger.debug("Estimating stock runout day.")
    runout_day = None
    for date, cumulative_units in cumulative_sold_units.items():
        if cumulative_units > current_stock:
            runout_day = date
            break
    return runout_day


@app.route("/")
async def index():
    return await render_template("index.html")


@app.route("/forecast", methods=["POST"])
async def get_forecast():
    content = await request.json
    if "sku" not in content or "period" not in content:
        return jsonify({"error": "Invalid input"}), 400

    sku = content["sku"]
    period = content["period"]

    try:
        if not prisma.is_connected():
            logger.debug("Connecting to Prisma.")
            await prisma.connect()

        shop = await prisma.shop.find_first(
            where={"id": "22d0279e-09b5-4043-beba-4707035aasdfs"},
            include={
                "orders": {
                    "include": {
                        "order_line_items": {
                            "include": {"product_listing_variant": True}
                        }
                    }
                }
            },
        )
        if not shop:
            return jsonify({"error": "Shop data not found"}), 404

        data = [
            {
                "date": order.created_at,
                "quantity": sum(
                    item.quantity
                    for item in order.order_line_items
                    if item.product_listing_variant
                    and item.product_listing_variant.sku == sku
                ),
            }
            for order in shop.orders
        ]

        forecast, cumulative_sold_units = await predict_next_period(data, period)

        inventory_bin_item = await prisma.inventorybinitem.find_first(
            where={"product": {"sku": sku}}
        )
        if not inventory_bin_item:
            return jsonify({"error": "Inventory data not found"}), 404
        current_stock = inventory_bin_item.on_hand

        runout_day = estimate_stock_runout(cumulative_sold_units, current_stock)
        while runout_day is None:
            additional_forecast, additional_cumulative_sold_units = (
                await predict_next_period(data, period)
            )
            forecast = pd.concat([forecast, additional_forecast])
            cumulative_sold_units = pd.concat(
                [cumulative_sold_units, additional_cumulative_sold_units]
            )
            runout_day = estimate_stock_runout(cumulative_sold_units, current_stock)

            data.extend(
                [
                    {"date": date, "quantity": qty}
                    for date, qty in additional_forecast.items()
                ]
            )

    except ValueError as e:
        logger.error(f"ValueError: {e}")
        return jsonify({"error": str(e)}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": "An unexpected error occurred"}), 500

    forecast_dict = {str(date): value for date, value in forecast.items()}
    cumulative_sold_units_dict = {
        str(date): value for date, value in cumulative_sold_units.items()
    }

    return jsonify(
        {
            "forecast": forecast_dict,
            "cumulative_sold_units": cumulative_sold_units_dict,
            "runout_day": str(runout_day),
            "current_stock": current_stock,
            "period": period,
        }
    )


if __name__ == "__main__":
    app.run(debug=True)
