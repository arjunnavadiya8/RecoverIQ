# Deployment checklist

## API on Render

1. Generate and verify `artifacts/model.joblib` from real Olist data.
2. Decide artifact distribution: commit only if repository policy and file size permit; otherwise download a versioned release artifact during build.
3. Push to GitHub and create a Render Blueprint from `render.yaml`.
4. Confirm `/health`, `/model-info`, `/predict` and `/docs`.
5. Note in the README that free services sleep after inactivity and may cold-start.

## Dashboard on Streamlit Community Cloud

1. Ensure the app can access the generated read-only warehouse extracts and artifacts.
2. Select the repository, branch and `app.py` entry point.
3. Confirm every page on desktop and mobile width.
4. Test from a signed-out browser and add the stable URL to the README.

## Release gate

- CI green, real-data warning correct, no secrets or raw customer data in Git
- Demo numbers replaced with real historical results
- Model and causal cards reviewed against generated JSON
- API rejects invalid inputs and dashboard labels assumptions

