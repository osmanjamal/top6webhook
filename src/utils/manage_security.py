import os
import sys
from typing import Dict, Callable
from typing import Dict, Callable


current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if current_dir not in sys.path:
    sys.path.append(current_dir)

from components.config.security import SecurityConfig



class SecurityManager:
    """Manager class for security-related operations"""

    @staticmethod
    def test_connection() -> None:
        """Test Binance API Connection"""
        try:
            config = SecurityConfig.load_credentials()
            print("\nBinance API Configuration:")
            
            # Check credentials presence
            print(
                f"API Key: "
                f"{'Present' if config['binance_futures']['api_key'] else 'Missing'}"
            )
            print(
                f"API Secret: "
                f"{'Present' if config['binance_futures']['api_secret'] else 'Missing'}"
            )
            print(
                f"Testnet Mode: "
                f"{'Enabled' if config['binance_futures']['testnet'] else 'Disabled'}"
            )
            print(f"Allowed IPs: {config['binance_futures']['allowed_ips']}")

            try:
                from components.actions.community_created_actions.crypto import (
                    binance_futures,
                )
                
                binance = binance_futures.BinanceFutures()
                test_result = binance.test_api_connection()
                
                print("\nBinance API Connection Test:")
                if test_result.get('status') == 'success':
                    print("Status: Connected Successfully")
                    print(
                        f"Account Type: "
                        f"{test_result.get('account_type', 'Unknown')}"
                    )
                    print(
                        f"Total Balance USDT: "
                        f"{test_result.get('total_balance_usdt', 0)}"
                    )
                    print(
                        f"Available Balance USDT: "
                        f"{test_result.get('available_balance_usdt', 0)}"
                    )
                    print(
                        f"Position Initial Margin: "
                        f"{test_result.get('position_initial_margin', 0)}"
                    )
                    print(
                        f"Unrealized PNL: "
                        f"{test_result.get('unrealized_pnl', 0)}"
                    )
                else:
                    print("Status: Connection Failed")
                    print(f"Error: {test_result.get('error', 'Unknown error')}")
                    
            except ImportError:
                print(
                    "\nWarning: BinanceFutures file not found. "
                    "Check if the file exists in the correct path."
                )

        except Exception as e:
            print(f"\nError: {str(e)}")

    @staticmethod
    def set_credentials() -> None:
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
    def add_ip() -> None:
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
    def list_ips() -> None:
        """List allowed IP addresses"""
        config = SecurityConfig.load_credentials()
        ips = config['binance_futures']['allowed_ips']
        if ips:
            print("\nAllowed IPs:")
            for ip in ips:
                print(f"- {ip}")
        else:
            print("No IPs configured!")


def main() -> None:
    """Main function to handle command line operations"""
    commands: Dict[str, Callable] = {
        'test-connection': SecurityManager.test_connection,
        'set-credentials': SecurityManager.set_credentials,
        'add-ip': SecurityManager.add_ip,
        'list-ips': SecurityManager.list_ips
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