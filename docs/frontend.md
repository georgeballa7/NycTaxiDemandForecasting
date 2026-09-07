# Frontend

The Streamlit application is the presentation layer of the project. It consumes prepared analytics and model results through FastAPI instead of running PySpark or training models in response to user interaction.

## Application Responsibilities

The application presents three main types of information:

- exploratory demand and trip analytics;
- historical model evaluation;
- future taxi-demand forecasts.

The UI obtains zones, metrics, analytical results and predictions from API endpoints. This separation keeps the frontend lightweight and allows the backend or database implementation to evolve without duplicating data logic in Streamlit.

## Historical Model View

The model-evaluation view displays persisted evaluation metrics, feature importance and historical predictions. These results represent the latest published model state; they are not hard-coded into the page.

## Future Forecast View

A user selects a taxi zone and future date/time. Streamlit sends the request to FastAPI and displays the returned demand estimate and forecast method.

The validation section retrieves the stored future-model metrics and shows all evaluated candidates. The production model is identified dynamically from the published results, so the interface does not assume that a particular algorithm must always win.

## Design Principle

Streamlit is deliberately a consumer of the production data contract. It does not read large processed datasets, start Spark or choose models itself. As new monthly data is ingested and the backend republishes results, the application automatically reflects the updated state.
