from uri_core.core.orchestrator import UriOrchestrator

def test_sync():
    print("Initializing Orchestrator...")
    orchestrator = UriOrchestrator()
    
    print("Starting Gmail Sync (This might take a few seconds...)")
    try:
        # Running the exact command the UI tries to run
        res = orchestrator.process_evidence("test_session", "New India Assurance OR insurance policy OR student database")
        print("\nSync completed without crashing Python!")
        print(f"Success: {res.get('success')}")
        print(f"Documents processed: {len(res.get('documents_processed', []))}")
        if res.get('errors'):
            print(f"Errors encountered: {res.get('errors')}")
    except Exception as e:
        print(f"\nCaught a Python exception: {str(e)}")

if __name__ == "__main__":
    test_sync()
