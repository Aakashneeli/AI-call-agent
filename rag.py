import os
from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings

class KnowledgeBase:
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.vector_store = None
        self.embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        
    def _build_index(self):
        # Use absolute path to ensure we find it
        index_path = os.path.join(os.getcwd(), "faiss_index")
        try:
            if os.path.exists(index_path):
                print(f"Loading existing vector index from {index_path}...")
                self.vector_store = FAISS.load_local(index_path, self.embeddings, allow_dangerous_deserialization=True)
                print("Vector index loaded successfully.")
                return

            # Load ALL PDFs
            documents = []
            if os.path.exists(self.data_dir):
                for filename in os.listdir(self.data_dir):
                    if filename.endswith(".pdf"):
                        pdf_path = os.path.join(self.data_dir, filename)
                        print(f"Loading PDF: {filename}")
                        loader = PyPDFLoader(pdf_path)
                        documents.extend(loader.load())
            
            if not documents:
                print("No documents found to ingest.")
                return

            # Split Text
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=1000,
                chunk_overlap=300
            )
            texts = text_splitter.split_documents(documents)
            
            # Create Vector Store
            print(f"Creating vector index from {len(documents)} pages... (this may take a moment)")
            self.vector_store = FAISS.from_documents(texts, self.embeddings)
            
            # Save Index
            self.vector_store.save_local(index_path)
            print("Vector index created and saved successfully.")
            
        except Exception as e:
            print(f"Error building index: {e}")

    def _extract_key_terms(self, question: str) -> list[str]:
        """Extract key terms from the question for better matching."""
        key_mappings = {
            "products": ["products", "docapture", "skill matrix", "intelligentic"],
            "services": ["services", "agentic ai", "automation", "consulting"],
            "leadership": ["leadership", "team", "ceo", "founder", "vinay", "syed", "venkat"],
            "contact": ["contact", "email", "phone", "address"],
            "offices": ["offices", "locations", "global", "hyderabad", "dubai", "usa"],
            "success": ["success", "case study", "testimonial", "results"],
            # RFP / Technical Terms
            "requirements": ["requirements", "must have", "shall", "mandatory", "functional", "non-functional"],
            "technical": ["technical", "architecture", "security", "deployment", "api", "integration", "stack"],
            "scope": ["scope", "deliverables", "timeline", "milestones", "phases"],
            "commercial": ["commercial", "budget", "pricing", "cost", "payment", "terms"],
            "compliance": ["compliance", "gdpr", "iso", "standards", "regulations"],
        }
        
        question_lower = question.lower()
        relevant_terms = []
        
        for key, terms in key_mappings.items():
            if key in question_lower or any(term in question_lower for term in terms):
                relevant_terms.extend(terms)
        
        return relevant_terms

    def _score_document(self, doc, question: str, key_terms: list[str]) -> int:
        """Score a document based on relevance to question and key terms."""
        score = 0
        doc_text_lower = doc.page_content.lower()
        metadata_str = str(doc.metadata).lower()
        
        # Boost based on key terms presence
        if key_terms:
            for term in key_terms:
                if term in doc_text_lower:
                    score += 3
                # Boost if key term is in metadata (e.g. filename)
                if term in metadata_str:
                    score += 2
        
        # Boost based on question words
        question_words = question.lower().split()
        for word in question_words:
            if len(word) > 3 and word in doc_text_lower:
                score += 1
        
        # Penalize very short documents (likely headers/footers noise)
        if len(doc.page_content) < 100:
            score -= 5
                
        return score

    def query(self, question, k=5):
        """Retrieve relevant context with re-ranking"""
        if not self.vector_store:
            return ""
            
        try:
            # 1. Fetch more candidates than needed (k*5) for better re-ranking
            docs = self.vector_store.similarity_search(question, k=k*5)
            
            # 2. Extract key terms
            key_terms = self._extract_key_terms(question)
            
            # 3. Re-rank based on custom scoring
            # Create pairs of (doc, score)
            scored_docs = []
            for doc in docs:
                score = self._score_document(doc, question, key_terms)
                scored_docs.append((doc, score))
            
            # Sort by score descending
            scored_docs.sort(key=lambda x: x[1], reverse=True)
            
            # 4. Select top k
            final_docs = [doc for doc, score in scored_docs[:k]]
            
            # Combine content with source attribution
            context_parts = []
            for i, doc in enumerate(final_docs):
                source = doc.metadata.get('source', 'Unknown Document')
                filename = os.path.basename(source)
                context_parts.append(f"[Document {i+1} | Source: {filename}]\n{doc.page_content}")
            
            context = "\n\n---\n\n".join(context_parts)
            return context
        except Exception as e:
            print(f"Error querying knowledge base: {e}")
            return ""
        except Exception as e:
            print(f"Error querying knowledge base: {e}")
            return ""

# Singleton instance placeholder
kb = None

def init_knowledge_base(data_dir):
    global kb
    kb = KnowledgeBase(data_dir)
    return kb

def get_knowledge_base():
    global kb
    return kb
