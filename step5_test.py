from uri_core.services.drive_service import DriveService

def test_search():
    print("Initializing URI Drive Search...")
    drive = DriveService()
    
    # We will search for 'Hostel' based on your recent files list
    search_term = "Hostel"
    print(f"Searching Drive for: '{search_term}'")
    
    res = drive.search_drive(search_term)
    
    if res.get("success"):
        files = res.get("files", [])
        if not files:
            print("\nNo files found matching the search term.")
            return
            
        print(f"\nSUCCESS! Found {len(files)} matching files:")
        for f in files:
            print(f"- {f['name']}")
            
        print("\nDownloading the top match...")
        top_match = files[0]
        dl_res = drive.download_file(top_match['id'], top_match['name'], top_match['mimeType'])
        
        if dl_res.get("success"):
            print(f"Downloaded to: {dl_res.get('path')}")
        else:
            print(f"Download failed: {dl_res.get('reason')}")
            
    else:
        print(f"\nSearch failed: {res.get('reason')}")

if __name__ == "__main__":
    test_search()
