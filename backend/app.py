from flask import Flask, jsonify, request, render_template, session
from flask_cors import CORS
import json
import time
from datetime import datetime
import hashlib
import base64
from blockchain import VotingBlockchain, generate_key_pair, sign_vote
import os

app = Flask(__name__,
            static_folder='static',
            template_folder='../frontend')
CORS(app)
app.secret_key = 'blockchain-voting-secret-key-2024'

# Initialize blockchain
blockchain = VotingBlockchain()


# Initialize with some sample data
def initialize_sample_data():
    """Initialize with sample candidates and test voter"""
    print("=" * 60)
    print("INITIALIZING BLOCKCHAIN VOTING SYSTEM")
    print("=" * 60)

    # Register sample candidates
    candidates = [
        {"id": "candidate-1", "name": "Alex Johnson", "party": "University Progressive"},
        {"id": "candidate-2", "name": "Sarah Miller", "party": "Academic Reform"},
        {"id": "candidate-3", "name": "David Chen", "party": "Digital Future"},
        {"id": "candidate-4", "name": "Maria Garcia", "party": "Sustainable Campus"}
    ]

    for candidate in candidates:
        blockchain.register_candidate(
            candidate["id"],
            candidate["name"],
            candidate["party"]
        )

    print(f"✅ Registered {len(candidates)} candidates")

    # Create test voters
    test_voters = []
    for i in range(1, 4):
        private_key, public_key = generate_key_pair()
        voter_id = f"TEST{i:03d}"

        blockchain.register_voter(voter_id, public_key)

        test_voters.append({
            "voter_id": voter_id,
            "private_key": private_key,
            "public_key": public_key,
            "name": f"Test Voter {i}"
        })

    # Store test credentials
    app.test_voters = test_voters

    print(f"✅ Created {len(test_voters)} test voters")
    print("=" * 60)
    print("\n🔑 TEST CREDENTIALS:")
    for voter in test_voters:
        print(f"  Voter ID: {voter['voter_id']}")
        print(f"  Private Key (first 50 chars): {voter['private_key'][:50]}...")
        print()

    # Create some initial votes for demonstration
    print("🎲 Creating sample votes for demonstration...")
    sample_votes = [
        ("TEST001", "candidate-1"),
        ("TEST002", "candidate-2"),
        ("TEST003", "candidate-3")
    ]

    for voter_id, candidate_id in sample_votes:
        for voter in test_voters:
            if voter["voter_id"] == voter_id:
                signature = sign_vote(voter["private_key"], voter_id, candidate_id)
                blockchain.add_vote(voter_id, candidate_id, signature)
                print(f"  ✅ Added vote: {voter_id} → {candidate_id}")
                break

    # Mine a block to confirm sample votes
    blockchain.mine_pending_votes()

    print("✅ Sample data initialized successfully!")
    print("=" * 60)


# Initialize sample data
initialize_sample_data()

# In-memory storage
voters_db = {}
elections_db = {
    'university-2024': {
        'election_id': 'university-2024',
        'title': 'University Student Council Elections 2024',
        'start_date': '2024-03-01',
        'end_date': '2024-03-31',
        'is_active': True,
        'total_voters': 0,
        'total_votes': 0
    }
}


# Helper functions
def generate_voter_id(name: str, email: str) -> str:
    """Generate a unique voter ID"""
    timestamp = str(int(time.time()))
    hash_input = f"{name}{email}{timestamp}"
    return "V" + hashlib.sha256(hash_input.encode()).hexdigest()[:8].upper()


def verify_admin():
    """Check if user is admin"""
    return session.get('is_admin', False)


# API Routes
@app.route('/')
def index():
    """Serve main page"""
    return render_template('index.html')


@app.route('/api/test-credentials', methods=['GET'])
def get_test_credentials():
    """Get test credentials for demo"""
    try:
        return jsonify({
            'success': True,
            'voters': app.test_voters
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/test-vote', methods=['POST'])
def test_vote():
    """Test endpoint for voting (no private key needed for test users)"""
    try:
        data = request.json
        voter_id = data.get('voter_id')
        candidate_id = data.get('candidate_id')

        print(f"Processing test vote: {voter_id} for {candidate_id}")

        if not all([voter_id, candidate_id]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Find test voter
        test_voter = None
        for voter in app.test_voters:
            if voter['voter_id'] == voter_id:
                test_voter = voter
                break

        if not test_voter:
            return jsonify({'error': 'Test voter not found'}), 404

        # Check if voter has already voted
        voter_status = blockchain.get_voter_status(voter_id)
        if voter_status['has_voted']:
            return jsonify({
                'error': 'You have already voted',
                'status': voter_status
            }), 400

        # Check if candidate exists
        if candidate_id not in blockchain.candidates:
            return jsonify({'error': 'Candidate not found'}), 404

        # Sign the vote using test voter's private key
        signature = sign_vote(test_voter['private_key'], voter_id, candidate_id)

        # Add vote to blockchain
        if blockchain.add_vote(voter_id, candidate_id, signature):
            print(f"Test vote added to blockchain for {voter_id}")

            return jsonify({
                'success': True,
                'message': 'Vote cast successfully!',
                'signature': signature,
                'voter_status': blockchain.get_voter_status(voter_id)
            })
        else:
            return jsonify({'error': 'Failed to cast vote. Please try again.'}), 400

    except Exception as e:
        print(f"Test vote error: {e}")
        return jsonify({'error': f'Vote failed: {str(e)}'}), 500


@app.route('/api/register', methods=['POST'])
def register_voter():
    """Register a new voter"""
    try:
        data = request.json
        name = data.get('name')
        email = data.get('email')
        student_id = data.get('student_id')
        department = data.get('department')

        if not name or not email:
            return jsonify({'error': 'Name and email are required'}), 400

        # Generate voter ID and keys
        voter_id = generate_voter_id(name, email)
        private_key, public_key = generate_key_pair()

        print(f"Registering voter {voter_id}...")

        # Register voter in blockchain
        if not blockchain.register_voter(voter_id, public_key):
            return jsonify({'error': 'Voter already registered'}), 400

        # Store voter info
        voters_db[voter_id] = {
            'voter_id': voter_id,
            'name': name,
            'email': email,
            'student_id': student_id,
            'department': department,
            'public_key': public_key,
            'registration_date': datetime.now().isoformat(),
            'has_voted': False
        }

        print(f"Voter {voter_id} registered successfully")

        return jsonify({
            'success': True,
            'voter_id': voter_id,
            'private_key': private_key,
            'public_key': public_key,
            'message': 'Registration successful. Save your private key!'
        }), 201

    except Exception as e:
        print(f"Registration error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/login', methods=['POST'])
def login():
    """Login voter"""
    try:
        data = request.json
        voter_id = data.get('voter_id')

        # Check if it's a test voter
        for test_voter in app.test_voters:
            if voter_id == test_voter['voter_id']:
                session['voter_id'] = voter_id
                session['voter_name'] = test_voter['name']
                session['is_test'] = True
                return jsonify({
                    'success': True,
                    'voter_id': voter_id,
                    'name': test_voter['name'],
                    'is_test': True
                })

        # Check regular voter
        if voter_id in voters_db:
            session['voter_id'] = voter_id
            session['voter_name'] = voters_db[voter_id]['name']
            session['is_test'] = False
            return jsonify({
                'success': True,
                'voter_id': voter_id,
                'name': voters_db[voter_id]['name'],
                'is_test': False
            })
        else:
            return jsonify({'error': 'Voter not found. Please register first.'}), 404

    except Exception as e:
        print(f"Login error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/vote', methods=['POST'])
def cast_vote():
    """Cast a vote with private key"""
    try:
        data = request.json
        voter_id = data.get('voter_id')
        candidate_id = data.get('candidate_id')
        private_key = data.get('private_key')

        print(f"Processing vote: {voter_id} for {candidate_id}")

        if not all([voter_id, candidate_id, private_key]):
            return jsonify({'error': 'Missing required fields'}), 400

        # Clean the private key
        private_key = private_key.strip()

        # Check if voter exists in blockchain
        if voter_id not in blockchain.voters:
            return jsonify({'error': 'Voter not registered in blockchain'}), 404

        # Check if voter has already voted
        voter_status = blockchain.get_voter_status(voter_id)
        if voter_status['has_voted']:
            return jsonify({
                'error': 'You have already voted',
                'status': voter_status
            }), 400

        # Check if candidate exists
        if candidate_id not in blockchain.candidates:
            return jsonify({'error': 'Candidate not found'}), 404

        # Sign the vote
        print(f"Signing vote for {voter_id}...")
        try:
            signature = sign_vote(private_key, voter_id, candidate_id)
            print(f"Signature generated: {signature[:50]}...")
        except Exception as e:
            print(f"Signing error: {e}")
            return jsonify({'error': f'Invalid private key: {str(e)}'}), 400

        # Add vote to blockchain
        if blockchain.add_vote(voter_id, candidate_id, signature):
            print(f"Vote added to blockchain for {voter_id}")

            # Update voter status in database
            if voter_id in voters_db:
                voters_db[voter_id]['has_voted'] = True

            return jsonify({
                'success': True,
                'message': 'Vote cast successfully!',
                'signature': signature,
                'voter_status': blockchain.get_voter_status(voter_id)
            })
        else:
            return jsonify({'error': 'Failed to cast vote. Please try again.'}), 400

    except Exception as e:
        print(f"Vote casting error: {e}")
        return jsonify({'error': f'Vote failed: {str(e)}'}), 500


@app.route('/api/results', methods=['GET'])
def get_results():
    """Get election results"""
    try:
        results = blockchain.get_results()
        return jsonify({
            'success': True,
            'results': results
        })
    except Exception as e:
        print(f"Results error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/chain', methods=['GET'])
def get_chain():
    """Get blockchain data"""
    try:
        chain_data = blockchain.get_chain_data()
        return jsonify({
            'success': True,
            'chain': chain_data,
            'length': len(chain_data),
            'pending_votes': len(blockchain.pending_votes)
        })
    except Exception as e:
        print(f"Chain error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/candidates', methods=['GET'])
def get_candidates():
    """Get list of candidates"""
    try:
        candidates = list(blockchain.candidates.values())
        return jsonify({
            'success': True,
            'candidates': candidates
        })
    except Exception as e:
        print(f"Candidates error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/voter/status', methods=['GET'])
def get_voter_status():
    """Get voter's voting status"""
    try:
        voter_id = request.args.get('voter_id')
        if not voter_id:
            return jsonify({'error': 'Voter ID required'}), 400

        status = blockchain.get_voter_status(voter_id)
        return jsonify({
            'success': True,
            'status': status
        })
    except Exception as e:
        print(f"Voter status error: {e}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    """Admin login"""
    try:
        data = request.json
        password = data.get('password')

        # Simple admin password
        if password == 'admin123':
            session['is_admin'] = True
            return jsonify({'success': True, 'message': 'Admin login successful'})
        else:
            return jsonify({'error': 'Invalid admin password'}), 401

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/stats', methods=['GET'])
def admin_stats():
    """Get admin statistics"""
    try:
        if not verify_admin():
            return jsonify({'error': 'Unauthorized'}), 401

        stats = {
            'total_voters': len(blockchain.voters),
            'voters_voted': sum(1 for v in voters_db.values() if v.get('has_voted', False)),
            'total_candidates': len(blockchain.candidates),
            'blocks_mined': len(blockchain.chain) - 1,
            'pending_votes': len(blockchain.pending_votes),
            'chain_valid': blockchain.is_chain_valid(),
            'difficulty': blockchain.difficulty,
            'nodes': len(blockchain.nodes)
        }

        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/mine', methods=['POST'])
def mine_block():
    """Mine pending votes (admin only)"""
    try:
        if not verify_admin():
            return jsonify({'error': 'Unauthorized'}), 401

        block = blockchain.mine_pending_votes()

        if block:
            return jsonify({
                'success': True,
                'message': f'Block #{block.index} mined successfully',
                'block': {
                    'index': block.index,
                    'hash': block.hash,
                    'transactions': len(block.transactions)
                }
            })
        else:
            return jsonify({'error': 'No pending votes to mine'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/add-candidate', methods=['POST'])
def add_candidate():
    """Add new candidate (admin only)"""
    try:
        if not verify_admin():
            return jsonify({'error': 'Unauthorized'}), 401

        data = request.json
        candidate_id = data.get('candidate_id')
        name = data.get('name')
        party = data.get('party')

        if not all([candidate_id, name, party]):
            return jsonify({'error': 'Missing required fields'}), 400

        if blockchain.register_candidate(candidate_id, name, party):
            return jsonify({
                'success': True,
                'message': 'Candidate added successfully'
            })
        else:
            return jsonify({'error': 'Candidate already exists'}), 400

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/system-info', methods=['GET'])
def system_info():
    """Get system information"""
    try:
        return jsonify({
            'success': True,
            'system': {
                'name': 'Blockchain Voting System',
                'version': '1.0.0',
                'status': 'running',
                'test_voters': [v['voter_id'] for v in app.test_voters],
                'candidates': list(blockchain.candidates.keys())
            }
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# Frontend routes
@app.route('/login')
def login_page():
    return render_template('login.html')


@app.route('/register')
def register_page():
    return render_template('register.html')


@app.route('/vote')
def vote_page():
    return render_template('vote.html')


@app.route('/results')
def results_page():
    return render_template('results.html')


@app.route('/admin')
def admin_page():
    return render_template('admin.html')


if __name__ == '__main__':
    # Create static directory if it doesn't exist
    if not os.path.exists('backend/static'):
        os.makedirs('backend/static')

    print("\n" + "=" * 60)
    print("🚀 BLOCKCHAIN VOTING SYSTEM - READY TO GO!")
    print("=" * 60)
    print("\n🌐 AVAILABLE ROUTES:")
    print("  • Home:           http://localhost:5000")
    print("  • Login:          http://localhost:5000/login")
    print("  • Register:       http://localhost:5000/register")
    print("  • Vote:           http://localhost:5000/vote")
    print("  • Results:        http://localhost:5000/results")
    print("  • Admin:          http://localhost:5000/admin")

    print("\n🔑 TEST VOTERS (EASY DEMO):")
    for voter in app.test_voters:
        print(f"  • Voter ID: {voter['voter_id']}")
        print(f"    Name: {voter['name']}")
        print(f"    Private Key: {voter['private_key'][:50]}...")
        print()

    print("🎯 QUICK START:")
    print("  1. Go to http://localhost:5000/login")
    print("  2. Login with TEST001, TEST002, or TEST003")
    print("  3. Click 'Use Test Credentials'")
    print("  4. Select candidate and click 'Submit Vote'")
    print("  5. Go to Admin panel to mine block (password: admin123)")
    print("  6. View results in real-time!")

    print("\n🛠️ ADMIN PANEL:")
    print("  • URL: http://localhost:5000/admin")
    print("  • Password: admin123")
    print("  • Mine blocks to confirm votes")

    print("=" * 60 + "\n")

    app.run(debug=True, port=5000, host='0.0.0.0')