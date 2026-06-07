import os
import uuid

import httpx
import gradio as gr

from core.config import settings


# ── Upload tab ──────────────────────────────────────────────────────────────

DOCUMENT_TYPES = [
    "blood_test",
    "lab_report",
    "symptom_note",
    "supplement_list",
    "diet_note",
    "doctor_summary",
    "journal",
]


def upload_document(file, source_date: str) -> str:
    if file is None:
        return "Please select a file to upload."

    try:
        file_path = file if isinstance(file, str) else file.name
        filename = os.path.basename(file_path)

        with open(file_path, "rb") as f:
            files = {"file": (filename, f, "application/octet-stream")}
            data = {}
            if source_date:
                data["source_date"] = source_date

            response = httpx.post(
                f"{settings.backend_url}/documents/upload",
                files=files,
                data=data,
                timeout=300.0,
            )

        if response.status_code == 200:
            doc = response.json()
            doc_type = doc.get("document_type") or "detecting…"
            return (
                f"✅ Upload successful!\n\n"
                f"Document ID: {doc['id']}\n"
                f"Filename:    {doc['filename']}\n"
                f"Type:        {doc_type}\n"
                f"Status:      {doc['processing_status']}\n\n"
                f"The document type is detected automatically. "
                f"Check document status to see the final result."
            )
        elif response.status_code == 409:
            detail = response.json().get("detail", {})
            existing_id = detail.get("existing_document_id", "unknown")
            return f"⚠️ This file has already been uploaded.\n\nExisting document ID: {existing_id}"
        else:
            return f"❌ Upload failed: {response.status_code}\n{response.text}"

    except Exception as e:
        return f"❌ Error: {e}"


def check_document_status(document_id: str) -> str:
    if not document_id.strip():
        return "Please enter a document ID."
    try:
        response = httpx.get(
            f"{settings.backend_url}/documents/{document_id.strip()}",
            timeout=10.0,
        )
        if response.status_code == 200:
            doc = response.json()
            return (
                f"Document ID: {doc['id']}\n"
                f"Filename:    {doc['filename']}\n"
                f"Type:        {doc['document_type']}\n"
                f"Status:      {doc['processing_status']}\n"
                f"Uploaded:    {doc['uploaded_at']}"
            )
        elif response.status_code == 404:
            return "Document not found."
        else:
            return f"Error: {response.status_code}"
    except Exception as e:
        return f"Error: {e}"


# ── Ask tab (conversational chat) ────────────────────────────────────────────

def ask_question(
    question: str,
    history: list[dict],
    session_id: str,
    document_type_filter: str,
) -> tuple[list[dict], str, str]:
    """Send a question to the supervisor and update the chat history."""
    if not question.strip():
        return history, "", ""

    try:
        payload: dict = {
            "question": question.strip(),
            "session_id": session_id,
        }
        if document_type_filter and document_type_filter != "All":
            payload["document_type"] = document_type_filter

        response = httpx.post(
            f"{settings.ai_agent_url}/query",
            json=payload,
            timeout=120.0,
        )

        if response.status_code == 200:
            data = response.json()
            answer = data["answer"]
            sources_text = ""
            if data["sources"]:
                sources_text = "\n\n".join(
                    f"📄 {s['filename']} | {s['document_type']} | {s['source_date'] or 'unknown date'} "
                    f"(score: {s['score']:.2f})\n{s['text'][:300]}..."
                    for s in data["sources"]
                )
            else:
                sources_text = "No source chunks found."

            history = history + [
                {"role": "user", "content": question.strip()},
                {"role": "assistant", "content": answer},
            ]
            return history, "", sources_text
        else:
            error_msg = f"Error {response.status_code}: {response.text}"
            history = history + [
                {"role": "user", "content": question.strip()},
                {"role": "assistant", "content": error_msg},
            ]
            return history, "", ""

    except Exception as e:
        error_msg = f"Error: {e}"
        history = history + [
            {"role": "user", "content": question.strip()},
            {"role": "assistant", "content": error_msg},
        ]
        return history, "", ""


def new_conversation() -> tuple[list, str]:
    """Reset the chat and generate a fresh session ID."""
    return [], str(uuid.uuid4())


# ── Report tab ────────────────────────────────────────────────────────────────

def generate_report(period_days: int) -> str:
    try:
        response = httpx.post(
            f"{settings.ai_agent_url}/report/generate",
            json={"user_id": "default", "period_days": period_days},
            timeout=180.0,
        )
        if response.status_code == 200:
            return response.json()["report"]
        else:
            return f"❌ Error {response.status_code}: {response.text}"
    except Exception as e:
        return f"❌ Error: {e}"


# ── Gradio UI ─────────────────────────────────────────────────────────────────

with gr.Blocks(title="HealthSignal") as demo:
    gr.Markdown("# 🏥 HealthSignal\nYour personal health intelligence assistant.")

    # ── Upload tab ──────────────────────────────────────────────────────────
    with gr.Tab("📤 Upload"):
        gr.Markdown("### Upload a health document")
        with gr.Row():
            with gr.Column():
                file_input = gr.File(
                    label="Select file (PDF or text)",
                    file_types=[".pdf", ".txt"],
                )
                source_date_input = gr.Textbox(
                    label="Document date (YYYY-MM-DD, optional)",
                    placeholder="e.g. 2024-03-15",
                )
                upload_btn = gr.Button("Upload & Ingest", variant="primary")
            with gr.Column():
                upload_output = gr.Textbox(label="Upload status", lines=8)

        upload_btn.click(
            fn=upload_document,
            inputs=[file_input, source_date_input],
            outputs=upload_output,
        )

        gr.Markdown("### Check document status")
        with gr.Row():
            doc_id_input = gr.Textbox(
                label="Document ID", placeholder="Paste document ID here"
            )
            check_btn = gr.Button("Check status")
        status_output = gr.Textbox(label="Status", lines=5)
        check_btn.click(
            fn=check_document_status, inputs=doc_id_input, outputs=status_output
        )

    # ── Ask tab ─────────────────────────────────────────────────────────────
    with gr.Tab("💬 Ask"):
        gr.Markdown(
            "### Chat with your health data\n"
            "Ask follow-up questions — the assistant remembers the conversation."
        )

        # session_id persists across turns in this tab
        session_id_state = gr.State(str(uuid.uuid4()))

        chatbot = gr.Chatbot(label="Conversation", height=450)

        with gr.Row():
            question_input = gr.Textbox(
                label="Your question",
                placeholder="e.g. What changed in my latest blood test?",
                lines=2,
                scale=4,
            )
            with gr.Column(scale=1):
                ask_btn = gr.Button("Send", variant="primary")
                new_chat_btn = gr.Button("New conversation")

        filter_dropdown = gr.Dropdown(
            choices=["All"] + DOCUMENT_TYPES,
            value="All",
            label="Filter by document type (optional)",
        )

        with gr.Accordion("📎 Source chunks used", open=False):
            sources_output = gr.Textbox(label="Sources", lines=8)

        ask_btn.click(
            fn=ask_question,
            inputs=[question_input, chatbot, session_id_state, filter_dropdown],
            outputs=[chatbot, question_input, sources_output],
        )
        question_input.submit(
            fn=ask_question,
            inputs=[question_input, chatbot, session_id_state, filter_dropdown],
            outputs=[chatbot, question_input, sources_output],
        )
        new_chat_btn.click(
            fn=new_conversation,
            inputs=[],
            outputs=[chatbot, session_id_state],
        )

    # ── Report tab ───────────────────────────────────────────────────────────
    with gr.Tab("📋 Doctor Report"):
        gr.Markdown(
            "### Generate a doctor visit report\n"
            "A structured summary of your recent abnormal markers, symptoms, supplement changes, "
            "and suggested questions to ask your doctor."
        )

        with gr.Row():
            period_slider = gr.Slider(
                minimum=30,
                maximum=365,
                value=90,
                step=30,
                label="Period (days back from today)",
            )
            generate_btn = gr.Button("Generate Report", variant="primary")

        report_output = gr.Textbox(label="Report", lines=30, max_lines=60)

        generate_btn.click(
            fn=generate_report,
            inputs=[period_slider],
            outputs=report_output,
        )


if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)
