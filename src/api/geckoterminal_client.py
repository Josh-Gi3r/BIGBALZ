"""
GeckoTerminal API Client with rate limiting and error handling
Supports token info, social data, and whale tracking
"""

import requests
import asyncio
import logging
import time
from typing import Dict, Optional, List, Any
from dataclasses import dataclass
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class TokenData:
    """Token information from GeckoTerminal API"""
    symbol: str
    name: str
    contract_address: str
    network: str
    price_usd: float
    market_cap_usd: float
    fdv_usd: float
    volume_24h: float
    total_supply: str
    liquidity_usd: float
    primary_dex: str
    price_change_24h: float = 0.0
    price_change_1h: float = 0.0
    price_change_5m: float = 0.0
    pool_address: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for session storage"""
        return {
            'symbol': self.symbol,
            'name': self.name,
            'contract_address': self.contract_address,
            'network': self.network,
            'price_usd': self.price_usd,
            'market_cap_usd': self.market_cap_usd,
            'fdv_usd': self.fdv_usd,
            'volume_24h': self.volume_24h,
            'total_supply': self.total_supply,
            'liquidity_usd': self.liquidity_usd,
            'primary_dex': self.primary_dex,
            'price_change_24h': self.price_change_24h,
            'price_change_1h': self.price_change_1h,
            'price_change_5m': self.price_change_5m,
            'pool_address': self.pool_address
        }


@dataclass
class SocialData:
    """Social information for a token"""
    description: Optional[str] = None
    websites: List[str] = None
    twitter_handle: Optional[str] = None
    telegram_handle: Optional[str] = None
    discord_url: Optional[str] = None
    coingecko_coin_id: Optional[str] = None
    
    def __post_init__(self):
        if self.websites is None:
            self.websites = []


class RateLimiter:
    """Advanced rate limiter with priority queue support"""
    
    def __init__(self, max_calls: int, time_window: int = 60):
        """
        Initialize rate limiter
        
        Args:
            max_calls: Maximum calls allowed in time window
            time_window: Time window in seconds (default: 60)
        """
        self.max_calls = max_calls
        self.time_window = time_window
        self.calls = deque()
        self.priority_queue = asyncio.PriorityQueue()
        self.semaphore = asyncio.Semaphore(max_calls)
        self._lock = asyncio.Lock()
        
    async def acquire(self, priority: int = 1):
        """
        Acquire permission to make an API call
        
        Args:
            priority: Call priority (0 = highest, higher numbers = lower priority)
        """
        await self.priority_queue.put((priority, time.time()))
        
        async with self._lock:
            now = time.time()
            
            # Remove old calls outside time window
            while self.calls and self.calls[0] < now - self.time_window:
                self.calls.popleft()
            
            # Wait if we've hit the rate limit
            if len(self.calls) >= self.max_calls:
                sleep_time = self.time_window - (now - self.calls[0])
                if sleep_time > 0:
                    logger.warning(f"Rate limit reached, waiting {sleep_time:.2f}s")
                    await asyncio.sleep(sleep_time)
                    # Clean up again after sleep
                    while self.calls and self.calls[0] < time.time() - self.time_window:
                        self.calls.popleft()
            
            # Record this call
            self.calls.append(time.time())
            
    def get_remaining_calls(self) -> int:
        """Get number of remaining calls in current window"""
        now = time.time()
        active_calls = sum(1 for call_time in self.calls 
                           if call_time > now - self.time_window)
        return max(0, self.max_calls - active_calls)


class GeckoTerminalClient:
    """GeckoTerminal API client with advanced features"""
    
    BASE_URL = "https://api.geckoterminal.com/api/v2"
    
    def __init__(self, api_key: Optional[str] = None, rate_limit: int = 500):
        """
        Initialize GeckoTerminal client
        
        Args:
            api_key: Optional API key for GeckoTerminal Pro
            rate_limit: Calls per minute limit
        """
        self.api_key = api_key
        self.rate_limiter = RateLimiter(rate_limit, 60)
        self._cache = {}
        self._cache_ttl = 300  # 5 minutes
        
        # Setup headers
        self.headers = {
            'Accept': 'application/json;version=20230302',
            'User-Agent': 'BIGBALZ-Bot/1.0'
        }
        
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
            
    async def _make_request(self, url: str, priority: int = 1) -> Optional[Dict]:
        """
        Make rate-limited API request
        
        Args:
            url: API endpoint URL
            priority: Request priority (0 = highest)
            
        Returns:
            Response data or None if error
        """
        # Check cache first
        cache_key = url
        if cache_key in self._cache:
            cached_data, timestamp = self._cache[cache_key]
            if time.time() - timestamp < self._cache_ttl:
                logger.debug(f"Returning cached data for {url}")
                return cached_data
        
        # Acquire rate limit permission
        await self.rate_limiter.acquire(priority)
        
        try:
            # Use synchronous requests in an async context
            response = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: requests.get(url, headers=self.headers, timeout=30)
            )
            
            if response.status_code == 200:
                data = response.json()
                # Cache successful responses
                self._cache[cache_key] = (data, time.time())
                logger.debug(f"Successfully fetched data from {url}")
                return data
            elif response.status_code == 404:
                logger.warning(f"Token not found (404): {url}")
                return None
            elif response.status_code == 429:
                logger.error("Rate limit exceeded despite local limiting")
                return None
            else:
                logger.error(f"API error {response.status_code}: {url}")
                logger.error(f"Response: {response.text[:200]}")  # Log first 200 chars of error
                return None
                    
        except requests.exceptions.Timeout:
            logger.error(f"Request timeout: {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error for {url}: {type(e).__name__}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error for {url}: {type(e).__name__}: {e}")
            return None
            
    async def get_token_info(self, network: str, address: str, 
                            priority: int = 1) -> Optional[TokenData]:
        """
        Get complete token information
        
        Args:
            network: Network identifier (eth, solana, bsc, base)
            address: Contract address
            priority: Request priority
            
        Returns:
            TokenData object or None if error
        """
        url = f"{self.BASE_URL}/networks/{network}/tokens/{address}"
        data = await self._make_request(url, priority)
        
        if not data:
            return None
            
        return self._parse_token_data(data, network)
    
    async def get_token_info_multi_network(self, address: str, 
                                          priority: int = 1) -> Optional[TokenData]:
        """
        Try to get token info across multiple networks
        
        Args:
            address: Contract address
            priority: Request priority
            
        Returns:
            TokenData object or None if not found on any network
        """
        from src.utils.network_detector import NetworkDetector
        
        # Detect network from address format
        detected_network = NetworkDetector.detect_network(address)
        
        if detected_network == "eth":
            # Try all EVM networks
            networks_to_try = NetworkDetector.get_evm_networks()
        elif detected_network == "solana":
            networks_to_try = ["solana"]
        else:
            # Try all networks if detection failed
            networks_to_try = NetworkDetector.get_all_networks()
            logger.warning(f"Could not detect network for address {address}, trying all networks")
        
        # Try each network
        for network in networks_to_try:
            logger.info(f"Trying to fetch token on {network} network...")
            token_data = await self.get_token_info(network, address, priority)
            if token_data:
                logger.info(f"Token found on {network} network!")
                return token_data
        
        logger.warning(f"Token not found on any network: {address}")
        return None
        
    def _parse_token_data(self, data: Dict, network: str) -> Optional[TokenData]:
        """Parse API response into TokenData object"""
        try:
            if not data:
                logger.error("No data received from API")
                return None
                
            token_data = data.get('data', {})
            if not token_data:
                logger.error(f"No token data in response: {data}")
                return None
                
            attrs = token_data.get('attributes', {})
            relationships = token_data.get('relationships', {})
            
            primary_pool_id = None
            top_pools = relationships.get('top_pools', {}).get('data', [])
            if top_pools:
                primary_pool_id = top_pools[0].get('id')
            
            included = data.get('included', [])
            primary_pool = None
            
            # Find the primary pool from included data
            for item in included:
                if item.get('type') == 'pool':
                    primary_pool = item
                    break
            
            # Get pool attributes for liquidity and DEX info
            pool_attrs = primary_pool.get('attributes', {}) if primary_pool else {}
            
            # Get price changes from pool data
            price_changes = pool_attrs.get('price_change_percentage', {})
            
            # Helper function to safely convert to float
            def safe_float(value, default=0):
                if value is None:
                    return default
                try:
                    return float(value)
                except (TypeError, ValueError):
                    return default
            
            # Extract liquidity from pool's reserve_in_usd
            liquidity = safe_float(pool_attrs.get('reserve_in_usd'))
            
            # If no pool liquidity, try token's total_reserve_in_usd
            if liquidity == 0:
                liquidity = safe_float(attrs.get('total_reserve_in_usd'))
            
            clean_pool_address = None
            if primary_pool_id:
                if primary_pool_id.startswith(f"{network}_"):
                    clean_pool_address = primary_pool_id[len(f"{network}_"):]
                else:
                    clean_pool_address = primary_pool_id

            return TokenData(
                symbol=attrs.get('symbol', 'UNKNOWN'),
                name=attrs.get('name', 'Unknown Token'),
                contract_address=attrs.get('address', ''),
                network=network,
                price_usd=safe_float(attrs.get('price_usd')),
                market_cap_usd=safe_float(attrs.get('market_cap_usd')),
                fdv_usd=safe_float(attrs.get('fdv_usd')),
                volume_24h=safe_float(attrs.get('volume_usd', {}).get('h24')),
                total_supply=attrs.get('total_supply', '0'),
                liquidity_usd=liquidity,
                primary_dex=pool_attrs.get('dex_id', 'Unknown') if pool_attrs else 'Unknown',
                price_change_24h=safe_float(price_changes.get('h24')),
                price_change_1h=safe_float(price_changes.get('h1')),
                price_change_5m=safe_float(price_changes.get('m5')),
                pool_address=clean_pool_address
            )
            
        except Exception as e:
            logger.error(f"Error parsing token data: {e}")
            return None
            
    async def get_social_info(self, network: str, address: str) -> Optional[SocialData]:
        """
        Get social information for a token
        
        Args:
            network: Network identifier
            address: Contract address
            
        Returns:
            SocialData object or None if error
        """
        url = f"{self.BASE_URL}/networks/{network}/tokens/{address}/info"
        data = await self._make_request(url, priority=2)  # Lower priority
        
        if not data:
            return None
            
        return self._parse_social_data(data)
        
    def _parse_social_data(self, data: Dict) -> Optional[SocialData]:
        """Parse social information from API response"""
        try:
            info = data.get('data', {}).get('attributes', {})
            
            return SocialData(
                description=info.get('description'),
                websites=info.get('websites', []),
                twitter_handle=info.get('twitter_handle'),
                telegram_handle=info.get('telegram_handle'),
                discord_url=info.get('discord_url'),
                coingecko_coin_id=info.get('coingecko_coin_id')
            )
            
        except Exception as e:
            logger.error(f"Error parsing social data: {e}")
            return None
            
    async def get_whale_trades(self, network: str, pool_address: str, 
                              limit: int = 20) -> Optional[List[Dict]]:
        """
        Get recent whale trades for analysis
        
        Args:
            network: Network identifier
            pool_address: Pool address
            limit: Number of trades to fetch
            
        Returns:
            List of trade data or None if error
        """
        url = f"{self.BASE_URL}/networks/{network}/pools/{pool_address}/trades"
        url += f"?limit={limit}"
        
        data = await self._make_request(url, priority=2)
        
        if not data:
            return None
            
        trades = data.get('data', [])
        return [self._parse_trade(trade) for trade in trades]
        
    def _parse_trade(self, trade: Dict) -> Dict:
        """Parse individual trade data"""
        attrs = trade.get('attributes', {})
        
        return {
            'type': attrs.get('kind', 'unknown'),  # buy/sell
            'amount_usd': float(attrs.get('volume_in_usd', 0)),
            'from_token_amount': float(attrs.get('from_token_amount', 0)),
            'to_token_amount': float(attrs.get('to_token_amount', 0)),
            'price_usd': float(attrs.get('price_to_in_usd', 0)),
            'timestamp': attrs.get('block_timestamp'),
            'tx_hash': attrs.get('tx_hash'),
            'from_address': attrs.get('tx_from_address')
        }
        
    async def get_trending_pools(self, network: str, duration: str = "5m", 
                                limit: int = 20) -> Optional[List[Dict]]:
        """
        Get trending pools for moonshot detection
        
        Args:
            network: Network identifier
            duration: Time duration (5m, 1h, 24h) - not used in current API
            limit: Number of results
            
        Returns:
            List of trending pool data
        """
        url = f"{self.BASE_URL}/networks/{network}/trending_pools"
        # Duration parameter is supported according to docs (5m, 1h, 6h, 24h)
        url += f"?duration={duration}&limit={limit}"
        
        data = await self._make_request(url, priority=3)  # Lower priority
        
        if not data:
            return []
            
        return data.get('data', [])
        
    async def get_new_pools(self, network: str, limit: int = 20) -> Optional[List[Dict]]:
        """
        Get newly created pools
        
        Args:
            network: Network identifier
            limit: Number of results
            
        Returns:
            List of new pool data
        """
        url = f"{self.BASE_URL}/networks/new_pools"
        url += f"?limit={limit}"
        
        data = await self._make_request(url, priority=3)
        
        if not data:
            return []
            
        return data.get('data', [])
    
    async def get_new_pools_paginated(self, network: str, max_pools: int = 1000) -> List[Dict]:
        """
        Get newly created pools with pagination
        
        Args:
            network: Network identifier
            max_pools: Maximum pools to fetch (up to 1000)
            
        Returns:
            List of new pool data with enriched token information
        """
        all_pools = []
        for page in range(1, 11):
            # Use network-specific endpoint with include parameter
            url = f"{self.BASE_URL}/networks/{network}/new_pools?page={page}&include=base_token,quote_token"
            data = await self._make_request(url, priority=3)
            
            if not data or not data.get('data'):
                break
                
            pools = data.get('data', [])
            included = data.get('included', [])
            
            token_lookup = {}
            for item in included:
                if item.get('type') == 'token':
                    token_lookup[item.get('id')] = item.get('attributes', {})
            
            # Enrich pool data with token information
            enriched_pools = []
            for pool in pools:
                pool_attrs = pool.get('attributes', {})
                relationships = pool.get('relationships', {})
                
                base_token_rel = relationships.get('base_token', {})
                base_token_id = base_token_rel.get('data', {}).get('id')
                
                if base_token_id and base_token_id in token_lookup:
                    token_data = token_lookup[base_token_id]
                    
                    enriched_pool = pool.copy()
                    enriched_attrs = enriched_pool.get('attributes', {}).copy()
                    
                    enriched_attrs['base_token_symbol'] = token_data.get('symbol', 'UNKNOWN')
                    enriched_attrs['network'] = network  # Set network explicitly
                    enriched_attrs['market_cap_usd'] = token_data.get('market_cap_usd')
                    enriched_attrs['fdv_usd'] = token_data.get('fdv_usd')
                    
                    enriched_pool['_token_data'] = token_data
                    
                    enriched_pool['attributes'] = enriched_attrs
                    enriched_pools.append(enriched_pool)
            
            all_pools.extend(enriched_pools)
            
            if len(all_pools) >= max_pools:
                break
        
        return all_pools[:max_pools]
        
    async def get_pool_info(self, network: str, pool_address: str) -> Optional[Dict]:
        """
        Get detailed pool information
        
        Args:
            network: Network identifier
            pool_address: Pool address
            
        Returns:
            Pool data dictionary
        """
        url = f"{self.BASE_URL}/networks/{network}/pools/{pool_address}"
        data = await self._make_request(url)
        
        if not data:
            return None
            
        return data.get('data', {})
        
    def clear_cache(self):
        """Clear the response cache"""
        self._cache.clear()
        logger.info("API cache cleared")
        
    async def get_pools_search(self, network: str, sort: str = "h24_volume_usd_desc", 
                              limit: int = 100) -> Optional[List[Dict]]:
        """
        Search pools with sorting options
        
        Args:
            network: Network identifier
            sort: Sort parameter (h24_volume_usd_desc, etc.)
            limit: Number of results
            
        Returns:
            List of pool data
        """
        url = f"{self.BASE_URL}/networks/{network}/pools"
        url += f"?sort={sort}&limit={limit}"
        
        data = await self._make_request(url, priority=3)
        
        if not data:
            return []
            
        return data.get('data', [])
    
    async def get_pools_paginated(self, network: str, sort: str = "h24_volume_usd_desc", 
                                 max_pools: int = 1000) -> List[Dict]:
        """
        Get pools with pagination and sorting
        
        Args:
            network: Network identifier
            sort: Sort parameter
            max_pools: Maximum pools to fetch
            
        Returns:
            List of pool data with enriched token information
        """
        all_pools = []
        for page in range(1, 11):
            url = f"{self.BASE_URL}/networks/{network}/pools?sort={sort}&page={page}&include=base_token,quote_token"
            data = await self._make_request(url, priority=3)
            
            if not data or not data.get('data'):
                break
                
            pools = data.get('data', [])
            included = data.get('included', [])
            
            token_lookup = {}
            for item in included:
                if item.get('type') == 'token':
                    token_lookup[item.get('id')] = item.get('attributes', {})
            
            # Enrich pool data with token information
            enriched_pools = []
            for pool in pools:
                relationships = pool.get('relationships', {})
                
                base_token_rel = relationships.get('base_token', {})
                base_token_id = base_token_rel.get('data', {}).get('id')
                
                if base_token_id and base_token_id in token_lookup:
                    token_data = token_lookup[base_token_id]
                    
                    enriched_pool = pool.copy()
                    enriched_attrs = enriched_pool.get('attributes', {}).copy()
                    
                    enriched_attrs['base_token_symbol'] = token_data.get('symbol', 'UNKNOWN')
                    enriched_attrs['network'] = network  # Set network explicitly
                    
                    if not enriched_attrs.get('market_cap_usd'):
                        enriched_attrs['market_cap_usd'] = token_data.get('market_cap_usd')
                    if not enriched_attrs.get('fdv_usd'):
                        enriched_attrs['fdv_usd'] = token_data.get('fdv_usd')
                    
                    enriched_pool['attributes'] = enriched_attrs
                    enriched_pools.append(enriched_pool)
                else:
                    enriched_pools.append(pool)
            
            all_pools.extend(enriched_pools)
            
            if len(all_pools) >= max_pools:
                break
        
        return all_pools[:max_pools]
    
    async def get_pool_ohlcv(self, network: str, pool_address: str, 
                           timeframe: str = "day", aggregate: int = 1, 
                           limit: int = 7) -> Optional[List[Dict]]:
        """
        Get OHLCV (candlestick) data for a pool
        
        Args:
            network: Network identifier
            pool_address: Pool address
            timeframe: Timeframe (day, hour, minute)
            aggregate: Aggregation level
            limit: Number of candles
            
        Returns:
            List of OHLCV data
        """
        url = f"{self.BASE_URL}/networks/{network}/pools/{pool_address}/ohlcv/{timeframe}"
        url += f"?aggregate={aggregate}&limit={limit}"
        
        data = await self._make_request(url, priority=2)
        
        if not data:
            return []
            
        return data.get('data', {}).get('attributes', {}).get('ohlcv_list', [])
    
    def get_rate_limit_status(self) -> Dict[str, Any]:
        """Get current rate limit status"""
        return {
            'remaining_calls': self.rate_limiter.get_remaining_calls(),
            'max_calls_per_minute': self.rate_limiter.max_calls,
            'cache_size': len(self._cache)
        }
