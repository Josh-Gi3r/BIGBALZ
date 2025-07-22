"""
Network detection utilities for automatic chain identification
"""

import re
from typing import Optional, List

class NetworkDetector:
    """Detect blockchain network from contract address format"""
    
    @staticmethod
    def detect_network(address: str) -> Optional[str]:
        """
        Detect network from address format
        
        Args:
            address: Contract address
            
        Returns:
            Network identifier or None
        """
        if not address:
            return None
            
        address = address.strip()
        
        # Ethereum/BSC/Base format (0x + 40 hex characters)
        if address.startswith('0x') and len(address) == 42:
            try:
                int(address[2:], 16)  # Validate hex
                return None
            except ValueError:
                return None
        
        # Solana format (base58, typically 32-44 characters)
        elif 32 <= len(address) <= 44:
            # Base58 characters (no 0, O, I, l)
            valid_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
            if all(c in valid_chars for c in address):
                return "solana"
        
        return None
    
    @staticmethod
    def get_evm_networks() -> List[str]:
        """Get list of EVM-compatible networks to try"""
        return ["eth", "base", "bsc"]
    
    @staticmethod
    def get_all_networks() -> List[str]:
        """Get all supported networks"""
        return ["eth", "base", "bsc", "solana"]
    
    @staticmethod
    def format_network_name(network: str) -> str:
        """Format network name for display"""
        network_names = {
            "eth": "Ethereum",
            "base": "Base",
            "bsc": "BSC",
            "solana": "Solana"
        }
        return network_names.get(network, network.upper())
