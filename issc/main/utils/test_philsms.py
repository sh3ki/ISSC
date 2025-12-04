"""Simple test for the PhilSMS helper.

Run this from the project root with the virtualenv activated. Example:

powershell
cd 'C:/Users/USER/Downloads/ISSC-Django-main/issc'
..\venv\Scripts\Activate.ps1
python -m main.utils.philsms --sync

Or run this script directly using the package import below:
python -m main.utils.test_philsms

This script sends a test SMS to `09945349194` by default.
"""

from main.utils.philsms import send_sms_sync


def main():
    to = '09945349194'
    message = 'ISSC System\nUnauthorized person detected in Camera 1 - TEST'
    print(f"Sending test SMS to {to} (synchronous)...")
    # Try verbose sync first so we can inspect provider response
    try:
        from main.utils.philsms import send_sms_sync_verbose
        ok, status, body = send_sms_sync_verbose(to, message)
        print('Verbose result ->', ok, status)
        print('Response body:', body)
    except Exception:
        ok = send_sms_sync(to, message)
        print('Result:', ok)


if __name__ == '__main__':
    main()
