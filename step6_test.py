from uri_core.services.drive_service import DriveService

def test_search_and_fallback():
    print("Initializing URI Drive Search...")
    drive = DriveService()
    
    search_term = "Hostel"
    print(f"Searching Drive for: '{search_term}'\n")
    
    res = drive.search_drive(search_term)
    
    if not res.get("success"):
        print(f"Search failed: {res.get('reason')}")
        return
        
    files = res.get("files", [])
    if not files:
        print("No files found matching the search term.")
        return
        
    print(f"SUCCESS! Found {len(files)} matching files.")
    
    # Loop through the files and try to download the first accessible one
    for f in files:
        print(f"\nAttempting to download: {f['name']}")
        dl_res = drive.download_file(f['id'], f['name'], f['mimeType'])
        
        if dl_res.get("success"):
            print(f"SUCCESS! Downloaded to: {dl_res.get('path')}")
            break  # Stop searching once we successfully secure a file
        else:
            reason = dl_res.get("reason")
            if "cannotExportFile" in reason or "403" in reason:
                print("-> SKIPPED: This file is restricted by the owner (Downloads disabled).")
            else:
                print(f"-> FAILED: {reason}")

if __name__ == "__main__":
    test_search_and_fallback()
