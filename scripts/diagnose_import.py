import importlib
import os
import sys
import time
import traceback

sys.path.insert(0, os.getcwd())  # ensure repo root (and `api`) is importable

MODULES = [
    "triage_iq.config",
    "triage_iq.db.connection",
    "triage_iq.db.crud",
    "triage_iq.ingestion.vector_store",
    "triage_iq.retrievers.compression_retriever",
    "triage_iq.chains.classifier_chain",
    "triage_iq.chains.rag_chain",
    "triage_iq.chains.routing_chain",
    "triage_iq.chains.escalation_chain",
    "triage_iq.tools.escalate_ticket",
    "triage_iq.tools.create_trello_card",
    "triage_iq.integrations.trello_board",
    "triage_iq.pipeline",
    "api.dashboard",
    "api.main",
]

for name in MODULES:
    print(f"IMPORTING {name}", flush=True)
    try:
        importlib.import_module(name)
        print(f"OK {name}", flush=True)
    except Exception:
        print(f"FAILED {name}", flush=True)
        traceback.print_exc()
        sys.exit(1)

print("ALL IMPORTS OK", flush=True)
time.sleep(300)
