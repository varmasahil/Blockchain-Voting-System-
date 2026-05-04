from datetime import datetime
import json


class Voter:
    def __init__(self, voter_id: str, name: str, email: str, public_key: str,
                 student_id: str = None, department: str = None):
        self.voter_id = voter_id
        self.name = name
        self.email = email
        self.public_key = public_key
        self.student_id = student_id
        self.department = department
        self.registration_date = datetime.now().isoformat()
        self.has_voted = False

    def to_dict(self):
        return {
            'voter_id': self.voter_id,
            'name': self.name,
            'email': self.email,
            'student_id': self.student_id,
            'department': self.department,
            'registration_date': self.registration_date,
            'has_voted': self.has_voted
        }


class Candidate:
    def __init__(self, candidate_id: str, name: str, party: str, description: str = ""):
        self.candidate_id = candidate_id
        self.name = name
        self.party = party
        self.description = description
        self.votes = 0

    def to_dict(self):
        return {
            'candidate_id': self.candidate_id,
            'name': self.name,
            'party': self.party,
            'description': self.description,
            'votes': self.votes
        }


class Election:
    def __init__(self, election_id: str, title: str, start_date: str, end_date: str):
        self.election_id = election_id
        self.title = title
        self.start_date = start_date
        self.end_date = end_date
        self.is_active = False
        self.total_voters = 0
        self.total_votes = 0

    def to_dict(self):
        return {
            'election_id': self.election_id,
            'title': self.title,
            'start_date': self.start_date,
            'end_date': self.end_date,
            'is_active': self.is_active,
            'total_voters': self.total_voters,
            'total_votes': self.total_votes
        }