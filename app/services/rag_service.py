# AI生成

"""RAG service — FAISS-based retrieval for VM hardening benchmark knowledge.



Loads benchmark data for Linux VM hardening (CIS, STIG, NIST, PCI-DSS) into a

FAISS index for retrieval-augmented generation during assessment.

"""
try:
    from sentence_transformers import SentenceTransformer
except ImportError:
    SentenceTransformer = None
import json

import logging

import numpy as np

from pathlib import Path

from typing import List, Dict, Optional




try:

    import faiss

    # Test accessing basic attribute to ensure full C module loaded correctly

    _ = getattr(faiss, "IndexFlatIP", None)

    FAISS_AVAILABLE = bool(_)

except (ImportError, AttributeError, Exception) as e:

    FAISS_AVAILABLE = False





logger = logging.getLogger(__name__)





class RAGService:

    """RAG service using FAISS for benchmark knowledge retrieval."""



    def __init__(self, benchmark_dir: Path, embedding_model: str = "all-MiniLM-L6-v2"):

        self.benchmark_dir = benchmark_dir

        self.embedding_model_name = embedding_model

        self.encoder = None

        self.index = None

        self.documents = []

        self.metadata = []

        self._loaded = False



    def is_loaded(self) -> bool:

        """Check if benchmarks have been loaded into the index."""

        return self._loaded



    def _load_encoder(self):

        """Load the sentence transformer model."""

        if self.encoder is None:

            if SentenceTransformer is None:
                raise RuntimeError("sentence_transformers package not installed — RAG features unavailable")

            logger.info(f"Loading embedding model: {self.embedding_model_name}")

            self.encoder = SentenceTransformer(self.embedding_model_name)



    def load_benchmarks(self):

        """Load all Linux VM benchmark JSON files into the FAISS index."""

        benchmark_files = {

            "cis_linux": self.benchmark_dir / "cis_linux.json",

            "stig_linux": self.benchmark_dir / "stig_linux.json",

            "nist_linux": self.benchmark_dir / "nist_linux.json",

            "pci_linux": self.benchmark_dir / "pci_linux.json",

        }



        all_docs = []

        all_meta = []



        for benchmark_name, file_path in benchmark_files.items():

            if not file_path.exists():

                logger.warning(f"Benchmark file not found: {file_path}")

                continue



            with open(file_path, "r", encoding="utf-8") as f:

                data = json.load(f)



            # Parse benchmark name into components

            parts = benchmark_name.split("_")

            benchmark_type = parts[0].upper()  # CIS, STIG, NIST, PCI

            platform = parts[1] if len(parts) > 1 else "linux"



            for item in data.get("controls", []):

                # Create a searchable text from the control item

                text = self._create_searchable_text(item)

                all_docs.append(text)

                all_meta.append({

                    "benchmark": benchmark_type,

                    "platform": platform,

                    "control_id": item.get("id", ""),

                    "title": item.get("title", ""),

                    "description": item.get("description", ""),

                    "expected": item.get("expected", ""),

                    "remediation": item.get("remediation", ""),

                    "severity": item.get("severity", ""),

                    "category": item.get("category", ""),

                })



        if not all_docs:

            logger.warning("No benchmark documents loaded")

            self._loaded = False

            return



        self.documents = all_docs

        self.metadata = all_meta



        # Build FAISS index

        if FAISS_AVAILABLE:

            try:

                self._load_encoder()

                embeddings = self.encoder.encode(all_docs, show_progress_bar=False)

                dimension = embeddings.shape[1]

                self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity

                # Normalize embeddings for cosine similarity

                faiss.normalize_L2(embeddings)

                self.index.add(embeddings.astype(np.float32))

                logger.info(f"FAISS index built with {len(all_docs)} documents")

            except Exception as e:

                logger.warning(f"Failed to build FAISS index: {e}. Falling back to text matching.")

                self.index = None

        else:

            logger.warning("FAISS not available, using simple text matching fallback")





        self._loaded = True



    def _create_searchable_text(self, item: dict) -> str:

        """Create a searchable text representation of a benchmark control."""

        parts = []

        for key in ["id", "title", "description", "category", "expected", "remediation"]:

            val = item.get(key, "")

            if val:

                parts.append(f"{key}: {val}")

        return " | ".join(parts)



    def search(

        self,

        query: str,

        benchmark: Optional[str] = None,

        top_k: int = 5,

    ) -> List[Dict]:

        """Search the RAG knowledge base.



        Args:

            query: search query text

            benchmark: filter by benchmark type (CIS/STIG/NIST/PCI)

            top_k: number of results to return



        Returns:

            list of matching benchmark controls with relevance scores

        """

        if not self._loaded:

            self.load_benchmarks()



        if not self.documents:

            return []



        # Filter documents by benchmark if specified

        candidate_indices = []

        for i, meta in enumerate(self.metadata):

            if benchmark and meta["benchmark"] != benchmark.upper():

                continue

            candidate_indices.append(i)



        if not candidate_indices:

            return []



        if FAISS_AVAILABLE and self.index is not None:

            # Use FAISS for retrieval

            query_embedding = self.encoder.encode([query], show_progress_bar=False)

            faiss.normalize_L2(query_embedding)

            scores, indices = self.index.search(query_embedding.astype(np.float32), len(self.documents))



            results = []

            for score, idx in zip(scores[0], indices[0]):

                if idx in candidate_indices:

                    meta = self.metadata[idx].copy()

                    meta["relevance_score"] = float(score)

                    results.append(meta)

                if len(results) >= top_k:

                    break

            return results

        else:

            # Fallback: simple keyword matching

            query_lower = query.lower()

            scored = []

            for idx in candidate_indices:

                doc_lower = self.documents[idx].lower()

                score = sum(1 for word in query_lower.split() if word in doc_lower)

                if score > 0:

                    meta = self.metadata[idx].copy()

                    meta["relevance_score"] = score / 10.0

                    scored.append(meta)

            scored.sort(key=lambda x: x["relevance_score"], reverse=True)

            return scored[:top_k]



    def get_benchmark_controls(

        self,

        benchmark: str,

    ) -> List[Dict]:

        """Get all controls for a specific benchmark."""

        if not self._loaded:

            self.load_benchmarks()



        results = []

        for meta in self.metadata:

            if meta["benchmark"] == benchmark.upper():

                # Return a copy with both 'id' and 'control_id' keys so consumers

                # that expect either naming convention work correctly.

                item = meta.copy()

                item["id"] = meta["control_id"]

                item["title"] = meta["title"]

                item["description"] = meta["description"]

                item["expected"] = meta["expected"]

                item["remediation"] = meta["remediation"]

                item["severity"] = meta["severity"]

                item["category"] = meta["category"]

                results.append(item)

        return results



    def is_loaded(self) -> bool:

        return self._loaded