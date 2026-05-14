"""Seed the local DB with demo data so the UI has something to show."""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app.local_db import LocalClient
from datetime import datetime, timezone

client = LocalClient()
now = datetime.now(timezone.utc).isoformat()

# ── Demo project 1 ─────────────────────────────────────────────────────────
p1_id = "demo-project-financial"
client.table("projects").upsert({
    "id": p1_id,
    "user_id": "local",
    "name": "Financial Report Analysis",
    "description": "Q&A dataset generated from quarterly financial reports. Demonstrates the full document-to-dataset pipeline.",
    "instruction": "Extract Q&A pairs about financial figures, risk factors, and key metrics.",
    "status": "completed",
    "schema_config": {
        "mode": "qa",
        "schema": {
            "generated_schema": [
                {"key": "question", "type": "string", "required": True, "description": "Question about the financial document"},
                {"key": "answer", "type": "string", "required": True, "description": "Answer grounded in the document"},
                {"key": "context", "type": "string", "required": True, "description": "Source passage from the document"},
                {"key": "topic", "type": "string", "required": False, "description": "Topic category"},
                {"key": "difficulty", "type": "string", "required": False, "description": "Difficulty level"},
                {"key": "question_type", "type": "string", "required": False, "description": "Type of question"},
                {"key": "keywords", "type": "string", "required": False, "description": "Comma-separated keywords"},
                {"key": "explanation", "type": "string", "required": False, "description": "Explanation of the answer"},
            ]
        },
        "instruction": "Extract Q&A pairs about financial figures, risk factors, and key metrics.",
        "generated_from_files": 2,
        "generated_at": now,
    },
    "total_pages_processed": 24,
    "processing_time_seconds": 45,
    "created_at": now,
    "updated_at": now,
}).execute()

# ── Demo documents for project 1 ──────────────────────────────────────────
client.table("documents").upsert({
    "id": "demo-doc-q3-report",
    "project_id": p1_id,
    "filename": "Q3_2025_Financial_Report.pdf",
    "file_path": "demo/q3_report.pdf",
    "file_size": 2_500_000,
    "file_type": ".pdf",
    "pages_extracted": 18,
    "page_count": 18,
    "status": "completed",
    "created_at": now,
    "updated_at": now,
}).execute()

client.table("documents").upsert({
    "id": "demo-doc-risk-factors",
    "project_id": p1_id,
    "filename": "Risk_Factors_Summary.docx",
    "file_path": "demo/risk_factors.docx",
    "file_size": 1_800_000,
    "file_type": ".docx",
    "pages_extracted": 6,
    "page_count": 6,
    "status": "completed",
    "created_at": now,
    "updated_at": now,
}).execute()

# ── Demo dataset for project 1 ────────────────────────────────────────────
sample_records = [
    {
        "question": "What was the total revenue reported in Q3 2025?",
        "answer": "The total revenue in Q3 2025 was $4.2 billion, representing a 12% year-over-year increase.",
        "context": "In the third quarter of 2025, the company reported total revenue of $4.2 billion, up 12% compared to $3.75 billion in Q3 2024.",
        "topic": "revenue",
        "difficulty": "basic",
        "question_type": "theoretical",
        "keywords": "revenue, Q3, 2025, growth",
        "explanation": "The revenue figure is directly stated in the financial summary section."
    },
    {
        "question": "What are the primary risk factors identified in the report?",
        "answer": "The primary risk factors include market volatility, regulatory changes in key markets, and supply chain disruptions affecting production timelines.",
        "context": "Key risks identified include: (1) market volatility driven by macroeconomic uncertainty, (2) evolving regulatory frameworks in APAC and EU markets, and (3) ongoing supply chain constraints.",
        "topic": "risk management",
        "difficulty": "intermediate",
        "question_type": "practical",
        "keywords": "risk, volatility, regulation, supply chain",
        "explanation": "Risk factors are enumerated in Section 3 of the Risk Factors Summary."
    },
    {
        "question": "How did the operating margin change compared to the previous quarter?",
        "answer": "The operating margin improved from 18.3% in Q2 to 21.7% in Q3, a 3.4 percentage point increase driven by cost optimization initiatives.",
        "context": "Operating margin expanded to 21.7% in Q3 2025 (Q2 2025: 18.3%), reflecting the benefits of the cost optimization program launched in January.",
        "topic": "profitability",
        "difficulty": "intermediate",
        "question_type": "application",
        "keywords": "operating margin, profitability, cost optimization",
        "explanation": "The margin improvement is attributed to the cost optimization program mentioned earlier in the report."
    },
    {
        "question": "What is the company's debt-to-equity ratio?",
        "answer": "The debt-to-equity ratio stands at 0.45, within the target range of 0.3–0.6 set by the board.",
        "context": "As of September 30, 2025, the debt-to-equity ratio was 0.45x, comfortably within the board-approved target corridor of 0.3–0.6x.",
        "topic": "balance sheet",
        "difficulty": "basic",
        "question_type": "theoretical",
        "keywords": "debt, equity, leverage, balance sheet",
        "explanation": "The ratio is reported in the balance sheet highlights section."
    },
    {
        "question": "What capital expenditure is planned for the next fiscal year?",
        "answer": "The company plans $800 million in capital expenditure for FY2026, focused on technology infrastructure and manufacturing capacity expansion.",
        "context": "Management has approved a capex budget of $800M for FY2026, with approximately 60% allocated to technology upgrades and 40% to manufacturing expansion in the Asia-Pacific region.",
        "topic": "capital expenditure",
        "difficulty": "advanced",
        "question_type": "practical",
        "keywords": "capex, investment, technology, manufacturing",
        "explanation": "The capex plan details are in the forward-looking statements section."
    },
]

client.table("datasets").upsert({
    "id": "demo-dataset-financial",
    "project_id": p1_id,
    "data": sample_records,
    "schema_used": [
        {"key": "question", "type": "string"},
        {"key": "answer", "type": "string"},
        {"key": "context", "type": "string"},
        {"key": "topic", "type": "string"},
        {"key": "difficulty", "type": "string"},
        {"key": "question_type", "type": "string"},
        {"key": "keywords", "type": "string"},
        {"key": "explanation", "type": "string"},
    ],
    "status": "completed",
    "total_records": len(sample_records),
    "created_at": now,
    "updated_at": now,
}).execute()

# ── Demo project 2 (empty — ready for user to try) ────────────────────────
client.table("projects").upsert({
    "id": "demo-project-empty",
    "user_id": "local",
    "name": "Product Documentation (Try Me!)",
    "description": "Upload your own documents here to generate a training dataset. Start by clicking 'Open Project'.",
    "status": "created",
    "total_pages_processed": 0,
    "processing_time_seconds": 0,
    "created_at": now,
    "updated_at": now,
}).execute()

print("Seed data inserted successfully!")
print(f"   - 2 projects (1 completed with dataset, 1 empty)")
print(f"   - 2 documents")
print(f"   - {len(sample_records)} Q&A records")
