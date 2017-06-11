from app import db

class BalanceTransactions(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	amount = db.Column(db.Integer)
	available_on = db.Column(db.DateTime)
	created = db.Column(db.DateTime)
	currency = db.Column(db.Text)
