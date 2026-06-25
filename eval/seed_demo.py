#!/usr/bin/env python3
"""
Seed the demo dataset for HealthSignal.

Creates a demo user (Maya Cohen) and uploads all 7 synthetic health documents.
Safe to run multiple times — duplicate files are skipped gracefully.

Usage:
    python eval/seed_demo.py
    python eval/seed_demo.py --backend http://localhost:8000
"""

import argparse
import sys
import time
from pathlib import Path

import httpx

DEMO_EMAIL = "maya@demo.healthsignal"
DEMO_PASSWORD = "DemoMaya2024!"
DEMO_NAME = "Maya Cohen"

# Documents to upload: (filename, document_type, source_date)
DOCUMENTS = [
    ("demo_labs_feb_2024.txt",      "blood_test",      "2024-02-08"),
    ("demo_labs_jun_2024.txt",      "blood_test",      "2024-06-20"),
    ("demo_labs_nov_2024.txt",      "blood_test",      "2024-11-14"),
    ("demo_symptoms_q1_2024.txt",   "symptom_note",    "2024-01-08"),
    ("demo_symptoms_q3_2024.txt",   "symptom_note",    "2024-07-03"),
    ("demo_supplements_2024.txt",   "supplement_list", "2024-02-25"),
    ("demo_lifestyle_2024.txt",     "journal",         "2024-04-08"),
]

DATA_DIR = Path(__file__).parent / "tests" / "001" / "data"


def get_token(backend: str) -> str:
    """Register or login the demo user and return a JWT."""
    with httpx.Client(base_url=backend, timeout=15.0) as client:
        # Try register first
        resp = client.post("/auth/register", json={
            "email": DEMO_EMAIL,
            "password": DEMO_PASSWORD,
        })
        if resp.status_code == 201:
            print(f"✓ Demo user registered: {DEMO_EMAIL}")
            return resp.json()["access_token"]

        if resp.status_code == 409:
            # Already exists — login instead
            resp = client.post("/auth/login", json={
                "email": DEMO_EMAIL,
                "password": DEMO_PASSWORD,
            })
            resp.raise_for_status()
            print(f"✓ Demo user logged in: {DEMO_EMAIL}")
            return resp.json()["access_token"]

        # Unexpected error
        resp.raise_for_status()
        return ""  # unreachable


def upload_document(
    client: httpx.Client,
    token: str,
    filename: str,
    document_type: str,
    source_date: str,
) -> str | None:
    """
    Upload a single document. Returns the document_id on success,
    None if skipped (duplicate), raises on other errors.
    """
    file_path = DATA_DIR / filename
    if not file_path.exists():
        print(f"  ✗ File not found: {file_path}")
        return None

    with open(file_path, "rb") as f:
        content = f.read()

    # Determine MIME type
    mime = "application/pdf" if filename.endswith(".pdf") else "text/plain"

    resp = client.post(
        "/documents/upload",
        files={"file": (filename, content, mime)},
        data={"document_type": document_type, "source_date": source_date},
        headers={"Authorization": f"Bearer {token}"},
        timeout=30.0,
    )

    if resp.status_code == 409:
        existing_id = resp.json().get("existing_document_id", "?")
        print(f"  → Skipped (duplicate): {filename}  [id={existing_id}]")
        return None

    resp.raise_for_status()
    doc_id = resp.json()["id"]
    print(f"  ↑ Uploaded: {filename}  [id={doc_id}]")
    return doc_id


def wait_for_completion(
    client: httpx.Client,
    token: str,
    doc_id: str,
    filename: str,
    timeout: int = 120,
    interval: int = 5,
) -> bool:
    """Poll until the document reaches 'completed' or times out."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        resp = client.get(
            f"/documents/{doc_id}",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10.0,
        )
        resp.raise_for_status()
        status = resp.json().get("processing_status", "unknown")
        if status == "completed":
            print(f"  ✓ Processed: {filename}")
            return True
        if status == "failed":
            print(f"  ✗ Processing failed: {filename}")
            return False
        time.sleep(interval)

    print(f"  ✗ Timed out waiting for: {filename}")
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed HealthSignal demo data")
    parser.add_argument("--backend", default="http://localhost:8000", help="Backend URL")
    args = parser.parse_args()

    backend = args.backend.rstrip("/")
    print(f"\nHealthSignal Demo Seeder")
    print(f"Backend: {backend}")
    print(f"Data:    {DATA_DIR}\n")

    # Check backend is reachable
    try:
        httpx.get(f"{backend}/health", timeout=5.0).raise_for_status()
    except Exception as e:
        print(f"✗ Cannot reach backend at {backend}: {e}")
        sys.exit(1)

    token = get_token(backend)
    print()

    results = []
    with httpx.Client(base_url=backend, timeout=30.0) as client:
        for filename, doc_type, source_date in DOCUMENTS:
            print(f"[{doc_type}] {filename} ({source_date})")
            doc_id = upload_document(client, token, filename, doc_type, source_date)
            if doc_id:
                success = wait_for_completion(client, token, doc_id, filename)
                results.append((filename, "completed" if success else "failed"))
            else:
                results.append((filename, "skipped"))
            print()

    # Summary
    print("=" * 56)
    print("SUMMARY")
    print("=" * 56)
    for filename, status in results:
        icon = "✓" if status == "completed" else ("→" if status == "skipped" else "✗")
        print(f"  {icon}  {filename:<40} {status}")

    failed = [f for f, s in results if s == "failed"]
    if failed:
        print(f"\n✗ {len(failed)} document(s) failed to process.")
        sys.exit(1)
    else:
        completed = [f for f, s in results if s == "completed"]
        skipped = [f for f, s in results if s == "skipped"]
        print(f"\n✓ Done. {len(completed)} uploaded, {len(skipped)} skipped (already exist).")
        print(f"  Demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")


if __name__ == "__main__":
    main()
