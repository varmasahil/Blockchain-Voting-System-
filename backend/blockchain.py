import hashlib
import json
import time
from datetime import datetime
from uuid import uuid4
from typing import List, Dict, Any
import base64

# Use simpler cryptography approach
import rsa  # Install: pip install rsa


class Block:
    def __init__(self, index: int, transactions: List[Dict], timestamp: float,
                 previous_hash: str, nonce: int = 0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.compute_hash()

    def compute_hash(self) -> str:
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def to_dict(self):
        return {
            'index': self.index,
            'transactions': self.transactions,
            'timestamp': self.timestamp,
            'previous_hash': self.previous_hash,
            'hash': self.hash,
            'nonce': self.nonce
        }

    def __repr__(self):
        return f"Block(Index: {self.index}, Hash: {self.hash[:10]}..., Transactions: {len(self.transactions)})"


class VotingBlockchain:
    def __init__(self):
        self.chain = []
        self.pending_votes = []
        self.voters = {}  # voter_id: public_key_string
        self.candidates = {}  # candidate_id: candidate_data
        self.nodes = set()
        self.difficulty = 2  # Reduced for faster mining
        self.create_genesis_block()

    def create_genesis_block(self):
        """Create the first block in the chain"""
        genesis_block = Block(0, [], time.time(), "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

    @property
    def last_block(self) -> Block:
        return self.chain[-1]

    def add_vote(self, voter_id: str, candidate_id: str, signature: str) -> bool:
        """Add a vote to pending transactions after verification"""
        # Check if voter exists
        if voter_id not in self.voters:
            print(f"Voter {voter_id} not found in voters list")
            return False

        # Check if candidate exists
        if candidate_id not in self.candidates:
            print(f"Candidate {candidate_id} not found")
            return False

        # Check if voter has already voted
        if self.has_voted(voter_id):
            print(f"Voter {voter_id} has already voted")
            return False

        # Verify signature
        if not self.verify_signature(voter_id, candidate_id, signature):
            print(f"Signature verification failed for voter {voter_id}")
            return False

        vote_transaction = {
            'voter_id': voter_id,
            'candidate_id': candidate_id,
            'signature': signature,
            'timestamp': time.time()
        }

        self.pending_votes.append(vote_transaction)
        print(f"Vote added to pending: {vote_transaction}")
        return True

    def has_voted(self, voter_id: str) -> bool:
        """Check if voter has voted in any block"""
        # Check pending votes
        for vote in self.pending_votes:
            if vote['voter_id'] == voter_id:
                return True

        # Check confirmed votes in blockchain
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.get('voter_id') == voter_id:
                    return True
        return False

    def verify_signature(self, voter_id: str, candidate_id: str, signature: str) -> bool:
        """Verify digital signature of a vote"""
        try:
            if voter_id not in self.voters:
                print(f"Voter {voter_id} not registered")
                return False

            public_key_str = self.voters[voter_id]

            # Load public key
            try:
                public_key = rsa.PublicKey.load_pkcs1(public_key_str.encode())
            except:
                # Try loading as PEM
                public_key = rsa.PublicKey.load_pkcs1_openssl_pem(public_key_str.encode())

            # Create the message that was signed
            message = f"{voter_id}:{candidate_id}"
            message_bytes = message.encode('utf-8')

            # Decode signature from base64
            signature_bytes = base64.b64decode(signature)

            # Verify signature
            try:
                rsa.verify(message_bytes, signature_bytes, public_key)
                print(f"Signature verified successfully for {voter_id}")
                return True
            except rsa.VerificationError:
                print(f"Invalid signature for voter {voter_id}")
                return False

        except Exception as e:
            print(f"Signature verification error: {e}")
            return False

    def mine_pending_votes(self, miner_address: str = "system") -> Block:
        """Mine pending votes into a new block"""
        if not self.pending_votes:
            print("No pending votes to mine")
            return None

        print(f"Mining {len(self.pending_votes)} pending votes...")

        last_block = self.last_block
        new_block = Block(
            index=last_block.index + 1,
            transactions=self.pending_votes.copy(),
            timestamp=time.time(),
            previous_hash=last_block.hash,
            nonce=0
        )

        # Proof of Work
        proof = self.proof_of_work(new_block)

        # Add block to chain
        self.chain.append(new_block)

        # Clear pending votes
        self.pending_votes = []

        print(f"Block #{new_block.index} mined successfully with {len(new_block.transactions)} transactions")
        return new_block

    def proof_of_work(self, block: Block) -> int:
        """Simple Proof of Work algorithm"""
        block.nonce = 0
        computed_hash = block.compute_hash()

        print(f"Mining block #{block.index}...")

        while not computed_hash.startswith('0' * self.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        block.hash = computed_hash
        print(f"Block mined! Nonce: {block.nonce}, Hash: {computed_hash[:20]}...")
        return block.nonce

    def is_chain_valid(self) -> bool:
        """Validate the entire blockchain"""
        for i in range(1, len(self.chain)):
            current_block = self.chain[i]
            previous_block = self.chain[i - 1]

            # Check hash integrity
            if current_block.hash != current_block.compute_hash():
                print(f"Block {current_block.index} hash is invalid!")
                return False

            # Check previous hash reference
            if current_block.previous_hash != previous_block.hash:
                print(f"Block {current_block.index} previous hash is invalid!")
                return False

        print("Blockchain validation successful!")
        return True

    def register_voter(self, voter_id: str, public_key: str) -> bool:
        """Register a new voter"""
        if voter_id in self.voters:
            print(f"Voter {voter_id} already registered")
            return False

        self.voters[voter_id] = public_key
        print(f"Voter {voter_id} registered successfully")
        return True

    def register_candidate(self, candidate_id: str, name: str, party: str) -> bool:
        """Register a new candidate"""
        if candidate_id in self.candidates:
            return False

        self.candidates[candidate_id] = {
            'id': candidate_id,
            'name': name,
            'party': party,
            'votes': 0
        }
        print(f"Candidate {name} ({candidate_id}) registered")
        return True

    def get_results(self) -> Dict:
        """Calculate election results from blockchain"""
        results = {candidate_id: 0 for candidate_id in self.candidates}

        # Count votes from blockchain
        for block in self.chain:
            for transaction in block.transactions:
                candidate_id = transaction.get('candidate_id')
                if candidate_id in results:
                    results[candidate_id] += 1

        # Count pending votes
        for vote in self.pending_votes:
            candidate_id = vote.get('candidate_id')
            if candidate_id in results:
                results[candidate_id] += 1

        # Update candidate objects with vote counts
        for candidate_id, votes in results.items():
            if candidate_id in self.candidates:
                self.candidates[candidate_id]['votes'] = votes

        return {
            'candidates': list(self.candidates.values()),
            'total_votes': sum(results.values()),
            'blocks_mined': len(self.chain) - 1,  # Exclude genesis block
            'chain_valid': self.is_chain_valid(),
            'pending_votes': len(self.pending_votes)
        }

    def get_voter_status(self, voter_id: str) -> Dict:
        """Check if voter has voted and get their vote"""
        # Check blockchain
        for block in self.chain:
            for transaction in block.transactions:
                if transaction.get('voter_id') == voter_id:
                    return {
                        'has_voted': True,
                        'candidate_id': transaction.get('candidate_id'),
                        'block_index': block.index,
                        'timestamp': transaction.get('timestamp'),
                        'status': 'confirmed'
                    }

        # Check pending votes
        for vote in self.pending_votes:
            if vote.get('voter_id') == voter_id:
                return {
                    'has_voted': True,
                    'candidate_id': vote.get('candidate_id'),
                    'status': 'pending',
                    'timestamp': vote.get('timestamp')
                }

        return {'has_voted': False, 'voter_id': voter_id}

    def get_chain_data(self) -> List[Dict]:
        """Get blockchain data for display"""
        chain_data = []
        for block in self.chain:
            chain_data.append({
                'index': block.index,
                'hash': block.hash,
                'previous_hash': block.previous_hash,
                'timestamp': block.timestamp,
                'nonce': block.nonce,
                'transactions': block.transactions,
                'transaction_count': len(block.transactions)
            })
        return chain_data


# Helper functions for key generation using rsa library
def generate_key_pair():
    """Generate RSA key pair for voters using rsa library"""
    try:
        # Generate key pair
        (public_key, private_key) = rsa.newkeys(512)  # 512 bits for faster testing

        # Convert to strings
        private_key_str = private_key.save_pkcs1().decode('utf-8')
        public_key_str = public_key.save_pkcs1().decode('utf-8')

        print("Key pair generated successfully")
        return private_key_str, public_key_str

    except Exception as e:
        print(f"Error generating key pair: {e}")
        raise


def sign_vote(private_key_str: str, voter_id: str, candidate_id: str) -> str:
    """Sign a vote with private key"""
    try:
        # Load private key from string
        private_key = rsa.PrivateKey.load_pkcs1(private_key_str.encode())

        # Create message to sign
        message = f"{voter_id}:{candidate_id}"
        message_bytes = message.encode('utf-8')

        # Sign the message
        signature = rsa.sign(message_bytes, private_key, 'SHA-256')

        # Encode signature as base64
        signature_b64 = base64.b64encode(signature).decode('utf-8')
        print(f"Vote signed successfully for {voter_id}")
        return signature_b64

    except Exception as e:
        print(f"Error signing vote: {e}")
        raise