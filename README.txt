BLOCKCHAIN-BASED STUDENT RECORD MANAGEMENT
==========================================

REQUIREMENTS
- Python 3.9 or newer
- Internet connection for the Google Fonts styling (the app itself works without it)

RUN ON macOS
1. Extract this ZIP file.
2. Open Terminal.
3. Move into the extracted folder, for example:
   cd ~/Downloads/blockchain_student_record_management
4. Create a virtual environment:
   python3 -m venv venv
5. Activate it:
   source venv/bin/activate
6. Install dependencies:
   pip install -r requirements.txt
7. Start the website:
   python app.py
8. Open this address in your browser:
   http://127.0.0.1:5000

DEMO ADMIN LOGIN
Username: admin
Password: admin123

FEATURES
- Admin login and logout
- Add, view, search, edit and delete student records
- SQLite database created automatically
- SHA-256 hash-linked blockchain audit ledger
- A new block is recorded for every create, update and delete action
- Verify the complete chain for tampering
- Responsive dark dashboard

IMPORTANT
This is an educational, single-server blockchain demonstration. The hash chain is stored
in the same SQLite database as the records; it is tamper-evident, not a decentralized
public blockchain. Change the demo password and Flask secret key before any real use.
Do not store sensitive student information in this demo deployment.
