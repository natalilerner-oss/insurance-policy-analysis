#!/usr/bin/env python3
"""
Test script for email service functionality.
"""

import sys
import os
from unittest.mock import patch, MagicMock

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from email_service import send_portfolio_email, create_portfolio_email_html


def test_email_html_generation():
    """Test that HTML email is generated correctly with Hebrew content"""
    print("Testing HTML email generation...")
    
    html = create_portfolio_email_html(
        family_name="ישראלי",
        download_link="https://example.com/download/portfolio.xlsx",
        total_premium=1500.50,
        products_count=5,
        report_date="2024-01-15"
    )
    
    # Check for key elements
    assert "ישראלי" in html, "Family name not found in HTML"
    assert "1,500.50" in html, "Total premium not formatted correctly"
    assert "5" in html, "Products count not found"
    assert "2024-01-15" in html, "Report date not found"
    assert "https://example.com/download/portfolio.xlsx" in html, "Download link not found"
    assert 'dir="rtl"' in html, "RTL direction not set"
    assert 'lang="he"' in html, "Hebrew language not set"
    
    print("✅ HTML generation test passed")


def test_send_email_without_sendgrid():
    """Test email sending when SendGrid is not configured"""
    print("\nTesting email without SendGrid configuration...")
    
    # Ensure SENDGRID_API_KEY is not set
    with patch.dict(os.environ, {}, clear=False):
        if 'SENDGRID_API_KEY' in os.environ:
            del os.environ['SENDGRID_API_KEY']
        
        result = send_portfolio_email(
            recipient_email="test@example.com",
            family_name="ישראלי",
            download_link="https://example.com/download/portfolio.xlsx",
            total_premium=1500.50,
            products_count=5,
            report_date="2024-01-15"
        )
        
        assert result["success"] is False, "Should fail when SendGrid not configured"
        assert "not configured" in result["message"], "Should mention configuration issue"
        
    print("✅ SendGrid not configured test passed")


def test_send_email_with_mock_sendgrid():
    """Test email sending with mocked SendGrid"""
    print("\nTesting email with mocked SendGrid...")
    
    # Mock SendGrid
    mock_response = MagicMock()
    mock_response.status_code = 202
    
    with patch.dict(os.environ, {
        'SENDGRID_API_KEY': 'test_key_12345',
        'SENDER_EMAIL': 'test@insurance-policy-analysis.com'
    }):
        with patch('email_service.SendGridAPIClient') as mock_sg:
            mock_sg.return_value.send.return_value = mock_response
            
            result = send_portfolio_email(
                recipient_email="test@example.com",
                family_name="ישראלי",
                download_link="https://example.com/download/portfolio.xlsx",
                total_premium=1500.50,
                products_count=5,
                report_date="2024-01-15"
            )
            
            assert result["success"] is True, f"Should succeed with mocked SendGrid: {result}"
            assert result["status_code"] == 202, "Should return 202 status"
            
            # Verify SendGrid was called
            assert mock_sg.called, "SendGrid client should be instantiated"
            assert mock_sg.return_value.send.called, "SendGrid send should be called"
    
    print("✅ Mocked SendGrid test passed")


def test_send_email_with_sendgrid_error():
    """Test email sending when SendGrid fails"""
    print("\nTesting email with SendGrid error...")
    
    with patch.dict(os.environ, {
        'SENDGRID_API_KEY': 'test_key_12345',
        'SENDER_EMAIL': 'test@insurance-policy-analysis.com'
    }):
        with patch('email_service.SendGridAPIClient') as mock_sg:
            mock_sg.return_value.send.side_effect = Exception("API Error: Invalid API key")
            
            result = send_portfolio_email(
                recipient_email="test@example.com",
                family_name="ישראלי",
                download_link="https://example.com/download/portfolio.xlsx",
                total_premium=1500.50,
                products_count=5,
                report_date="2024-01-15"
            )
            
            assert result["success"] is False, "Should fail when SendGrid raises exception"
            assert "API Error" in result["error"], "Should include error message"
    
    print("✅ SendGrid error test passed")


def main():
    print("🧪 Testing Email Service")
    print("=" * 50)
    
    try:
        test_email_html_generation()
        test_send_email_without_sendgrid()
        test_send_email_with_mock_sendgrid()
        test_send_email_with_sendgrid_error()
        
        print("\n" + "=" * 50)
        print("🎯 All tests passed successfully!")
        return 0
        
    except AssertionError as e:
        print(f"\n❌ Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
