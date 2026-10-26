"""
core/knowledge.py
Curated financial knowledge base for RAG and agent grounding.
Provides authoritative domain concepts on budgeting, tax, investments, and debt.
"""

FINANCIAL_KNOWLEDGE_BASE = {
    "50_30_20_rule": {
        "title": "50/30/20 Budgeting Framework",
        "content": (
            "The 50/30/20 rule divides net after-tax income into 3 buckets: "
            "1. 50% for Needs: rent, groceries, utilities, basic transportation, minimum debt payments. "
            "2. 30% for Wants: dining out, streaming, travel, hobbies, entertainment. "
            "3. 20% for Savings & Debt Paydown: emergency fund, retirement (PPF/NPS/401k), mutual fund SIPs, "
            "extra debt payments. If needs exceed 50%, reduce wants before cutting savings."
        )
    },
    "emergency_fund": {
        "title": "Emergency Fund Strategy",
        "content": (
            "An emergency fund should cover 3 to 6 months of essential living expenses (rent, groceries, EMIs, utilities). "
            "Keep it in high-liquidity instruments: high-yield savings accounts or liquid mutual funds, never locked in stocks "
            "or illiquid real estate. Target: ₹1,50,000 to ₹3,00,000 depending on monthly baseline burn."
        )
    },
    "sip_investing": {
        "title": "Systematic Investment Plan (SIP) & Rupee Cost Averaging",
        "content": (
            "A SIP invests a fixed amount monthly into diversified equity/index mutual funds (e.g. Nifty 50 or S&P 500). "
            "Benefits: 1. Rupee-cost averaging buys more units when markets drop and fewer when high. "
            "2. Eliminates market timing stress. Historically, 10-15 year equity index SIPs have compounded at 11-13% CAGR."
        )
    },
    "debt_reduction": {
        "title": "Debt Avalanche vs Snowball Strategy",
        "content": (
            "1. Avalanche method: Pay minimum on all debts, throw all extra funds at the loan with highest interest rate "
            "(e.g. credit cards at 36-42% APR). Mathematically optimal, saves the most interest. "
            "2. Snowball method: Pay off smallest balance first for psychological quick wins. Recommended if motivation is the bottleneck."
        )
    },
    "tax_saving": {
        "title": "Tax Optimization & Section 80C Deductions",
        "content": (
            "Under Indian tax regimes: "
            "1. Section 80C allows deductions up to ₹1.5 Lakh via ELSS mutual funds (3-year lock-in), PPF (15-year safe return), EPF, and term life insurance. "
            "2. Section 80CCD(1B) offers additional ₹50,000 deduction for National Pension System (NPS). "
            "3. Health insurance premium gives up to ₹25,000 to ₹50,000 deduction under Section 80D."
        )
    },
    "compound_interest": {
        "title": "The Power of Compounding & Inflation",
        "content": (
            "Compounding formula: A = P * (1 + r/n)^(nt). For monthly SIPs: FV = P * [((1 + i)^n - 1) / i] * (1 + i). "
            "Inflation (typically 5-7% in India) erodes purchasing power. A ₹10,000 expense today will require ~₹20,000 in 10-12 years. "
            "Savings kept purely in cash lose real value over time; equity allocation is crucial to beat inflation."
        )
    }
}


def search_knowledge(query: str) -> str:
    """Keyword / topic-based retrieval from financial knowledge base."""
    query_lower = query.lower()
    matches = []
    for key, item in FINANCIAL_KNOWLEDGE_BASE.items():
        title = item["title"].lower()
        content = item["content"].lower()
        if any(term in title or term in content for term in query_lower.split()):
            matches.append(f"### {item['title']}\n{item['content']}")

    if not matches:
        # Default to 50/30/20 and emergency fund
        return f"### {FINANCIAL_KNOWLEDGE_BASE['50_30_20_rule']['title']}\n{FINANCIAL_KNOWLEDGE_BASE['50_30_20_rule']['content']}"

    return "\n\n".join(matches[:2])
