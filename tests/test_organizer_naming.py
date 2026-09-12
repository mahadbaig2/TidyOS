"""Regression tests for Organizer Agent semantic filename synthesis."""

from pathlib import Path
import pytest

from tidyos.agents.librarian import FileUnderstanding
from tidyos.agents.organizer import OrganizerAgent, _extract_date_snippet


def test_extract_date_snippet():
    assert _extract_date_snippet("September 2026 hosting invoice") == "September_2026"
    assert _extract_date_snippet("Invoice dated Sep 2026") == "September_2026"
    assert _extract_date_snippet("Quarterly report 2026-09-12") == "2026_09_12"
    assert _extract_date_snippet("Summary for FY 2026") == "2026"
    assert _extract_date_snippet("No dates here") == ""


def test_generic_invoice_synthesizes_semantic_filename():
    """Critical Hackathon Demo Regression Test:
    document (17).pdf + Vercel September 2026 invoice semantics
    MUST NOT result in Document_(17).pdf.
    """
    organizer = OrganizerAgent()

    # Scenario A: Title contains rich metadata
    understanding_a = FileUnderstanding(
        file_path="Downloads/document (17).pdf",
        sha256_hash="dummy1",
        document_type="invoice",
        title="Vercel Invoice September 2026",
        entities=["Vercel"],
        topics=["billing", "hosting"],
        summary="Hosting invoice from Vercel for September 2026",
        confidence=0.94,
    )
    proposal_a = organizer.propose("Downloads/document (17).pdf", understanding=understanding_a)
    assert proposal_a.proposed_filename == "Vercel_Invoice_September_2026.pdf"
    assert proposal_a.proposed_filename != "Document_(17).pdf"
    assert proposal_a.proposed_filename != "document (17).pdf"

    # Scenario B: Title was generic ("Document (17)"), but entities + summary have semantics
    understanding_b = FileUnderstanding(
        file_path="Downloads/document (17).pdf",
        sha256_hash="dummy2",
        document_type="invoice",
        title="Document (17)",
        entities=["Vercel Inc."],
        topics=["billing"],
        summary="September 2026 monthly subscription fee.",
        confidence=0.92,
    )
    proposal_b = organizer.propose("Downloads/document (17).pdf", understanding=understanding_b)
    assert proposal_b.proposed_filename == "Vercel_Invoice_September_2026.pdf"
    assert proposal_b.proposed_filename != "Document_(17).pdf"


def test_resume_synthesizes_semantic_filename():
    organizer = OrganizerAgent()
    understanding = FileUnderstanding(
        file_path="Downloads/resume_final_3.pdf",
        sha256_hash="dummy3",
        document_type="resume",
        title="Resume Final 3",
        entities=["Alex Chen"],
        topics=["AI Product Engineering"],
        summary="Resume for AI Product Engineering role",
        confidence=0.90,
    )
    proposal = organizer.propose("Downloads/resume_final_3.pdf", understanding=understanding)
    assert "Alex_Chen" in proposal.proposed_filename or "Ai_Product_Engineering" in proposal.proposed_filename
    assert "Resume" in proposal.proposed_filename
    assert proposal.proposed_filename.endswith(".pdf")
    assert proposal.proposed_filename != "Resume_Final_3.pdf"


def test_descriptive_filename_is_preserved_safely():
    organizer = OrganizerAgent()
    understanding = FileUnderstanding(
        file_path="Documents/quarterly_financial_report_q3.pdf",
        sha256_hash="dummy4",
        document_type="report",
        title="Quarterly Report",
        confidence=0.85,
    )
    proposal = organizer.propose("Documents/quarterly_financial_report_q3.pdf", understanding=understanding)
    assert proposal.proposed_filename == "quarterly_financial_report_q3.pdf"
