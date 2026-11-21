import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import sqlite3
import hashlib

# =====================================================
# PAGE CONFIGURATION
# =====================================================

st.set_page_config(
    page_title="CreditLens | Fintech Demo",
    page_icon="💳",
    layout="wide"
)

# =====================================================
# SESSION STATE INITIALIZATION
# =====================================================

if "logged_user" not in st.session_state:
    st.session_state.logged_user = ""
defaults = {
    "consent": False,
    "analysed": False,
    "loan_authenticated": False,
    "offer_generated": False,
    "applicant": "",
    "occupation": "",
    "city": "",
    "transactions": None
}

for key, value in defaults.items():
    if key not in st.session_state:
        st.session_state[key] = value

# =====================================================
# LOGIN CREDENTIALS
# =====================================================


# DATABASE SETUP

def create_database():
    conn = sqlite3.connect("creditlens_users.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()


def hash_password(password):
    return hashlib.sha256(
        password.encode()
    ).hexdigest()


def register_user(name, email, password):
    conn = sqlite3.connect("creditlens_users.db")
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO users (name, email, password) VALUES (?, ?, ?)",
            (name, email, hash_password(password))
        )

        conn.commit()
        return True

    except sqlite3.IntegrityError:
        return False

    finally:
        conn.close()


def verify_user(email, password):
    conn = sqlite3.connect("creditlens_users.db")
    cursor = conn.cursor()

    cursor.execute(
        "SELECT name FROM users WHERE email=? AND password=?",
        (email, hash_password(password))
    )

    user = cursor.fetchone()
    conn.close()

    return user


create_database()


# =====================================================
# CUSTOM CSS
# =====================================================

st.markdown("""
<style>

.stApp {
    background-color: #f5f7fb;
}

.block-container {
    padding-top: 1.4rem;
    max-width: 1250px;
}

.hero {
    background: linear-gradient(115deg,#102a43,#176b87);
    padding: 28px;
    border-radius: 18px;
    color: white;
    margin-bottom: 20px;
}

.hero h1 {
    color: white;
    font-size: 2.3rem;
}

.hero p {
    color: #d8edf4;
}

.metric-card {
    background: white;
    padding: 18px;
    border-radius: 14px;
    border: 1px solid #e6ebf2;
}

</style>
""", unsafe_allow_html=True)

# =====================================================
# HEADER
# =====================================================

st.markdown("""
<div class="hero">
    <h1>💳 CreditLens</h1>
    <p>Fair, Explainable Micro-Credit Powered by Everyday Cash Flow</p>
    <p>
    FINTECH HACKATHON PROTOTYPE |
    SIMULATED DATA |
    NOT A REAL LOAN APPROVAL
    </p>
</div>
""", unsafe_allow_html=True)

# =====================================================
# HELPER FUNCTIONS
# =====================================================

def money(value):
    return "₹{:,.2f}".format(value)


def make_demo_data(
    months=6,
    daily_income=1450,
    expense_ratio=0.62,
    volatility=0.18
):
    rng = np.random.default_rng(42)

    rows = []

    today = pd.Timestamp.today().normalize()

    start = today - pd.DateOffset(months=months)

    days = pd.date_range(start, today, freq="D")

    for d in days:

        if d.weekday() < 6 and rng.random() < 0.78:

            income = max(
                150,
                rng.normal(
                    daily_income,
                    daily_income * volatility
                )
            )

            rows.append([
                d,
                "CREDIT",
                round(float(income), 2),
                "UPI",
                "Customer payments"
            ])

        if rng.random() < 0.72:

            expense = max(
                40,
                rng.normal(
                    daily_income * expense_ratio / 2.2,
                    90
                )
            )

            rows.append([
                d,
                "DEBIT",
                round(float(expense), 2),
                "UPI",
                "Business / household expense"
            ])

    return pd.DataFrame(
        rows,
        columns=[
            "date",
            "type",
            "amount",
            "mode",
            "description"
        ]
    )


def calculate_score(df):

    df = df.copy()

    df["type"] = df["type"].astype(str).str.upper()

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    credits = df[
        df["type"].isin(["CREDIT", "INCOME"])
    ]["amount"].sum()

    debits = df[
        df["type"].isin(["DEBIT", "EXPENSE"])
    ]["amount"].sum()

    monthly = df.copy()

    monthly["date"] = pd.to_datetime(monthly["date"])

    monthly["month"] = (
        monthly["date"].dt.to_period("M").astype(str)
    )

    income_by_month = (
        monthly[
            monthly["type"].isin(["CREDIT", "INCOME"])
        ]
        .groupby("month")["amount"]
        .sum()
    )

    if len(income_by_month) > 1 and income_by_month.mean() > 0:

        stability = max(
            0,
            1 - (
                income_by_month.std()
                / income_by_month.mean()
            )
        )

    else:
        stability = 0.55

    credit_count = len(
        df[df["type"].isin(["CREDIT", "INCOME"])]
    )

    net_ratio = max(
        0,
        min(
            1,
            (credits - debits) / max(credits, 1)
        )
    )

    frequency = min(1, credit_count / 100)

    score = int(np.clip(
        300
        + 250 * stability
        + 180 * net_ratio
        + 170 * frequency
        + 60 * min(1, len(income_by_month) / 6),
        300,
        900
    ))

    return (
        score,
        credits,
        debits,
        income_by_month,
        stability,
        net_ratio,
        credit_count
    )


def prepare_csv(uploaded_file):

    df = pd.read_csv(uploaded_file)

    df.columns = [
        str(c).strip().lower()
        for c in df.columns
    ]

    required = {"date", "type", "amount"}

    if not required.issubset(df.columns):
        raise ValueError(
            "CSV must contain date, type and amount columns."
        )

    df["date"] = pd.to_datetime(
        df["date"],
        errors="coerce"
    )

    df["type"] = (
        df["type"].astype(str).str.strip().str.upper()
    )

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["date", "type", "amount"]
    )

    df = df[
        df["type"].isin(
            ["CREDIT", "DEBIT", "INCOME", "EXPENSE"]
        )
    ]

    df = df[df["amount"] >= 0]

    if df.empty:
        raise ValueError(
            "No valid transactions found in CSV."
        )

    return df


# =====================================================
# SIDEBAR
# =====================================================

st.sidebar.title("⚙️ Demo Controls")

st.sidebar.caption(
    "Create different applicant profiles."
)

profile = st.sidebar.selectbox(
    "Applicant Profile",
    [
        "Street vendor – steady income",
        "Delivery partner – variable income",
        "New small merchant – growing income"
    ]
)

if profile.startswith("Street"):

    daily_income = 1550
    expense_ratio = 0.60
    volatility = 0.12

elif profile.startswith("Delivery"):

    daily_income = 1250
    expense_ratio = 0.72
    volatility = 0.34

else:

    daily_income = 1850
    expense_ratio = 0.58
    volatility = 0.22


months = st.sidebar.slider(
    "Transaction History (Months)",
    3,
    12,
    6
)

daily_income = st.sidebar.slider(
    "Average Daily Incoming UPI (₹)",
    300,
    5000,
    daily_income,
    100
)

uploaded = st.sidebar.file_uploader(
    "Upload Transaction CSV",
    type=["csv"]
)

st.sidebar.markdown("---")

st.sidebar.caption(
    "Expected CSV columns: date, type, amount. "
    "Optional columns: mode, description."
)

# =====================================================
# MAIN NAVIGATION
# =====================================================

tab1, tab2, tab3, tab4 = st.tabs([
    "🏁 Applicant Journey",
    "📊 Cash-flow Insights",
    "💰 Loan Offer",
    "🧭 How It Works"
])

# =====================================================
# TAB 1: APPLICANT JOURNEY
# =====================================================

with tab1:

    st.subheader("1. Consent & Applicant Details")

    left, right = st.columns([1.2, 1])

    with left:

        name = st.text_input(
            "Applicant Name",
            "Ravi Kumar"
        )

        occupation = st.selectbox(
            "Occupation",
            [
                "Street vendor",
                "Delivery partner",
                "Kirana shop owner",
                "Auto driver",
                "Freelancer"
            ]
        )

        city = st.text_input(
            "City",
            "Hyderabad"
        )

        consent = st.checkbox(
            "I give permission to analyse my simulated UPI transaction data for this demo."
        )

        st.session_state.consent = consent

        st.info(
            "Privacy-first demo: No bank account is connected. "
            "Transactions are synthetic or uploaded by you."
        )

    with right:

        st.markdown("### Applicant Snapshot")

        st.write(f"**Name:** {name or '—'}")

        st.write(f"**Work:** {occupation}")

        st.write(f"**Location:** {city}")

        st.success("Prototype Environment")

        st.write("**Data Source**")

        st.write(
            "UPI transaction simulation / uploaded CSV"
        )

    # Prepare transaction data

    valid_data = True

    if uploaded is not None:

        try:

            df = prepare_csv(uploaded)

            st.success(
                f"CSV uploaded successfully: {len(df)} transactions."
            )

        except Exception as e:

            st.error(str(e))

            valid_data = False

            df = None

    else:

        df = make_demo_data(
            months,
            daily_income,
            expense_ratio,
            volatility
        )

    # ANALYSIS BUTTON

    if st.button(
        "🔍 Analyse Cash Flow & Generate CreditLens Score",
        type="primary",
        disabled=(not consent or not valid_data)
    ):

        st.session_state.analysed = True

        st.session_state.applicant = name

        st.session_state.occupation = occupation

        st.session_state.city = city

        st.session_state.transactions = df.copy()

        st.session_state.offer_generated = False

        st.success(
            "Analysis complete! Your CreditLens score is ready."
        )

    if not consent:

        st.caption(
            "Tick the consent checkbox to enable analysis."
        )

    # DISPLAY CREDIT SCORE

    if (
        st.session_state.analysed
        and st.session_state.transactions is not None
    ):

        st.markdown("---")

        st.subheader("2. CreditLens Result")

        (
            score,
            credits,
            debits,
            income_by_month,
            stability,
            net_ratio,
            credit_count
        ) = calculate_score(
            st.session_state.transactions
        )

        if score >= 760:
            band = "Excellent"

        elif score >= 680:
            band = "Good"

        elif score >= 580:
            band = "Fair"

        else:
            band = "Needs Improvement"

        a, b, c, d = st.columns(4)

        a.metric(
            "CreditLens Score",
            f"{score}/900",
            band
        )

        b.metric(
            "Total Incoming",
            money(credits)
        )

        c.metric(
            "Total Outgoing",
            money(debits)
        )

        d.metric(
            "Income Transactions",
            f"{credit_count:,}"
        )

        st.progress(
            score / 900,
            text=f"{band} Profile – Simulated Score"
        )

        st.caption(
            "This is a simulated prototype score, "
            "not a credit bureau score or real lending decision."
        )


# =====================================================
# TAB 2: CASH-FLOW INSIGHTS
# =====================================================

with tab2:

    st.subheader("📊 Cash-flow Insights")

    if not st.session_state.analysed:

        st.info(
            "Complete applicant consent and cash-flow analysis first."
        )

    else:

        df = st.session_state.transactions.copy()

        (
            score,
            credits,
            debits,
            monthly_income,
            stability,
            net_ratio,
            credit_count
        ) = calculate_score(df)

        df["date"] = pd.to_datetime(df["date"])

        df["month"] = (
            df["date"].dt.to_period("M").astype(str)
        )

        m = (
            df[
                df["type"].isin(["CREDIT", "INCOME"])
            ]
            .groupby("month", as_index=False)["amount"]
            .sum()
        )

        m = m.rename(
            columns={"amount": "Incoming UPI"}
        )

        st.plotly_chart(
            px.bar(
                m,
                x="month",
                y="Incoming UPI",
                title="Monthly Incoming UPI Payments",
                color_discrete_sequence=["#168aad"]
            ),
            use_container_width=True
        )

        x, y = st.columns(2)

        with x:

            st.metric(
                "Income Stability",
                f"{stability * 100:.0f}%"
            )

            st.progress(
                float(np.clip(stability, 0, 1))
            )

            st.caption(
                "Measures consistency of monthly incoming payments."
            )

        with y:

            st.metric(
                "Net Cash-flow Ratio",
                f"{net_ratio * 100:.0f}%"
            )

            st.progress(
                float(np.clip(net_ratio, 0, 1))
            )

            st.caption(
                "Share of incoming cash remaining after expenses."
            )

        st.markdown("### Explainable Score Factors")

        factors = pd.DataFrame([
            [
                "Income Stability",
                round(stability * 100),
                "Monthly income consistency"
            ],
            [
                "Net Cash Flow",
                round(net_ratio * 100),
                "Incoming minus outgoing"
            ],
            [
                "Transaction Frequency",
                min(100, round(credit_count)),
                "Regular earning activity"
            ],
            [
                "History Length",
                min(
                    100,
                    round(len(monthly_income) / 6 * 100)
                ),
                "Months of observed activity"
            ]
        ], columns=[
            "Factor",
            "Indicator",
            "Meaning"
        ])

        st.dataframe(
            factors,
            hide_index=True,
            use_container_width=True
        )

        st.info(
            "CreditLens rewards regular earning activity, "
            "stable monthly cash flow and a positive balance after expenses."
        )


# =====================================================
# TAB 3: LOGIN AND LOAN OFFER
# =====================================================


with tab3:

    st.subheader("💳 CreditLens Account")

    if not st.session_state.loan_authenticated:

        login_tab, signup_tab = st.tabs([
            "🔐 Login",
            "📝 Sign Up"
        ])

        # LOGIN
        with login_tab:

            st.subheader("Welcome Back!")

            with st.form("login_form"):

                email = st.text_input("Email Address")
                password = st.text_input(
                    "Password",
                    type="password"
                )

                login_button = st.form_submit_button(
                    "Login",
                    type="primary"
                )

            if login_button:

                user = verify_user(email, password)

                if user:

                    st.session_state.loan_authenticated = True
                    st.session_state.logged_user = user[0]

                    st.success("Login successful!")
                    st.rerun()

                else:
                    st.error("Invalid email or password.")

        # SIGN UP
        with signup_tab:

            st.subheader("Create Your Account")

            with st.form("signup_form"):

                new_name = st.text_input("Full Name")
                new_email = st.text_input("Email Address")

                new_password = st.text_input(
                    "Create Password",
                    type="password"
                )

                confirm_password = st.text_input(
                    "Confirm Password",
                    type="password"
                )

                signup_button = st.form_submit_button(
                    "Create Account",
                    type="primary"
                )

            if signup_button:

                if not all([
                    new_name.strip(),
                    new_email.strip(),
                    new_password,
                    confirm_password
                ]):
                    st.error("Please fill in all fields.")

                elif "@" not in new_email or "." not in new_email:
                    st.error("Enter a valid email address.")

                elif len(new_password) < 8:
                    st.error("Password must contain at least 8 characters.")

                elif new_password != confirm_password:
                    st.error("Passwords do not match.")

                else:

                    success = register_user(
                        new_name.strip(),
                        new_email.strip().lower(),
                        new_password
                    )

                    if success:
                        st.success(
                            "Account created successfully! "
                            "Please go to Login."
                        )
                    else:
                        st.error(
                            "This email is already registered."
                        )

    else:

        st.success(
            f"Welcome, {st.session_state.get('logged_user', 'User')}!"
        )

        if st.button("Logout"):

            st.session_state.loan_authenticated = False
            st.session_state.logged_user = ""
            st.rerun()

        if not st.session_state.analysed:

            st.warning(
                "Please complete cash-flow analysis first."
            )

        else:

            score, credits, debits, monthly_income, stability, net_ratio, credit_count = calculate_score(
                st.session_state.transactions
            )

            avg_monthly_income = (
                credits / max(1, len(monthly_income))
            )

            max_loan = int(np.clip(
                avg_monthly_income * (0.35 + score / 1800),
                3000,
                100000
            ))

            rate = (
                12.0 if score >= 760
                else 15.0 if score >= 680
                else 18.0 if score >= 580
                else 22.0
            )

            st.subheader("🎉 Your Loan Offer")

            st.metric("Eligible Loan", money(max_loan))
            st.metric("Interest Rate", f"{rate:.1f}%")

            amount = st.slider(
                "Choose Loan Amount",
                1000,
                max(1000, max_loan),
                min(max_loan, int(max_loan * 0.7)),
                500
            )

            tenure = st.select_slider(
                "Repayment Period",
                options=[3, 6, 9, 12],
                value=6
            )

            monthly_rate = rate / 1200

            emi = (
                amount * monthly_rate
                * (1 + monthly_rate)**tenure
                / ((1 + monthly_rate)**tenure - 1)
                if monthly_rate else amount / tenure
            )

            st.metric("Monthly EMI", money(emi))
            st.metric("Total Repayment", money(emi * tenure))

            st.success("Demo Loan Offer Generated!")



# =====================================================
# TAB 4: HOW IT WORKS
# =====================================================

with tab4:

    st.subheader(
        "🧭 CreditLens Architecture – Prototype"
    )

    steps = [

        (
            "1. Consent",
            "Applicant approves the use of transaction data."
        ),

        (
            "2. Analyse",
            "Clean and aggregate incoming and outgoing transactions."
        ),

        (
            "3. Score",
            "Cash-flow indicators generate an explainable 300–900 score."
        ),

        (
            "4. Loan Offer",
            "A simulated lender estimates the loan amount, interest and EMI."
        ),

        (
            "5. Repayment",
            "Repayment reminders and positive repayment history can support future assessment."
        )

    ]

    for title, description in steps:

        st.markdown(f"### {title}")

        st.write(description)

        st.divider()

    st.warning(
        "Hackathon prototype: This application uses synthetic data "
        "and transparent rule-based scoring. It does not connect to "
        "UPI, bank accounts, credit bureaus or real lenders."
    )


# =====================================================
# FOOTER
# =====================================================

st.markdown("---")

st.caption(
    "💳 CreditLens Hackathon Demo | "
    "Synthetic Data Only | "
    "No Real Financial Product or Loan Approval"
)