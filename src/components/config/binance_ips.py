class BinanceIPs:
    # Binance Official IPs - يجب تحديثها دورياً
    OFFICIAL_IPS = [
        "3.218.71.225",
        "34.198.178.193",
        "34.198.252.185",
        "52.204.21.209",
        "52.204.96.201",
        "52.204.110.46",
        "52.73.63.71",
        "54.156.165.64",
        "54.160.247.147",
        "54.198.92.196",
        "54.208.185.213",
        "54.208.224.156",
        "100.24.43.44",
    ]

    # Custom IPs (مثل IP الخادم الخاص بك)
    CUSTOM_IPS = []

    @classmethod
    def get_all_allowed_ips(cls):
        """الحصول على جميع عناوين IP المسموح بها"""
        return cls.OFFICIAL_IPS + cls.CUSTOM_IPS

    @classmethod
    def add_custom_ip(cls, ip):
        """إضافة IP مخصص"""
        if ip not in cls.CUSTOM_IPS:
            cls.CUSTOM_IPS.append(ip)

    @classmethod
    def remove_custom_ip(cls, ip):
        """إزالة IP مخصص"""
        if ip in cls.CUSTOM_IPS:
            cls.CUSTOM_IPS.remove(ip)

    @classmethod
    def is_ip_allowed(cls, ip):
        """التحقق مما إذا كان IP مسموحاً به"""
        return ip in cls.get_all_allowed_ips()