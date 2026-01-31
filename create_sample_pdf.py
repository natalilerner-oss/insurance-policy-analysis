from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

def create_sample_policy_pdf(filename):
    c = canvas.Canvas(filename, pagesize=letter)
    c.drawString(100, 750, "Sample Insurance Policy")
    c.drawString(100, 730, "Policy Number: 123456789")
    c.drawString(100, 710, "Insured: John Doe")
    c.drawString(100, 690, "Coverage: Health Insurance")
    c.drawString(100, 670, "Premium: $100 per month")
    c.drawString(100, 650, "Effective Date: 2024-01-01")
    c.save()

if __name__ == "__main__":
    create_sample_policy_pdf("sample_policy.pdf")