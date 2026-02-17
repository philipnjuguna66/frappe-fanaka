import frappe
from frappe.model.document import Document

class LandSale(Document):
    def validate(self):
        self.calculate_totals()
    
    def calculate_totals(self):
        self.grand_total = self.price - (self.discount or 0) + (self.interest or 0)
        total_penalties = sum([d.amount for d in self.penalties])
        self.grand_total += total_penalties
