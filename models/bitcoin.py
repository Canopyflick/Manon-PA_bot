# models/bitcoin.py
from dataclasses import dataclass

@dataclass
class BitcoinPrice:
    simple_message: str
    detailed_message: str
    raw_price: float
    usd_change: float

