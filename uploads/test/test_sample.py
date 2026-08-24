"""
UMAY 9 Test Python Dosyasi
Gelistirici: Cengiz Kilarc
Tarih: 24 Agustos 2026
"""

import math
import json
from datetime import datetime

SECRET_KEY = "UMAY_PY_SECRET_72934"
VERSION = "9.0.1"
TEST_VALUE = 564

def fibonacci(n):
    """Fibonacci hesaplama fonksiyonu"""
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)

def factorial(n):
    """Faktoriyel hesaplama"""
    if n == 0 or n == 1:
        return 1
    return n * factorial(n - 1)

def is_prime(n):
    """Asal sayi kontrolu"""
    if n < 2:
        return False
    for i in range(2, int(math.sqrt(n)) + 1):
        if n % i == 0:
            return False
    return True

def calculate_average(numbers):
    """Listedeki sayilarin ortalamasini hesaplar"""
    if not numbers:
        return 0
    return sum(numbers) / len(numbers)

class UMAYTest:
    """UMAY test sinifi"""
    
    def __init__(self, name):
        self.name = name
        self.results = []
    
    def run(self, test_func, *args):
        """Testi calistir ve sonucu kaydet"""
        try:
            result = test_func(*args)
            self.results.append({"test": self.name, "result": result, "status": "PASS"})
            return result
        except Exception as e:
            self.results.append({"test": self.name, "error": str(e), "status": "FAIL"})
            return None

# Test verileri
if __name__ == "__main__":
    print(f"UMAY Test Suite v{VERSION}")
    print(f"Secret Key: {SECRET_KEY}")
    print(f"Fibonacci(10) = {fibonacci(10)}")
    print(f"Factorial(10) = {factorial(10)}")
    print(f"Is 17 prime? {is_prime(17)}")
    print(f"Average of [1,2,3,4,5] = {calculate_average([1,2,3,4,5])}")
    print(f"Test Value: {TEST_VALUE}")
