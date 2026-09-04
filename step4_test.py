from uri_core.services.drive_service import DriveService
import os

def test_download():
    print("Connecting to Drive...")
    drive = DriveService()
    
    list_res = drive.list_recent_files(limit=1)
    if not list_res.get("success") or not list_res.get("files"):
        print("Failed to find files.")
        return
        
    latest_file = list_res.get("files")[0]
    print(f"Targeting Latest File: {latest_file['name']}")
    print("Attempting to download/export...")
    
    download_res = drive.download_file(
        latest_file['id'], 
        latest_file['name'], 
        latest_file['mimeType']
    )
    
    if download_res.get("success"):
        file_path = download_res.get("path")
        file_size = os.path.getsize(file_path) / 1024 # KB
        print(f"\nSUCCESS! File secured in workspace.")
        print(f"Path: {file_path}")
        print(f"Size: {file_size:.2f} KB")
    else:
        print(f"\nDOWNLOAD FAILED: {download_res.get('reason')}")

if __name__ == "__main__":
    test_download()
