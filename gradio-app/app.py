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


def upload_document(file, document_type: str, source_date: str) -> str:
    if file is None:
        return "Please select a file to upload."

    try:
        with open(file.name, "rb") as f:
            files = {"file": (file.name.split("/")[-1], f, "application/octet-stream")}
            data = {"document_type": document_type}
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
            return (
                f"✅ Upload successful!\n\n"
                f"Document ID: {doc['id']}\n"
                f"Filename:    {doc['filename']}\n"
                f"Type:        {doc['document_type']}\n"
                f"Status:      {doc['processing_status']}\n\n"
                f"Ingestion has started in the background. "
                f"Refresh document status to check progress."
            )
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


# ── Query tab ────────────────────────────────────────────────────────────────

def ask_question(question: str, document_type_filter: str) -> tuple[str, str]:
    if not question.strip():
        return "Please enter a question.", ""
    try:
        payload = {"question": question.strip()}
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

            return answer, sources_text
        else:
            return f"Error: {response.status_code}\n{response.text}", ""

    except Exception as e:
        return f"Error: {e}", ""


# ── Gradio UI ────────────────────────────────────────────────────────────────

with gr.Blocks(title="HealthSignal") as demo:
    gr.Markdown("# 🏥 HealthSignal\nYour personal health intelligence assistant.")

    with gr.Tab("📤 Upload"):
        gr.Markdown("### Upload a health document")
        with gr.Row():
            with gr.Column():
                file_input = gr.File(
                    label="Select file (PDF or text)",
                    file_types=[".pdf", ".txt"],
                )
                doc_type = gr.Dropdown(
                    choices=DOCUMENT_TYPES,
                    value="blood_test",
                    label="Document type",
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
            inputs=[file_input, doc_type, source_date_input],
            outputs=upload_output,
        )

        gr.Markdown("### Check document status")
        with gr.Row():
            doc_id_input = gr.Textbox(label="Document ID", placeholder="Paste document ID here")
            check_btn = gr.Button("Check status")
        status_output = gr.Textbox(label="Status", lines=5)
        check_btn.click(fn=check_document_status, inputs=doc_id_input, outputs=status_output)

    with gr.Tab("💬 Ask"):
        gr.Markdown("### Ask a question about your health data")
        with gr.Row():
            with gr.Column(scale=2):
                question_input = gr.Textbox(
                    label="Your question",
                    placeholder="e.g. What changed in my latest blood test?",
                    lines=3,
                )
                filter_dropdown = gr.Dropdown(
                    choices=["All"] + DOCUMENT_TYPES,
                    value="All",
                    label="Filter by document type (optional)",
                )
                ask_btn = gr.Button("Ask", variant="primary")
            with gr.Column(scale=3):
                answer_output = gr.Textbox(label="Answer", lines=12)

        with gr.Accordion("📎 Source chunks used", open=False):
            sources_output = gr.Textbox(label="Sources", lines=10)

        ask_btn.click(
            fn=ask_question,
            inputs=[question_input, filter_dropdown],
            outputs=[answer_output, sources_output],
        )


if __name__ == "__main__":
    demo.launch(server_port=7860, share=False)
