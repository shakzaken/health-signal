"""
Health Signal Eval Framework — versioned test runner.

Each test lives in eval/tests/<NNN>/ and contains:
  - golden_qa.md  — questions and expected answers (human-readable reference)
  - results.json  — output after running (generated)
  - report.md     — markdown report with scores and recommendations (generated)

To run the latest test:
    python eval/setup_and_run.py

To run a specific test:
    python eval/setup_and_run.py --test 001

To create and run a new test (copies golden_qa.md template from latest):
    python eval/setup_and_run.py --new

Options:
    --backend     Backend URL (default: http://localhost:8000)
    --ai-agent    AI agent URL (default: http://localhost:8001)
    --skip-setup  Skip user registration and file upload (use existing data)
"""

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

import httpx

EVAL_USER_PASSWORD = "eval-password-2024"


def eval_user_email(test_number: str) -> str:
    return f"eval-{test_number}@healthsignal.dev"

EVAL_DIR = Path(__file__).parent
TESTS_DIR = EVAL_DIR / "tests"
DEFAULT_DEMO_DATA_DIR = TESTS_DIR / "001" / "data"


def data_dir_for_test(test_dir: Path) -> Path:
    """Use test-local data/ folder if present, otherwise fall back to test 001 data."""
    local = test_dir / "data"
    return local if local.exists() else DEFAULT_DEMO_DATA_DIR

POLL_INTERVAL = 5
MAX_WAIT = 300


# ── Test directory helpers ────────────────────────────────────────────────────

def list_tests() -> list[Path]:
    if not TESTS_DIR.exists():
        return []
    return sorted(p for p in TESTS_DIR.iterdir() if p.is_dir() and p.name.isdigit())


def latest_test() -> Path | None:
    tests = list_tests()
    return tests[-1] if tests else None


def get_test(number: str) -> Path:
    path = TESTS_DIR / number.zfill(3)
    if not path.exists():
        print(f"Test {number} not found at {path}")
        sys.exit(1)
    return path


def create_new_test() -> Path:
    tests = list_tests()
    next_num = (int(tests[-1].name) + 1) if tests else 1
    new_dir = TESTS_DIR / str(next_num).zfill(3)
    new_dir.mkdir(parents=True)

    # Copy golden_qa.md from latest as a starting template
    if tests:
        src = tests[-1] / "golden_qa.md"
        if src.exists():
            shutil.copy(src, new_dir / "golden_qa.md")
            print(f"  Created test {new_dir.name} — copied golden_qa.md from {tests[-1].name}")
            print(f"  Edit {new_dir / 'golden_qa.md'} before running.")
        else:
            print(f"  Created test {new_dir.name} — no golden_qa.md to copy, create one manually.")
    else:
        print(f"  Created first test at {new_dir}")

    return new_dir


# ── Auth ──────────────────────────────────────────────────────────────────────

def register_or_login(backend: str, email: str) -> str:
    with httpx.Client(base_url=backend, timeout=30.0) as client:
        resp = client.post("/auth/register", json={"email": email, "password": EVAL_USER_PASSWORD})
        if resp.status_code == 201:
            print(f"  Registered eval user: {email}")
            return resp.json()["access_token"]
        if resp.status_code == 409:
            resp = client.post("/auth/login", json={"email": email, "password": EVAL_USER_PASSWORD})
            resp.raise_for_status()
            print(f"  Logged in as: {email}")
            return resp.json()["access_token"]
        resp.raise_for_status()
    return ""


# ── Document management ───────────────────────────────────────────────────────

def delete_existing_documents(backend: str, token: str) -> None:
    """
    Clear all documents for the eval user before each run.

    Documents cannot be deleted via the public API (users do not have delete access).
    This function uses direct database access via docker compose — it is a local
    maintenance operation and must never run against production.
    """
    headers = {"Authorization": f"Bearer {token}"}
    with httpx.Client(base_url=backend, timeout=30.0) as client:
        resp = client.get("/documents", headers=headers)
        resp.raise_for_status()
        docs = resp.json()
        if not docs:
            print("  No existing documents.")
            return

    print(f"  Deleting {len(docs)} existing document(s) via database...")
    doc_ids = [doc["id"] for doc in docs]
    ids_list = "', '".join(doc_ids)

    # Delete child rows, then documents — same order as IngestionCleanupRepository
    sql_commands = [
        f"DELETE FROM lab_markers WHERE lab_result_id IN (SELECT id FROM lab_results WHERE document_id IN ('{ids_list}'))",
        f"DELETE FROM lab_results WHERE document_id IN ('{ids_list}')",
        f"DELETE FROM symptom_entries WHERE document_id IN ('{ids_list}')",
        f"DELETE FROM supplement_entries WHERE document_id IN ('{ids_list}')",
        f"DELETE FROM timeline_events WHERE reference_id IN (SELECT id FROM lab_results WHERE document_id IN ('{ids_list}'))",
        f"DELETE FROM documents WHERE id IN ('{ids_list}')",
    ]
    for sql in sql_commands:
        subprocess.run(
            ["docker", "compose", "exec", "-T", "postgres",
             "psql", "-U", "yakir", "-d", "healthsignal", "-c", sql],
            cwd=EVAL_DIR.parent,
            capture_output=True,
        )


def upload_demo_files(backend: str, token: str, demo_data_dir: Path) -> list[str]:
    headers = {"Authorization": f"Bearer {token}"}
    demo_files = sorted(p for p in demo_data_dir.glob("*") if not p.name.startswith(".") and p.is_file())
    if not demo_files:
        print(f"  ERROR: No demo files found in {DEMO_DATA_DIR}")
        sys.exit(1)

    doc_ids = []
    with httpx.Client(base_url=backend, timeout=60.0) as client:
        for path in demo_files:
            with open(path, "rb") as f:
                resp = client.post(
                    "/documents/upload",
                    headers=headers,
                    files={"file": (path.name, f, "text/plain")},
                    data={},
                )
            if resp.status_code in (200, 202):
                doc_id = resp.json()["id"]
                doc_ids.append(doc_id)
                print(f"  Uploaded: {path.name} → {doc_id}")
            else:
                print(f"  Warning: failed to upload {path.name} — {resp.status_code}")
    return doc_ids


def wait_for_processing(backend: str, token: str, doc_ids: list[str]) -> bool:
    headers = {"Authorization": f"Bearer {token}"}
    print(f"\n  Waiting for {len(doc_ids)} document(s) (max {MAX_WAIT}s)...")
    start = time.time()
    while time.time() - start < MAX_WAIT:
        with httpx.Client(base_url=backend, timeout=30.0) as client:
            resp = client.get("/documents", headers=headers)
            resp.raise_for_status()
            docs = {d["id"]: d for d in resp.json()}

        statuses = {did: docs.get(did, {}).get("processing_status", "unknown") for did in doc_ids}
        pending = [did for did, s in statuses.items() if s in ("pending", "processing")]
        failed = [did for did, s in statuses.items() if s == "failed"]
        completed = [did for did, s in statuses.items() if s == "completed"]

        print(f"  {len(completed)} completed / {len(pending)} pending / {len(failed)} failed   ", end="\r")

        if not pending:
            print()
            if failed:
                print(f"  Warning: {len(failed)} document(s) failed.")
            return len(failed) == 0
        time.sleep(POLL_INTERVAL)

    print(f"\n  Timeout waiting for processing.")
    return False


# ── Eval + report ─────────────────────────────────────────────────────────────

def run_eval(ai_agent: str, token: str, results_path: Path, test_dir: Path) -> bool:
    import subprocess
    venv_python = EVAL_DIR.parent / "ai-agent" / ".venv" / "bin" / "python"
    python = str(venv_python) if venv_python.exists() else sys.executable
    cmd = [
        python, "-m", "eval.run_evals",
        "--token", token,
        "--ai-agent", ai_agent,
        "--output", str(results_path),
    ]
    dataset_path = test_dir / "dataset.json"
    if dataset_path.exists():
        cmd += ["--dataset", str(dataset_path)]
    result = subprocess.run(cmd, cwd=EVAL_DIR.parent / "ai-agent")
    return result.returncode == 0


def generate_report(results_path: Path, report_path: Path, test_number: str) -> None:
    import subprocess
    cmd = [
        sys.executable,
        str(EVAL_DIR / "generate_report.py"),
        str(results_path),
        "--out", str(report_path),
        "--test", test_number,
    ]
    subprocess.run(cmd, cwd=EVAL_DIR.parent)


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Health Signal eval framework")
    parser.add_argument("--test", default=None, help="Test number to run (e.g. 001). Defaults to latest.")
    parser.add_argument("--new", action="store_true", help="Create a new test directory and exit")
    parser.add_argument("--backend", default="http://localhost:8000")
    parser.add_argument("--ai-agent", default="http://localhost:8001")
    parser.add_argument("--skip-setup", action="store_true", help="Skip user setup and file upload")
    args = parser.parse_args()

    # --new: just scaffold the directory and exit
    if args.new:
        create_new_test()
        return

    # Resolve test directory
    test_dir = get_test(args.test) if args.test else latest_test()
    if not test_dir:
        print("No tests found. Run with --new to create the first one.")
        sys.exit(1)

    results_path = test_dir / "results.json"
    report_path = test_dir / "report.md"
    test_number = test_dir.name
    email = eval_user_email(test_number)

    print(f"\n=== Health Signal Eval — Test {test_number} ===")
    print(f"    Directory: {test_dir}")
    print(f"    User:      {email}\n")

    if not args.skip_setup:
        print("Step 1: Auth")
        token = register_or_login(args.backend, email)

        print("\nStep 2: Clean existing documents")
        delete_existing_documents(args.backend, token)

        print("\nStep 3: Upload demo files")
        demo_data_dir = data_dir_for_test(test_dir)
        print(f"  Data source: {demo_data_dir}")
        doc_ids = upload_demo_files(args.backend, token, demo_data_dir)
        if not doc_ids:
            print("  ERROR: No documents uploaded.")
            sys.exit(1)

        print("\nStep 4: Wait for processing")
        wait_for_processing(args.backend, token, doc_ids)
    else:
        print("Step 1-4: Skipped (--skip-setup)")
        print("Step 1: Auth (needed for eval)")
        token = register_or_login(args.backend, email)

    print(f"\nStep 5: Run eval suite")
    passed = run_eval(args.ai_agent, token, results_path, test_dir)

    print(f"\nStep 6: Generate report")
    if results_path.exists():
        generate_report(results_path, report_path, test_number)
    else:
        print("  No results file — skipping report.")

    print(f"\n=== Test {test_number} complete ===")
    print(f"  Golden Q&A: {test_dir / 'golden_qa.md'}")
    print(f"  Results:    {results_path}")
    print(f"  Report:     {report_path}\n")

    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
