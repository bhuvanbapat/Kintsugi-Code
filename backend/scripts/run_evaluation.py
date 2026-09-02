"""Run the evaluation benchmark and print results."""
import pathlib
import shutil
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))

from app.models.domain import Repository
from app.services.evaluator import run_evaluation_for_repo
from app.services.indexer import index_repository
from app.services.rag_service import build_retriever
from app.services.store import Store


def main() -> None:
    tmp = pathlib.Path(tempfile.mkdtemp())
    shutil.copytree(
        pathlib.Path(__file__).resolve().parent.parent.parent / "examples" / "sample_repo",
        tmp / "sample_repo",
    )
    store = Store(db_path=str(tmp / "t.db"))
    repo = Repository(name="sample_repo", root_path=str(tmp / "sample_repo"))
    store.upsert_repository(repo)
    index_repository(repo, store)
    # Register the temp repo's retriever in the process-level cache the
    # evaluator uses (get_retriever), pointing at our store.
    import app.services.rag_service as rag

    rag._retrievers[repo.id] = build_retriever(store, repo.id)
    result = run_evaluation_for_repo(repo.id, store)
    print("=== Evaluation summary ===")
    print(result["summary"])
    for case in result["cases"]:
        print(case["case_id"], "recall:", case["recall"], "passed:", case["passed"],
              "latency_ms:", case["latency_ms"])


if __name__ == "__main__":
    sys.exit(main())
