"""
Response Generator with OpenAI Integration
Creates energy-matched personality responses based on BALZ classification
"""

import openai
import logging
import asyncio
from typing import Dict, Any, Optional
from dataclasses import dataclass
import random

from .reasoning_engine import BALZCategory, TokenClassification

logger = logging.getLogger(__name__)


@dataclass
class ResponseConfig:
    """Configuration for response generation"""
    temperature: float
    max_tokens: int
    personality: str
    profanity_level: str
    enthusiasm_level: str


class ResponseGenerator:
    """
    Generates energy-matched responses using OpenAI
    Different personalities based on BALZ classification
    """
    
    def __init__(self, openai_api_key: str):
        """
        Initialize response generator
        
        Args:
            openai_api_key: OpenAI API key
        """
        self.client = openai.OpenAI(api_key=openai_api_key)
        
        # Energy level configurations for each BALZ category
        self.energy_configs = {
            BALZCategory.TRASH: ResponseConfig(
                temperature=0.9,
                max_tokens=400,
                personality="Firm warning with sharp wit, protective tone",
                profanity_level="minimal",
                enthusiasm_level="strongly negative"
            ),
            BALZCategory.RISKY: ResponseConfig(
                temperature=0.8,
                max_tokens=350,
                personality="Skeptical analysis with dry humor, questioning approach",
                profanity_level="none",
                enthusiasm_level="cautiously skeptical"
            ),
            BALZCategory.CAUTION: ResponseConfig(
                temperature=0.7,
                max_tokens=300,
                personality="Balanced assessment with measured optimism",
                profanity_level="none",
                enthusiasm_level="neutral to positive"
            ),
            BALZCategory.OPPORTUNITY: ResponseConfig(
                temperature=0.8,
                max_tokens=350,
                personality="Genuine excitement with sophisticated analysis",
                profanity_level="none",
                enthusiasm_level="enthusiastically positive"
            )
        }
        
        # Fallback responses in case OpenAI fails
        self.fallback_responses = self._load_fallback_responses()
        
    async def generate_balz_response(self, 
                                   classification: TokenClassification,
                                   token_data: Any) -> str:
        """
        Generate energy-matched BALZ classification response
        
        Args:
            classification: Token classification result
            token_data: Token data dictionary
            
        Returns:
            Energy-matched response string
        """
        try:
            config = self.energy_configs[classification.category]
            
            # Build the prompt
            prompt = self._build_balz_prompt(classification, token_data)
            system_prompt = self._get_system_prompt(classification.category)
            
            # Make API call with retry logic
            response = await self._call_openai_with_retry(
                system_prompt=system_prompt,
                user_prompt=prompt,
                config=config
            )
            
            if response:
                return self._format_balz_response(response, classification)
            else:
                # Use fallback if OpenAI fails
                return self._get_fallback_response(classification, token_data)
                
        except Exception as e:
            logger.error(f"Error generating BALZ response: {e}")
            return self._get_fallback_response(classification, token_data)
    
    async def _call_openai_with_retry(self, system_prompt: str, 
                                    user_prompt: str,
                                    config: ResponseConfig,
                                    max_retries: int = 3) -> Optional[str]:
        """Call OpenAI API with retry logic"""
        for attempt in range(max_retries):
            try:
                response = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.client.chat.completions.create(
                        model="gpt-4-turbo-preview",
                        messages=[
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": user_prompt}
                        ],
                        temperature=config.temperature,
                        max_tokens=config.max_tokens
                    )
                )
                
                return response.choices[0].message.content
                
            except openai.RateLimitError:
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                    continue
                else:
                    logger.error("OpenAI rate limit exceeded")
                    return None
                    
            except Exception as e:
                logger.error(f"OpenAI API error: {e}")
                return None
                
        return None
    
    def _get_system_prompt(self, category: BALZCategory) -> str:
        """Get system prompt based on category energy"""
        base_prompt = """You are BIGBALZ Bot - not particularly bright but you've got opinions.
Keep it simple, use small words, and deliver dry humor without explaining jokes.
You're barely paying attention but somehow your takes are funny.

IMPORTANT: Format your assessment with line breaks between different thoughts. No walls of text."""
        
        if category == BALZCategory.TRASH:
            return f"""{base_prompt}

ENERGY LEVEL: DISAPPOINTED BUT NOT SURPRISED
- This token is garbage and you know it
- Make fun of how bad it is without mercy
- Act like you can't believe they're even considering this
- Drop simple truths that hit hard
- Don't sugarcoat - this is trash
- End with a harsh reality check (e.g., "enjoy poverty", "see you at McDonald's", "hope you like ramen")"""
        
        elif category == BALZCategory.RISKY:
            return f"""{base_prompt}

ENERGY LEVEL: EH WHATEVER
- Act like you've seen this movie before
- Make jokes about their gambling addiction
- Point out the obvious risks like they're a child
- Shrug at their life choices
- If they wanna lose money that's on them
- End with casino/gambling reference (e.g., "welcome to the casino", "house always wins", "wen lambo? never lambo")"""
        
        elif category == BALZCategory.CAUTION:
            return f"""{base_prompt}

ENERGY LEVEL: MILD INTEREST
- It's not terrible but it's not great
- Make lukewarm observations
- Act like you're doing them a favor by looking
- Point out the obvious stuff
- Maybe it'll work out maybe it won't
- End with cautious/neutral line (e.g., "your money your choice", "could go either way", "flip a coin")"""
        
        elif category == BALZCategory.OPPORTUNITY:
            return f"""{base_prompt}

ENERGY LEVEL: ACTUALLY EXCITED
- This one doesn't suck for once
- Get genuinely hyped but in a dumb way
- Act surprised something good showed up
- Make simple observations about why it's good
- This is the one time you pay attention
- End with hype but realistic (e.g., "lfg but don't bet the farm", "wagmi maybe", "moon potential detected")"""
    
    def _build_balz_prompt(self, classification: TokenClassification,
                          token_data: Any) -> str:
        """Build the classification prompt with token data"""
        # Handle both TokenData objects and dicts
        if hasattr(token_data, 'symbol'):
            symbol = token_data.symbol
            name = token_data.name
            price = token_data.price_usd
            market_cap = token_data.market_cap_usd
            volume = token_data.volume_24h
            liquidity = token_data.liquidity_usd
        else:
            symbol = token_data.get('symbol', 'UNKNOWN')
            name = token_data.get('name', 'Unknown Token')
            price = token_data.get('price_usd', 0)
            market_cap = token_data.get('market_cap_usd', 0)
            volume = token_data.get('volume_24h', 0)
            liquidity = token_data.get('liquidity_usd', 0)
        
        return f"""Provide a BALZ RANK analysis for this token:

TOKEN: {name} ({symbol})
CLASSIFICATION: {classification.emoji} {classification.category.value}{f' | {classification.sub_category}' if classification.sub_category else ''}

TIER BREAKDOWN:
- Volume Tier: {classification.volume_tier} (${volume:,.0f} daily)
- Liquidity Tier: {classification.liquidity_tier} (${liquidity:,.0f})
- Market Cap Tier: {classification.market_cap_tier} (${market_cap:,.0f})
- FDV Ratio: {classification.fdv_ratio_tier}

KEY METRICS:
- Price: ${price:,.8f}

Respond with the energy that matches {classification.category.value} classification.
Format your response EXACTLY like this:

BALZ RANK: {classification.emoji} {classification.category.value}{f' | {classification.sub_category}' if classification.sub_category else ''}

**Token:** {symbol}

**Tier Analysis:**
• Volume: {classification.volume_tier}
• Liquidity: {classification.liquidity_tier}
• Market Cap: {classification.market_cap_tier}
• FDV Ratio: {classification.fdv_ratio_tier}

**Assessment:** [Your personality-filled analysis here - use line breaks between thoughts to make it readable, not a wall of text]

[End with an appropriate savage line - NO QUOTATION MARKS - just the line itself]"""
    
    def _format_balz_response(self, response: str, 
                            classification: TokenClassification) -> str:
        """Format the final BALZ response"""
        # Ensure response starts with BALZ RANK if it doesn't
        if not response.startswith("BALZ RANK:"):
            sub_cat = f" | {classification.sub_category}" if classification.sub_category else ""
            response = f"BALZ RANK: {classification.emoji} {classification.category.value}{sub_cat}\n\n{response}"
        
        return response
    
    def _load_fallback_responses(self) -> Dict[BALZCategory, list]:
        """Load fallback responses for each category"""
        return {
            BALZCategory.TRASH: [
                """BALZ RANK: ⛔ TRASH | {sub_category}

lmao you serious rn? this thing has {liquidity_tier} liquidity. that's basically nothing.

{volume_tier} volume? nobody's buying this garbage except you apparently. 

oh and that {fdv_ratio_tier} FDV ratio... they're gonna dump so many tokens on your head you'll need a helmet.

this is what we call exit liquidity. you're the exit.

🗑️ why do you hate money?""",
                
                """BALZ RANK: ⛔ TRASH | {sub_category}

bruh. {liquidity_tier} liquidity. {volume_tier} volume. do i need to spell it out?

this token is so bad it makes me sad. like actually depressed that it exists.

{fdv_ratio_tier} FDV ratio means the devs are laughing at you right now. literally.

just buy lottery tickets instead. at least those have a chance.

💸 financial natural selection at work"""
            ],
            
            BALZCategory.RISKY: [
                """BALZ RANK: 🔶 RISKY | {sub_category}

ah yes another degen play. {liquidity_tier} liquidity and {volume_tier} volume. classic.

{fdv_ratio_tier} FDV ratio too. so you're basically gambling. cool cool.

might work might not. probably not but hey what do i know.

if you lose money don't cry to me about it.

🎰 casino's open i guess""",
                
                """BALZ RANK: 🔶 RISKY | {sub_category}

{liquidity_tier} liquidity huh. {volume_tier} volume. i've seen worse i guess.

that {fdv_ratio_tier} FDV ratio tho... yikes.

look if you wanna throw money at this be my guest. just don't use the rent money.

could moon could rug. probably rug but whatever floats your boat.

⚡ your funeral"""
            ],
            
            BALZCategory.CAUTION: [
                """BALZ RANK: ⚠️ CAUTION | {sub_category}

{liquidity_tier} liquidity. {volume_tier} volume. it's... fine i guess.

{fdv_ratio_tier} FDV ratio is kinda sus but not terrible.

not the worst thing i've seen today. not the best either. it exists.

might go up might go down. probably sideways tbh.

📊 meh""",
                
                """BALZ RANK: ⚠️ CAUTION | {sub_category}

ok so {liquidity_tier} liquidity and {volume_tier} volume. could be worse.

that {fdv_ratio_tier} FDV ratio is whatever. seen better seen worse.

it's not trash but it's not amazing. it's just... there.

if you buy it cool. if you don't also cool. i literally don't care.

⚖️ flip a coin"""
            ],
            
            BALZCategory.OPPORTUNITY: [
                """BALZ RANK: 🚀 OPPORTUNITY | {sub_category}

yooooo wait this one actually doesn't suck???

{liquidity_tier} liquidity and {volume_tier} volume. damn ok.

{fdv_ratio_tier} FDV ratio too. this is... actually good? wtf?

i'm shook. a real one appeared. this never happens.

quick buy it before it rugs lmao jk but seriously this is decent.

💎 holy shit an actual opportunity""",
                
                """BALZ RANK: 🚀 OPPORTUNITY | {sub_category}

hold up hold up. {liquidity_tier} liquidity? {volume_tier} volume? 

AND a {fdv_ratio_tier} FDV ratio????

bro this might actually print. i can't believe i'm saying this.

the numbers don't lie. this one's got the juice.

if you don't buy this you're actually stupid. there i said it.

🔥 lfg i guess"""
            ]
        }
    
    def _get_fallback_response(self, classification: TokenClassification,
                              token_data: Any) -> str:
        """Get fallback response when OpenAI fails"""
        fallbacks = self.fallback_responses.get(classification.category, [])
        if not fallbacks:
            return f"BALZ RANK: {classification.emoji} {classification.category.value}\n\nAnalysis complete. Unable to generate detailed response."
        
        # Select random fallback and format with data
        template = random.choice(fallbacks)
        
        return template.format(
            sub_category=classification.sub_category,
            liquidity_tier=classification.liquidity_tier,
            volume_tier=classification.volume_tier,
            fdv_ratio_tier=classification.fdv_ratio_tier,
            emoji=classification.emoji,
            category=classification.category.value
        )