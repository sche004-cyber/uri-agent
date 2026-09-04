from uri_core.core.orchestrator import UriOrchestrator

def run_final_test():
    print("Initializing URI Orchestrator...\n")
    orchestrator = UriOrchestrator()
    
    print("--- Final Test: Formatted Student Output ---")
    res = orchestrator.process_message("test_session", "Find phone number for B230035CS")
    
    print(res.get("answer"))

if __name__ == "__main__":
    run_final_test()
