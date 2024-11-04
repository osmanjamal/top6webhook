import os
import sys

# إضافة المسار للـ PYTHONPATH
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)

import typer
from components.config.security import SecurityConfig

app = typer.Typer()

@app.command()
def set_credentials(
    api_key: str = typer.Option(..., prompt=True),
    api_secret: str = typer.Option(..., prompt=True, hide_input=True),
    testnet: bool = typer.Option(False, prompt=True),
):
    """تعيين بيانات اعتماد Binance"""
    config = SecurityConfig.load_credentials()
    config['binance_futures']['api_key'] = api_key
    config['binance_futures']['api_secret'] = api_secret
    config['binance_futures']['testnet'] = testnet
    SecurityConfig.save_credentials(config)
    print("Credentials saved successfully!")

@app.command()
def add_ip(ip: str = typer.Option(..., prompt=True)):
    """إضافة عنوان IP مسموح به"""
    config = SecurityConfig.load_credentials()
    if ip not in config['binance_futures']['allowed_ips']:
        config['binance_futures']['allowed_ips'].append(ip)
        SecurityConfig.save_credentials(config)
        print(f"IP {ip} added successfully!")
    else:
        print(f"IP {ip} already exists!")

@app.command()
def test_connection():
    """اختبار اتصال API مع Binance"""
    try:
        # اختبار تحميل الإعدادات
        config = SecurityConfig.load_credentials()
        print("\nتم تحميل الإعدادات بنجاح:")
        print(f"API Key: {'موجود' if config['binance_futures']['api_key'] else 'غير موجود'}")
        print(f"API Secret: {'موجود' if config['binance_futures']['api_secret'] else 'غير موجود'}")
        print(f"Testnet Mode: {'مفعل' if config['binance_futures']['testnet'] else 'غير مفعل'}")
        print(f"Allowed IPs: {config['binance_futures']['allowed_ips']}")

        # اختبار الاتصال مع Binance
        try:
            from components.actions.community_created_actions.crypto.binance_futures import BinanceFutures
            binance = BinanceFutures()
            test_result = binance.test_api_connection()
            print("\nنتيجة اختبار الاتصال مع Binance:")
            print(test_result)
        except ImportError:
            print("\nتحذير: لم يتم العثور على ملف BinanceFutures. تأكد من وجود الملف في المسار الصحيح.")
        
    except Exception as e:
        print(f"\nخطأ: {str(e)}")

@app.command()
def remove_ip(ip: str = typer.Option(..., prompt=True)):
    """إزالة عنوان IP"""
    config = SecurityConfig.load_credentials()
    if ip in config['binance_futures']['allowed_ips']:
        config['binance_futures']['allowed_ips'].remove(ip)
        SecurityConfig.save_credentials(config)
        print(f"IP {ip} removed successfully!")
    else:
        print(f"IP {ip} not found!")

@app.command()
def list_ips():
    """عرض قائمة عناوين IP المسموح بها"""
    config = SecurityConfig.load_credentials()
    ips = config['binance_futures']['allowed_ips']
    if ips:
        print("\nAllowed IPs:")
        for ip in ips:
            print(f"- {ip}")
    else:
        print("No IPs configured!")

if __name__ == "__main__":
    app()
    