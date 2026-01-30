from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter
from io import BytesIO
from decimal import Decimal
from typing import List
from insurance_portfolio_schema import InsurancePortfolioRequest, InsuranceProduct, Coverage

# Hebrew Terminology Reference
INSURANCE_COMPANIES = {
    "harel": "הראל",
    "phoenix": "פניקס",
    "migdal": "מגדל",
    "clal": "כלל",
    "menora": "מנורה",
    "ayalon": "איילון"
}

INSURANCE_PRODUCTS = {
    "health": "בריאות",
    "critical_illness": "מחלות קשות",
    "life": "ביטוח חיים",
    "disability": "אכ\"ע",
    "personal_accident": "תאונות אישיות",
    "service_letter": "כתב שירות"
}

HEALTH_COVERAGES = {
    "surgeries_first_shekel": "ניתוחים שקל ראשון",
    "surgery_alternatives": "טיפולי מחליפי ניתוח",
    "transplants_abroad": "השתלות וטיפולים בחו\"ל",
    "medical_consultation": "ייעוץ רפואי",
    "special_medications": "תרופות מיוחדות",
    "personal_physician": "רופא מלווה אישי",
    "surgeries_abroad": "ביטוח לניתוחים בחו\"ל",
    "ambulatory_services": "שירותיים אמבולטורים",
    "premium_medications": "תרופות פרימיום",
    "fast_diagnosis": "אבחון רפואי מהיר",
    "medical_tech_devices": "טיפולי בטכנולוגיות ואביזר רפואי"
}

# Styling
HEADER_FILL = PatternFill(start_color="4F46E5", fill_type="solid")
HEADER_FONT = Font(bold=True, size=11, name="Arial", color="FFFFFF")
DATA_FONT = Font(size=10, name="Arial")
SUBTOTAL_FILL = PatternFill(start_color="E5E7EB", fill_type="solid")
CURRENCY_FORMAT = '₪#,##0.00'
DATE_FORMAT = 'DD/MM/YYYY'

HEADERS = [
    "שם המבוטח",
    "מס פוליסה",
    "תחילת ביטוח",
    "שם חברת ביטוח",
    "שם המוצר",
    "פירוט",
    "פרמיה",
    "החרגות והנחות"
]

def generate_insurance_portfolio(data: InsurancePortfolioRequest) -> BytesIO:
    wb = Workbook()
    ws = wb.active
    ws.title = "ביטוח"
    ws.sheet_view.rightToLeft = True  # RTL for Hebrew

    # Write headers
    for col, header in enumerate(HEADERS, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.alignment = Alignment(horizontal="center", vertical="center")

    # Write data
    row = 2
    for product in data.insurance_products:
        row = _write_product(ws, row, product)

    # Grand total
    if row > 2:
        ws.cell(row=row, column=6, value="סה\"כ פרמיה חודשית")
        total_formula = f"=SUM(G2:G{row-1})"
        ws.cell(row=row, column=7, value=total_formula).number_format = CURRENCY_FORMAT
        ws.cell(row=row, column=7).font = Font(bold=True)
        ws.cell(row=row, column=7).fill = SUBTOTAL_FILL

    # Auto-fit columns
    _auto_fit_columns(ws)

    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return output

def _write_product(ws, start_row: int, product: InsuranceProduct) -> int:
    """Write a single insurance product, return next row number"""
    row = start_row

    if product.coverages:
        # Health-type product with coverage breakdown
        for i, coverage in enumerate(product.coverages):
            if i == 0:
                # First row includes all product info
                ws.cell(row=row, column=1, value=product.member_name)
                ws.cell(row=row, column=2, value=product.policy_number)
                ws.cell(row=row, column=3, value=product.start_date).number_format = DATE_FORMAT
                ws.cell(row=row, column=4, value=product.company)
                ws.cell(row=row, column=5, value=product.product_name)

            ws.cell(row=row, column=6, value=coverage.name)
            ws.cell(row=row, column=7, value=float(coverage.premium)).number_format = CURRENCY_FORMAT

            if i == 0 and (product.exclusions or product.discounts):
                exclusions_discounts = []
                if product.exclusions:
                    exclusions_discounts.append(product.exclusions)
                if product.discounts:
                    exclusions_discounts.append(product.discounts)
                ws.cell(row=row, column=8, value=" | ".join(exclusions_discounts))

            row += 1

        # Subtotal row
        total = sum(c.premium for c in product.coverages)
        ws.cell(row=row, column=6, value="סה\"כ")
        ws.cell(row=row, column=7, value=float(total)).number_format = CURRENCY_FORMAT
        ws.cell(row=row, column=7).fill = SUBTOTAL_FILL
        ws.cell(row=row, column=7).font = Font(bold=True)
        row += 1
    else:
        # Simple product (life, critical illness, etc.)
        ws.cell(row=row, column=1, value=product.member_name)
        ws.cell(row=row, column=2, value=product.policy_number)
        ws.cell(row=row, column=3, value=product.start_date).number_format = DATE_FORMAT
        ws.cell(row=row, column=4, value=product.company)
        ws.cell(row=row, column=5, value=product.product_name)
        ws.cell(row=row, column=6, value=product.details)
        ws.cell(row=row, column=7, value=float(product.premium or 0)).number_format = CURRENCY_FORMAT

        exclusions_discounts = []
        if product.exclusions:
            exclusions_discounts.append(product.exclusions)
        if product.discounts:
            exclusions_discounts.append(product.discounts)
        if exclusions_discounts:
            ws.cell(row=row, column=8, value=" | ".join(exclusions_discounts))

        row += 1

    return row

def _auto_fit_columns(ws):
    """Auto-fit column widths based on content"""
    for col in range(1, len(HEADERS) + 1):
        max_length = 0
        column_letter = get_column_letter(col)

        for row in range(1, ws.max_row + 1):
            cell = ws.cell(row=row, column=col)
            if cell.value:
                max_length = max(max_length, len(str(cell.value)))

        # Set minimum width
        adjusted_width = max(max_length + 2, 10)
        ws.column_dimensions[column_letter].width = adjusted_width