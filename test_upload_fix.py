#!/usr/bin/env python3

import requests
import os

def test_document_upload():
    """Test the document upload endpoint to verify the fix."""
    
    # Create a simple test PDF content (minimal PDF structure)
    test_pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test PDF) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000173 00000 n 
0000000301 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF"""
    
    # API endpoint and headers
    url = "http://localhost:5000/documents/"
    headers = {
        "X-API-Key": "admin"
    }
    
    # Create the file upload data
    files = {
        "file": ("test_document.pdf", test_pdf_content, "application/pdf")
    }
    
    data = {
        "description": "Test document upload to verify fix"
    }
    
    try:
        print("Testing document upload...")
        response = requests.post(url, headers=headers, files=files, data=data, timeout=30)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("✅ Document upload test PASSED!")
            return True
        else:
            print("❌ Document upload test FAILED!")
            return False
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        return False

if __name__ == "__main__":
    test_document_upload()
