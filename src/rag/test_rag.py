from src.rag.document_loader import DocumentLoader
from src.rag.knowledge_base import KnowledgeBase

PDF_PATH = "Data/Loan_Recovery.pdf"


def main():
    print("\n🔍 RAG TEST – Loan Recovery PDF\n")

    # 1️⃣ Load PDF
    print("1️⃣ Loading PDF...")
    documents = DocumentLoader.load_pdf(PDF_PATH)

    if not documents:
        print("❌ No documents loaded")
        return

    print(f"✅ Loaded {len(documents)} pages")

    # 2️⃣ Create Knowledge Base
    print("2️⃣ Creating Knowledge Base...")
    kb = KnowledgeBase()

    if not kb.create_collection(documents):
        print("❌ Failed to create knowledge base")
        return

    print("\n✅ READY! Ask questions about Loan Recovery (type 'exit' to stop)\n")

    # 3️⃣ Interactive QA loop
    while True:
        question = input("❓ Question: ").strip()
        if question.lower() == "exit":
            break

        response = kb.query(question, n_results=3)

        if not response or not response.get("results"):
            print("⚠️ No results found\n")
            continue

        print("\n📌 Retrieved Context:\n")
        for i, hit in enumerate(response["results"], 1):
            meta = hit.get("metadata", {})
            page = meta.get("page", "N/A")
            source = meta.get("source", "Unknown")

            print(f"{i}. Page {page} — {source}")
            print(f"   {hit['content'][:300]}...\n")


if __name__ == "__main__":
    main()