import time
import json
import asyncio
from dotenv import load_dotenv
from pydantic import ValidationError
from openai import RateLimitError, OpenAIError
from .client_initialization import openai_client, async_openai_client

from ..schemas import DatasetRecords
import logging
logger = logging.getLogger(__name__)

load_dotenv()

def generation_agent(content, system_prompt, model="gpt-5-nano", retries=3, base_wait=2):
    logger.info(f"🎯 Starting dataset generation with model: {model}")
    logger.info(f"📤 System prompt length: {len(system_prompt)} characters")
    logger.info(f"📤 Content length: {len(content)} characters")
    logger.info(f"📤 Content preview: {content[:200]}...")
    
    for attempt in range(retries):
        try:
            logger.info(f"🚀 Making OpenAI API call (attempt {attempt + 1}/{retries}) to model: {model}")
            
            response = openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
            )

            raw_text = response.choices[0].message.content.strip()
            logger.info(f"📝 Raw API response length: {len(raw_text)} characters")
            logger.info(f"📝 Raw API response preview: {raw_text[:200]}...")
            logger.info(f"📊 API Usage - Tokens: {response.usage.total_tokens if response.usage else 'N/A'}")

            if raw_text.startswith("```json"):
                raw_text = raw_text[len("```json"):].lstrip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[len("```"):].lstrip()

            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].rstrip()

            parsed_json = json.loads(raw_text)
            logger.info(f"✅ Successfully parsed JSON response")
            logger.info(f"📊 Generated {len(parsed_json) if isinstance(parsed_json, list) else 'unknown'} records")
            
            final_package = {"dataset": parsed_json}
            validated = DatasetRecords(**final_package)
            
            logger.info(f"✅ Successfully validated dataset with {len(validated.dataset)} records")
            return validated.dataset

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON Parse Error: {e}")
            logger.error(f"Raw response that failed to parse: {raw_text[:500]}...")
            return []

        except ValidationError as e:
            logger.error(f"❌ Pydantic Validation Error: {e}")
            logger.error(f"Raw response that failed validation: {raw_text[:500]}...")
            return []

        except RateLimitError:
            wait_time = base_wait * (2 ** attempt)
            logger.warning(f"⚠️ Rate Limit: Retrying in {wait_time}s (Attempt {attempt + 1}/{retries})...")
            time.sleep(wait_time)

        except OpenAIError as e:
            logger.error(f"❌ OpenAI Error: {e}")
            return []

    logger.error("❌ [Rate limit Error] Exceeded retry attempts due to rate limiting.")
    return []

async def generation_agent_async(content, system_prompt, model="gpt-5-nano", retries=3, base_wait=2):
    """Async version of generation_agent for parallel processing"""
    logger.info(f"🎯 Starting async dataset generation with model: {model}")
    logger.info(f"📤 System prompt length: {len(system_prompt)} characters")
    logger.info(f"📤 Content length: {len(content)} characters")
    logger.info(f"📤 Content preview: {content[:200]}...")
    
    for attempt in range(retries):
        try:
            logger.info(f"🚀 Making async OpenAI API call (attempt {attempt + 1}/{retries}) to model: {model}")
            
            response = await async_openai_client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": content}
                ],
            )

            raw_text = response.choices[0].message.content.strip()
            logger.info(f"📝 Raw API response length: {len(raw_text)} characters")
            logger.info(f"📝 Raw API response preview: {raw_text[:200]}...")
            logger.info(f"📊 API Usage - Tokens: {response.usage.total_tokens if response.usage else 'N/A'}")

            if raw_text.startswith("```json"):
                raw_text = raw_text[len("```json"):].lstrip()
            elif raw_text.startswith("```"):
                raw_text = raw_text[len("```"):].lstrip()

            if raw_text.endswith("```"):
                raw_text = raw_text[:-3].rstrip()

            parsed_json = json.loads(raw_text)
            logger.info(f"✅ Successfully parsed JSON response")
            logger.info(f"📊 Generated {len(parsed_json) if isinstance(parsed_json, list) else 'unknown'} records")
            
            final_package = {"dataset": parsed_json}
            validated = DatasetRecords(**final_package)
            
            logger.info(f"✅ Successfully validated dataset with {len(validated.dataset)} records")
            return validated.dataset

        except json.JSONDecodeError as e:
            logger.error(f"❌ JSON Parse Error: {e}")
            logger.error(f"Raw response that failed to parse: {raw_text[:500]}...")
            return []

        except ValidationError as e:
            logger.error(f"❌ Pydantic Validation Error: {e}")
            logger.error(f"Raw response that failed validation: {raw_text[:500]}...")
            return []

        except RateLimitError:
            wait_time = base_wait * (2 ** attempt)
            logger.warning(f"⚠️ Rate Limit: Retrying in {wait_time}s (Attempt {attempt + 1}/{retries})...")
            await asyncio.sleep(wait_time)  # Use async sleep

        except OpenAIError as e:
            logger.error(f"❌ OpenAI Error: {e}")
            return []

    logger.error("❌ [Rate limit Error] Exceeded retry attempts due to rate limiting.")
    return []