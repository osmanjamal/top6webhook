import os
import sys

current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(current_dir)

from components.config.security import SecurityConfig

class SecurityManager:
    @staticmethod
    def test_connection():
        """Test Binance API Connection"""
        try:
            # Test configuration loading
            config = SecurityConfig.load_credentials()
            print("\nBinance API Configuration:")
            print(f"API Key: {'Present' if config['binance_futures']['api_key'] else 'Missing'}")
            print(f"API Secret: {'Present' if config['binance_futures']['api_secret'] else 'Missing'}")
            print(f"Testnet Mode: {'Enabled' if config['binance_futures']['testnet'] else 'Disabled'}")
            print(f"Allowed IPs: {config['binance_futures']['allowed_ips']}")

            # Test Binance connection
            try:
                from components.actions.community_created_actions.crypto.binance_futures import BinanceFutures
                binance = BinanceFutures()
                test_result = binance.test_api_connection()
                print("\nBinance API Connection Test:")
                if test_result.get('status') == 'success':
                    print(f"Status: Connected Successfully")
                    print(f"Account Type: {test_result.get('account_type', 'Unknown')}")
                    print(f"Total Balance USDT: {test_result.get('total_balance_usdt', 0)}")
                    print(f"Available Balance USDT: {test_result.get('available_balance_usdt', 0)}")
                    print(f"Position Initial Margin: {test_result.get('position_initial_margin', 0)}")
                    print(f"Unrealized PNL: {test_result.get('unrealized_pnl', 0)}")
                else:
                    print(f"Status: Connection Failed")
                    print(f"Error: {test_result.get('error', 'Unknown error')}")
                    
            except ModuleNotFoundError:
                print("\nError: BinanceFutures module not found")
                print("Path: src/components/actions/community_created_actions/crypto/binance_futures.py")
            except ImportError as e:
                print(f"\nImport Error: {str(e)}")
                print("Check if all required modules are installed (ccxt, flask, etc.)")
            except Exception as e:
                print(f"\nUnexpected Error: {str(e)}")
                
        except Exception as e:
            print(f"\nConfiguration Error: {str(e)}")

    @staticmethod
    def set_credentials():
        """Set Binance API Credentials"""
        api_key = input("Enter API Key: ")
        api_secret = input("Enter API Secret: ")
        testnet = input("Enable Testnet (y/n)? ").lower() == 'y'

        config = SecurityConfig.load_credentials()
        config['binance_futures']['api_key'] = api_key
        config['binance_futures']['api_secret'] = api_secret
        config['binance_futures']['testnet'] = testnet
        SecurityConfig.save_credentials(config)
        print("Credentials saved successfully!")
        

    @staticmethod
    def add_ip():
        """Add allowed IP address"""
        ip = input("Enter IP address: ")
        config = SecurityConfig.load_credentials()
        if ip not in config['binance_futures']['allowed_ips']:
            config['binance_futures']['allowed_ips'].append(ip)
            SecurityConfig.save_credentials(config)
            print(f"IP {ip} added successfully!")
        else:
            print(f"IP {ip} already exists!")

    @staticmethod
    def list_ips():
        """List allowed IP addresses"""
        config = SecurityConfig.load_credentials()
        ips = config['binance_futures']['allowed_ips']
        if ips:
            print("\nAllowed IPs:")
            for ip in ips:
                print(f"- {ip}")
        else:
            print("No IPs configured!")


    @staticmethod
    def test_order():
        """Test placing a small test order"""
        try:
            from components.actions.community_created_actions.crypto.binance_futures import BinanceFutures
            binance = BinanceFutures()

            # Test data for a very small BTCUSDT order
            test_data = {
                "symbol": "BTCUSDT",
                "side": "buy",
                "amount": 0.001,  # Minimum amount
                "stopLoss": None,
                "takeProfit": None
            }

            print("\nPreparing test order:")
            print(f"Symbol: {test_data['symbol']}")
            print(f"Side: {test_data['side']}")
            print(f"Amount: {test_data['amount']} BTC")
            
            # Get market info first
            market_info = binance.exchange.fetch_ticker("BTCUSDT")
            print(f"Current price: {market_info['last']} USDT")
            
            proceed = input("\nDo you want to proceed with the test order? (yes/no): ")
            
            if proceed.lower() == 'yes':
                order = binance.execute_trade(test_data)
                print("\nOrder executed successfully!")
                print(f"Order ID: {order['id']}")
                print(f"Status: {order['status']}")
                print(f"Filled Amount: {order.get('filled', 0)}")
                print(f"Average Price: {order.get('average', 0)}")
            else:
                print("\nTest order cancelled")
                
        except Exception as e:
            print(f"\nError: {str(e)}")



def main():
    commands = {
        'test-connection': SecurityManager.test_connection,
        'set-credentials': SecurityManager.set_credentials,
        'add-ip': SecurityManager.add_ip,
        'list-ips': SecurityManager.list_ips,
        'test-order': SecurityManager.test_order  # إضافة هذا السطر
    }

    if len(sys.argv) < 2 or sys.argv[1] not in commands:
        print("\nAvailable commands:")
        for cmd in commands.keys():
            print(f"  {cmd}")
        return

    command = sys.argv[1]
    commands[command]()





if __name__ == "__main__":
    main()