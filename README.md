# CreditLens – Fintech Hackathon Demo

A runnable Streamlit prototype based on the CreditLens hackathon presentation.

## Features
- Applicant consent screen
- Synthetic UPI transaction data and optional CSV upload
- Cash-flow analysis and transparent 300–900 demo score
- Explainable score factors and monthly income chart
- Simulated micro-loan offer with EMI calculation
- Architecture walkthrough for judges

## Run locally
1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (recommended).
4. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

5. Start the app:

   ```bash
   streamlit run app.py
   ```

6. Open the local URL shown by Streamlit (usually http://localhost:8501).

## Judge demo flow (2–3 minutes)
1. Select an applicant profile in the left sidebar.
2. Enter applicant details and tick the consent checkbox.
3. Click **Analyse cash flow & generate CreditLens score**.
4. Open **Cash-flow insights** to show monthly income and explainable factors.
5. Open **Loan offer** to change amount and tenure and show the EMI.
6. Open **How it works** to explain how the prototype maps to the proposed product.

## CSV format
Required columns: `date,type,amount`
- `type` should be `CREDIT` or `DEBIT`
- `date` should be parseable as a date
- `amount` should be numeric
Optional columns: `mode,description`

A sample CSV is included as `sample_upi_transactions.csv`.

## Important limitations
This is a hackathon demonstration, not a real credit-scoring or lending system. The transaction data is synthetic. The score is a transparent rule-based baseline, not a trained XGBoost model and not a credit bureau score. SHAP, Account Aggregator, UPI and lender integrations are represented in the architecture explanation only. No actual loan approval or disbursement occurs. A production system would require consent infrastructure, security controls, model validation, fairness testing, KYC, lender partnerships and regulatory review.
