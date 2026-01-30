#!/usr/bin/env python3
"""
Local test script for Insurance Portfolio Excel generation
"""

import sys
import os
from datetime import date
from decimal import Decimal

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from insurance_portfolio_schema import InsurancePortfolioRequest, FamilyMember, InsuranceProduct, Coverage
from insurance_portfolio_generator import generate_insurance_portfolio

def create_sample_data() -> InsurancePortfolioRequest:
    """Create sample insurance portfolio data for testing"""

    # Sample family members
    family_members = [
        FamilyMember(name="ראובן ישראלי", role="ראש משפחה"),
        FamilyMember(name="שרה ישראלי", role="בת זוג"),
        FamilyMember(name="יעקב ישראלי", role="בן")
    ]

    # Sample insurance products
    insurance_products = [
        # Health insurance with coverage breakdown
        InsuranceProduct(
            member_name="ראובן ישראלי",
            policy_number="12345678",
            start_date=date(2020, 10, 1),
            company="הראל",
            product_name="בריאות",
            coverages=[
                Coverage(name="ניתוחים שקל ראשון", premium=Decimal("101.04")),
                Coverage(name="תרופות מיוחדות", premium=Decimal("24.35")),
                Coverage(name="השתלות וטיפולים בחו\"ל", premium=Decimal("19.70"))
            ],
            exclusions="מחלת כבד קודמת",
            discounts="15% עד 06/2026"
        ),

        # Critical illness insurance
        InsuranceProduct(
            member_name="שרה ישראלי",
            policy_number="87654321",
            start_date=date(2019, 3, 15),
            company="פניקס",
            product_name="מחלות קשות",
            details="סכום ביטוח 1,000,000 ₪",
            premium=Decimal("89.50")
        ),

        # Life insurance
        InsuranceProduct(
            member_name="ראובן ישראלי",
            policy_number="11223344",
            start_date=date(2018, 7, 1),
            company="מגדל",
            product_name="ביטוח חיים",
            details="סכום ביטוח 2,500,000 ₪",
            premium=Decimal("156.75")
        ),

        # Disability insurance
        InsuranceProduct(
            member_name="ראובן ישראלי",
            policy_number="55667788",
            start_date=date(2021, 1, 10),
            company="כלל",
            product_name="אכ\"ע",
            details="ימי המתנה 90, סכום ביטוח 10,000 ₪",
            premium=Decimal("67.20")
        ),

        # Personal accident insurance
        InsuranceProduct(
            member_name="שרה ישראלי",
            policy_number="99001122",
            start_date=date(2022, 5, 20),
            company="הראל",
            product_name="תאונות אישיות",
            details="מוות/נכות מתאונה - סכום ביטוח 500,000 ₪",
            premium=Decimal("45.30")
        )
    ]

    return InsurancePortfolioRequest(
        family_name="ישראלי",
        report_date=date(2024, 1, 15),
        family_members=family_members,
        insurance_products=insurance_products
    )

def main():
    print("🧪 Testing Insurance Portfolio Excel Generation")
    print("=" * 50)

    try:
        # Create sample data
        print("📋 Creating sample insurance portfolio data...")
        data = create_sample_data()

        print(f"👨‍👩‍👧‍👦 Family: {data.family_name}")
        print(f"📅 Report Date: {data.report_date}")
        print(f"👥 Family Members: {len(data.family_members)}")
        print(f"📄 Insurance Products: {len(data.insurance_products)}")

        # Generate Excel
        print("\n📊 Generating Excel file...")
        excel_bytes = generate_insurance_portfolio(data)

        # Save to file
        output_filename = f"test_portfolio_{data.family_name}_{data.report_date}.xlsx"
        with open(output_filename, 'wb') as f:
            f.write(excel_bytes.getvalue())

        print(f"✅ Excel file generated successfully: {output_filename}")

        # Calculate totals for verification
        total_premium = sum(
            sum(c.premium for c in p.coverages) if p.coverages else (p.premium or 0)
            for p in data.insurance_products
        )

        print("\n📈 Summary:")
        print(f"   • Total Monthly Premium: ₪{total_premium:.2f}")
        print(f"   • Products with Coverage Breakdown: {sum(1 for p in data.insurance_products if p.coverages)}")
        print(f"   • Simple Products: {sum(1 for p in data.insurance_products if not p.coverages)}")

        print("\n🎯 Test completed successfully!")
        print(f"📁 Open '{output_filename}' to view the generated Excel report")

    except Exception as e:
        print(f"❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())