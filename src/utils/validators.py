"""
Contract address validation for multiple blockchain networks
Supports: Ethereum, Solana, BSC, Base
"""

import re
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)


class ContractValidator:
    """Validates contract addresses for supported blockchain networks"""
    
    # Network-specific regex patterns
    NETWORK_PATTERNS = {
        'eth': r'^0x[a-fA-F0-9]{40}$',      # Ethereum: 0x + 40 hex chars
        'bsc': r'^0x[a-fA-F0-9]{40}$',      # BSC: Same as Ethereum
        'base': r'^0x[a-fA-F0-9]{40}$',     # Base: Same as Ethereum
        'solana': r'^[1-9A-HJ-NP-Za-km-z]{32,44}$'  # Solana: Base58 encoded
    }
    
    # Network display names
    NETWORK_NAMES = {
        'eth': 'Ethereum',
        'solana': 'Solana',
        'bsc': 'BNB Smart Chain',
        'base': 'Base'
    }
    
    # Example addresses for error messages
    EXAMPLE_ADDRESSES = {
        'eth': '0x95aD61b0a150d79219dCF64E1E6Cc01f0B64C4cE',
        'solana': 'EPjFWdd5AufqSSqeM2qN1xzybapC8G4wEGGkZwyTDt1v',
        'bsc': '0xe9e7CEA3DedcA5984780Bafc599bD69ADd087D56',
        'base': '0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913'
    }
    
    @classmethod
    def validate_contract(cls, address: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate a contract address and detect its network
        
        Args:
            address: Contract address to validate
            
        Returns:
            Tuple of (is_valid, network, error_message)
            - is_valid: True if address is valid for any supported network
            - network: Detected network name if valid, None otherwise
            - error_message: Error description if invalid, None otherwise
        """
        if not address:
            return False, None, "No contract address provided"
        
        # Clean the input
        address = address.strip()
        
        # Check for common issues
        if len(address) < 32:
            return False, None, "Contract address is too short"
        
        if len(address) > 44:
            return False, None, "Contract address is too long"
        
        # Try to match against each network pattern
        for network, pattern in cls.NETWORK_PATTERNS.items():
            if re.match(pattern, address):
                logger.info(f"Valid {network.upper()} contract detected: {address}")
                return True, network, None
        
        # If no match found, provide helpful error message
        error_msg = cls._generate_error_message(address)
        return False, None, error_msg
    
    @classmethod
    def _generate_error_message(cls, address: str) -> str:
        """Generate a helpful error message for invalid addresses"""
        error_parts = ["Invalid contract format. Please provide a valid address."]
        
        # Check if it looks like an Ethereum-style address but malformed
        if address.startswith('0x'):
            if len(address) != 42:
                error_parts.append(f"Ethereum addresses should be 42 characters (got {len(address)})")
            elif not all(c in '0123456789abcdefABCDEF' for c in address[2:]):
                error_parts.append("Ethereum addresses should only contain hexadecimal characters")
        
        # Check if it might be a Solana address
        elif all(c in '123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz' for c in address):
            if len(address) < 32:
                error_parts.append("Solana addresses should be at least 32 characters")
        
        error_parts.append("\nSupported networks and examples:")
        for network, example in cls.EXAMPLE_ADDRESSES.items():
            network_name = cls.NETWORK_NAMES[network]
            error_parts.append(f"• {network_name}: `{example}`")
        
        return "\n".join(error_parts)
    
    @classmethod
    def format_contract_display(cls, address: str, length: int = 8) -> str:
        """
        Format contract address for display (truncated)
        
        Args:
            address: Full contract address
            length: Number of characters to show at start and end
            
        Returns:
            Truncated address like "0x95aD...C4cE"
        """
        if not address or len(address) <= length * 2:
            return address
        
        return f"{address[:length]}...{address[-4:]}"
    
    @classmethod
    def is_checksum_valid(cls, address: str) -> bool:
        """
        Validate EIP-55 checksum for Ethereum-style addresses
        Note: This is optional validation, not all addresses use checksums
        
        Args:
            address: Ethereum-style address to check
            
        Returns:
            True if checksum is valid or not applicable
        """
        if not address.startswith('0x') or len(address) != 42:
            return True  # Not an Ethereum address, checksum not applicable
        
        # For now, we'll accept all Ethereum addresses
        # Full EIP-55 checksum validation could be added here
        return True
    
    @classmethod
    def normalize_address(cls, address: str, network: str) -> str:
        """
        Normalize address format for consistency
        
        Args:
            address: Contract address
            network: Network name
            
        Returns:
            Normalized address
        """
        address = address.strip()
        
        # Ethereum-style addresses: ensure lowercase (except for checksum)
        if network in ['eth', 'bsc', 'base']:
            # For now, convert to lowercase. Checksum preservation could be added
            return address.lower()
        
        return address
    
    @classmethod
    def get_explorer_url(cls, address: str, network: str) -> Optional[str]:
        """
        Get blockchain explorer URL for the contract
        
        Args:
            address: Contract address
            network: Network name
            
        Returns:
            Explorer URL or None if not available
        """
        explorer_urls = {
            'eth': f'https://etherscan.io/token/{address}',
            'bsc': f'https://bscscan.com/token/{address}',
            'base': f'https://basescan.org/token/{address}',
            'solana': f'https://solscan.io/token/{address}'
        }
        
        return explorer_urls.get(network)