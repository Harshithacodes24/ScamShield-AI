# =========================================================
# OCR CONFIGURATION (KEEP AT TOP)
# =========================================================
import os
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
os.environ["TESSDATA_PREFIX"] = r"C:\Program Files\Tesseract-OCR\tessdata"

# =========================================================
# IMPORTS
# =========================================================
import streamlit as st
import pandas as pd
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image, ImageOps
from datetime import datetime

# =========================================================
# PAGE CONFIG
# =========================================================
st.set_page_config(page_title="ScamShield AI", page_icon="🛡️", layout="wide")

# =========================================================
# STYLING
# =========================================================
st.markdown("""
<style>
.main-title { font-size:42px; font-weight:800; color:#1f4e79; }
.subtitle { font-size:18px; color:#555; margin-bottom:25px; }
.stButton>button {
    background-color:#1f4e79;
    color:white;
    border-radius:8px;
    padding:10px 20px;
    font-weight:600;
}
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-title">🛡 ScamShield AI</div>', unsafe_allow_html=True)
st.markdown('<div class="subtitle">Hybrid Explainable Fraud Detection & Awareness Assistant</div>', unsafe_allow_html=True)

# =========================================================
# LOAD & TRAIN MODEL (KAGGLE DATASET)
# =========================================================
@st.cache_resource
def load_and_train():

    df = pd.read_csv("spam.csv", encoding="latin-1")
    df = df[["v1", "v2"]]
    df.columns = ["label", "text"]

    df["label"] = df["label"].map({
        "spam": "fraud",
        "ham": "legit"
    })

    df = df.dropna()

    vectorizer = TfidfVectorizer(stop_words="english", max_features=5000)
    X = vectorizer.fit_transform(df["text"])
    y = df["label"]

    model = MultinomialNB()
    model.fit(X, y)

    return model, vectorizer

model, vectorizer = load_and_train()

# =========================================================
# RISK ENGINE
# =========================================================
def compute_risk(message):

    text = message.lower()
    factors = {}
    highlighted_text = message

    def highlight(word):
        nonlocal highlighted_text
        highlighted_text = re.sub(
            word,
            f"<span style='background-color:#ffcccc;padding:4px;border-radius:5px'>{word}</span>",
            highlighted_text,
            flags=re.IGNORECASE
        )

    # Rule Signals
    if "registration fee" in text or "processing fee" in text:
        factors["Payment Request"] = 30
        highlight("registration fee")
        highlight("processing fee")

    if "otp" in text and ("send" in text or "share" in text):
        factors["OTP Collection Attempt"] = 30
        highlight("otp")

    if "whatsapp" in text:
        factors["Unofficial WhatsApp Contact"] = 20
        highlight("whatsapp")

    if "http" in text or ".com" in text:
        factors["Suspicious Link"] = 20
        highlight("http")

    if "urgent" in text or "immediately" in text:
        factors["Urgency Pressure"] = 15
        highlight("urgent")
        highlight("immediately")

    if "no interview" in text:
        factors["No Interview Claim"] = 15
        highlight("no interview")

    if ("won" in text or 
        "congratulations" in text or 
        "cash prize" in text or 
        "claim now" in text):
        factors["Lottery / Prize Scam Language"] = 25
        highlight("won")
        highlight("congratulations")
        highlight("cash prize")

    # ML Contribution
    vec = vectorizer.transform([message])
    prob = model.predict_proba(vec)[0]
    fraud_index = list(model.classes_).index("fraud")
    ml_prob = prob[fraud_index]

    factors["ML Pattern Probability"] = round(ml_prob * 30, 2)

    total_score = sum(factors.values())
    risk_percent = min(total_score, 100)

    return risk_percent, factors, highlighted_text

# =========================================================
# CLASSIFICATION
# =========================================================
def classify_scam_type(message, factors):

    text = message.lower()

    if "otp" in text:
        return "OTP Phishing"

    if "registration fee" in text:
        return "Job Scam (Advance Fee)"

    if "salary" in text and "whatsapp" in text:
        return "Job Scam (WhatsApp Recruitment)"

    if "won" in text or "cash prize" in text:
        return "Lottery / Prize Scam"

    if "http" in text:
        return "Link-Based Phishing"

    if factors:
        return "Suspicious Pattern"

    return "No Clear Scam Category"

# =========================================================
# SESSION STATE
# =========================================================
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello 👋 I am ScamShield AI. Paste a suspicious message to analyze it."}
    ]

if "history" not in st.session_state:
    st.session_state.history = []

# =========================================================
# TABS
# =========================================================
tab1, tab2 = st.tabs(["💬 Chat Assistant", "📊 Analytics Dashboard"])

# =========================================================
# TAB 1 – CHAT
# =========================================================
with tab1:

    if st.button("Clear Chat"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Chat cleared. Start new analysis."}
        ]
        st.session_state.history = []
        st.rerun()

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"], unsafe_allow_html=True)

    user_input = st.chat_input("Type suspicious message...")

    if user_input:

        st.session_state.messages.append({"role": "user", "content": user_input})

        # Compute risk
        risk_percent, factors, highlighted = compute_risk(user_input)
        scam_type = classify_scam_type(user_input, factors)

        # Risk Level
        if risk_percent >= 70:
            level = "⚠️ HIGH RISK"
        elif risk_percent >= 40:
            level = "⚠️ MODERATE RISK"
        else:
            level = "🟢 LOW RISK"

        # -------------------------
        # DETAILED REASONING ENGINE
        # -------------------------

        reasoning = []
        education = []
        advice_points = []

        if "Payment Request" in factors:
            reasoning.append("The message asks for money before providing a service.")
            education.append("Advance-fee scams create fake opportunities and request deposits.")
            advice_points.append("Do not send money or share payment details.")

        if "OTP Collection Attempt" in factors:
            reasoning.append("The message attempts to collect your OTP.")
            education.append("Sharing OTP gives attackers access to your account.")
            advice_points.append("Never share OTP with anyone.")

        if "Suspicious Link" in factors:
            reasoning.append("The message includes an external link.")
            education.append("Phishing links redirect to fake websites that steal credentials.")
            advice_points.append("Do not click unknown links.")

        if "Lottery / Prize Scam Language" in factors:
            reasoning.append("The message promises unexpected rewards.")
            education.append("Scammers use prize claims to create excitement.")
            advice_points.append("Ignore prize claims you did not enter for.")

        if "Urgency Pressure" in factors:
            reasoning.append("The message creates urgency to pressure quick action.")
            education.append("Urgency reduces rational thinking.")
            advice_points.append("Take time to verify before responding.")

        if not reasoning:
            reasoning.append("No strong scam indicators detected.")
            advice_points.append("Stay cautious and verify unknown communications.")

        # Decision explanation
        if risk_percent >= 70:
            decision_explanation = "Multiple scam patterns were detected. The message strongly matches known fraud behavior."
        elif risk_percent >= 40:
            decision_explanation = "Some suspicious elements were found. The message shares similarities with scam patterns."
        else:
            decision_explanation = "No strong scam patterns were detected, but caution is still advised."

        reasoning_text = "\n".join([f"- {r}" for r in reasoning])
        education_text = "\n".join([f"- {e}" for e in education])
        advice_text = "\n".join([f"- {a}" for a in advice_points])

        response = f"""
## {level}

### 📌 Scam Category
**{scam_type}**

### 🔍 Why This Decision Was Made
{decision_explanation}

### 🧠 Risk Indicators Identified
{reasoning_text}

### 📚 How This Scam Works
{education_text}

### 🛡 Recommended Actions
{advice_text}

---

### 📄 Message Reviewed
{highlighted}
"""

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        st.session_state.history.append({
            "timestamp": datetime.now(),
            "risk": risk_percent,
            "category": scam_type,
            "factors": factors
        })

        st.rerun()
# -----------------------------
# IMAGE UPLOAD SECTION (SMART VERSION)
# -----------------------------
st.markdown("### 📷 Upload Screenshot for Analysis")

uploaded_file = st.file_uploader(
    "Upload Screenshot (Optional)",
    type=["png", "jpg", "jpeg"],
    key="image_upload"
)

if uploaded_file is not None:

    image = Image.open(uploaded_file)

    if image.mode != "RGB":
        image = image.convert("RGB")

    image = ImageOps.grayscale(image)

    st.image(image, use_column_width=True)

    raw_text = pytesseract.image_to_string(image)

    # ---- Clean OCR Output ----
    lines = raw_text.split("\n")
    cleaned_lines = []

    for line in lines:
        line = line.strip()
        if line and line not in cleaned_lines:
            cleaned_lines.append(line)

    cleaned_text = " ".join(cleaned_lines)

    st.markdown("### 📝 Extracted Text (Editable)")
    editable_text = st.text_area(
        "You can edit before analysis:",
        value=cleaned_text,
        height=150
    )

    if st.button("Analyze Extracted Text"):

        st.session_state.messages.append({
            "role": "user",
            "content": editable_text
        })

        risk_percent, factors, highlighted = compute_risk(editable_text)
        scam_type = classify_scam_type(editable_text, factors)

        if risk_percent >= 70:
            level = "⚠️ HIGH RISK"
        elif risk_percent >= 40:
            level = "⚠️ MODERATE RISK"
        else:
            level = "🟢 LOW RISK"

        # Decision explanation
        if risk_percent >= 70:
            decision_explanation = "Multiple scam indicators were detected. This strongly matches known fraud behavior."
        elif risk_percent >= 40:
            decision_explanation = "Some suspicious elements were found. The message shares similarities with scam patterns."
        else:
            decision_explanation = "No strong scam patterns were detected, but caution is advised."

        reasoning = []
        education = []
        advice = []

        if "Suspicious Link" in factors:
            reasoning.append("The message contains an external link.")
            education.append("Phishing links redirect to fake login pages.")
            advice.append("Avoid clicking unknown links.")

        if "Lottery / Prize Scam Language" in factors:
            reasoning.append("The message promises unexpected rewards.")
            education.append("Scammers use prize claims to create excitement.")
            advice.append("Ignore prize claims you did not enter.")

        if "Unofficial WhatsApp Contact" in factors:
            reasoning.append("The message redirects to WhatsApp contact.")
            education.append("Legitimate recruiters usually use official email domains.")
            advice.append("Verify using official company website.")

        if not reasoning:
            reasoning.append("No strong scam indicators detected.")
            advice.append("Stay cautious and verify unknown communications.")

        reasoning_text = "\n".join([f"- {r}" for r in reasoning])
        education_text = "\n".join([f"- {e}" for e in education])
        advice_text = "\n".join([f"- {a}" for a in advice])

        response = f"""
## {level}

### 📌 Scam Category
**{scam_type}**

### 🔍 Why This Decision Was Made
{decision_explanation}

### 🧠 Risk Indicators
{reasoning_text}

### 📚 Scam Awareness Insight
{education_text}

### 🛡 Recommended Action
{advice_text}

---

### 📄 Message Reviewed
{highlighted}
"""

        st.session_state.messages.append({
            "role": "assistant",
            "content": response
        })

        st.session_state.history.append({
            "timestamp": datetime.now(),
            "risk": risk_percent,
            "category": scam_type,
            "factors": factors
        })

        st.rerun()
# =========================================================
# TAB 2 – DASHBOARD
# =========================================================
with tab2:

    st.header("📊 Fraud Risk Analytics Dashboard")

    if st.session_state.history:

        df_hist = pd.DataFrame(st.session_state.history)
        latest = df_hist.iloc[-1]

        col1, col2 = st.columns(2)

        with col1:
            gauge = go.Figure(go.Indicator(
                mode="gauge+number",
                value=latest["risk"],
                title={'text': "Latest Risk Score"},
                gauge={
                    'axis': {'range': [0, 100]},
                    'steps': [
                        {'range': [0, 40], 'color': "green"},
                        {'range': [40, 70], 'color': "yellow"},
                        {'range': [70, 100], 'color': "red"}
                    ],
                }
            ))
            st.plotly_chart(gauge, use_container_width=True)

        with col2:
            if latest["factors"]:
                factor_df = pd.DataFrame({
                    "Factor": list(latest["factors"].keys()),
                    "Contribution": list(latest["factors"].values())
                })
                fig = px.bar(factor_df,
                             x="Contribution",
                             y="Factor",
                             orientation="h",
                             text="Contribution",
                             title="Risk Contribution")
                st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No analyses performed yet.")