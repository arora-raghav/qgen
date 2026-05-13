import json
import logging
from dotenv import load_dotenv
from typing import Literal

from ..schemas import DatasetSchema, SchemaField
from .client_initialization import openai_client
from ..prompts import schema_generate_prompt, business_schema_generate_prompt

load_dotenv()
logger = logging.getLogger(__name__)

def generate_dataset_schema(
    user_concept: str, 
    mode: Literal["qa", "business"] = "qa",
    model: str = "gpt-5-nano"
    # model: str = "gpt-5-nano"
) -> DatasetSchema:
    logger.info(f"🔍 Generating {mode.upper()} schema for concept: {user_concept[:100]}...")
    
    # Choose prompt based on mode
    logger.info(f"🎯 Schema generation requested with mode: '{mode}'")
    
    if mode == "business":
        base_prompt = business_schema_generate_prompt
        logger.info("🏢 Using business schema generation mode")
    else:
        base_prompt = schema_generate_prompt
        logger.info("🧠 Using Q&A schema generation mode")
    
    logger.info(f"📝 Base prompt length: {len(base_prompt)} characters")
    logger.info(f"📝 Base prompt preview: {base_prompt[:200]}...")
    
    # Enhanced prompt to ensure proper JSON format
    enhanced_prompt = f"""{base_prompt}

**MODE: {mode.upper()}**

You MUST respond with a JSON object that follows this exact structure:
{{
    "generated_schema": [
        {{
            "key": "field_name",
            "type": "string", 
            "description": "Description of the field"
        }}
    ]
}}

Valid types are: "string", "number", "integer", "boolean", "date", "datetime", "enum"

**IMPORTANT: Based on the selected mode '{mode}', generate a schema with 3-8 relevant fields:**
- If mode is 'qa': Generate fields for question-answer training (question, answer, context, difficulty, etc.)
- If mode is 'business': Generate fields for business data extraction (company_name, amount, currency, etc.)

**DO NOT mix the two approaches. Follow the mode exactly.**"""

    logger.info(f"🚀 Final enhanced prompt length: {len(enhanced_prompt)} characters")
    logger.info(f"🚀 Enhanced prompt preview: {enhanced_prompt[:300]}...")

    try:
        logger.info(f"🚀 Making OpenAI API call to model: {model}")
        logger.info(f"📤 System prompt length: {len(enhanced_prompt)} characters")
        logger.info(f"📤 User content length: {len(user_concept)} characters")
        logger.info(f"📤 User content preview: {user_concept[:200]}...")
        
        response = openai_client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": enhanced_prompt},
                {"role": "user", "content": user_concept},
            ],
        )

        raw_text = response.choices[0].message.content.strip()
        logger.info(f"📝 Raw API response length: {len(raw_text)} characters")
        logger.info(f"📝 Raw API response preview: {raw_text[:200]}...")
        logger.info(f"📊 API Usage - Tokens: {response.usage.total_tokens if response.usage else 'N/A'}")
        
        # Clean up the response if it has markdown formatting
        if raw_text.startswith("```json"):
            raw_text = raw_text[len("```json"):].lstrip()
        elif raw_text.startswith("```"):
            raw_text = raw_text[len("```"):].lstrip()
        
        if raw_text.endswith("```"):
            raw_text = raw_text[:-3].rstrip()
        
        # Parse the JSON response
        parsed_json = json.loads(raw_text)
        logger.info(f"✅ Parsed JSON successfully: {parsed_json}")
        
        # Create and validate the DatasetSchema object
        schema_obj = DatasetSchema(**parsed_json)
        logger.info(f"🎯 Created {mode} schema with {len(schema_obj.generated_schema)} fields")
        
        return schema_obj
        
    except json.JSONDecodeError as e:
        logger.error(f"❌ JSON parsing error: {e}")
        logger.error(f"Raw response: {raw_text}")
        
        # Create a fallback schema based on the mode
        logger.warning(f"⚠️ JSON parsing failed, using fallback {mode} schema")
        fallback_schema = create_fallback_schema(user_concept, mode)
        logger.info(f"🔄 Using fallback {mode} schema with {len(fallback_schema.generated_schema)} fields")
        
        # Double-check the fallback schema is correct for the mode
        if mode == "qa":
            # Verify it's a Q&A schema
            field_keys = [f.key for f in fallback_schema.generated_schema]
            if "question" not in field_keys or "answer" not in field_keys:
                logger.error(f"❌ Fallback schema is missing Q&A fields: {field_keys}")
                # Force create a proper Q&A schema
                fallback_schema = DatasetSchema(generated_schema=[
                    SchemaField(key="question", type="string", description="Question about the document content"),
                    SchemaField(key="answer", type="string", description="Answer based on the document"),
                    SchemaField(key="context", type="string", description="Relevant context from the source document"),
                    SchemaField(key="difficulty", type="string", description="Difficulty level of the question"),
                    SchemaField(key="topic", type="string", description="Main subject area or category"),
                    SchemaField(key="question_type", type="string", description="Type of question")
                ])
                logger.info("🔧 Forced creation of proper Q&A fallback schema")
        
        return fallback_schema
        
    except Exception as e:
        logger.error(f"❌ Schema validation error: {e}")
        logger.error(f"Parsed JSON: {parsed_json if 'parsed_json' in locals() else 'N/A'}")
        
        # Create a fallback schema
        logger.warning(f"⚠️ Schema validation failed, using fallback {mode} schema")
        fallback_schema = create_fallback_schema(user_concept, mode)
        logger.info(f"🔄 Using fallback {mode} schema with {len(fallback_schema.generated_schema)} fields")
        
        # Double-check the fallback schema is correct for the mode
        if mode == "qa":
            # Verify it's a Q&A schema
            field_keys = [f.key for f in fallback_schema.generated_schema]
            if "question" not in field_keys or "answer" not in field_keys:
                logger.error(f"❌ Fallback schema is missing Q&A fields: {field_keys}")
                # Force create a proper Q&A schema
                fallback_schema = DatasetSchema(generated_schema=[
                    SchemaField(key="question", type="string", description="Question about the document content"),
                    SchemaField(key="answer", type="string", description="Answer based on the document"),
                    SchemaField(key="context", type="string", description="Relevant context from the source document"),
                    SchemaField(key="difficulty", type="string", description="Difficulty level of the question"),
                    SchemaField(key="topic", type="string", description="Main subject area or category"),
                    SchemaField(key="question_type", type="string", description="Type of question")
                ])
                logger.info("🔧 Forced creation of proper Q&A fallback schema")
        
        return fallback_schema

def create_fallback_schema(user_concept: str, mode: str = "qa") -> DatasetSchema:
    """Create a basic fallback schema when API parsing fails"""
    logger.info(f"📋 Creating fallback {mode} schema...")
    
    if mode == "business":
        # Business-focused fallback schema
        fallback_fields = [
            SchemaField(key="company_name", type="string", description="Name of the company or organization"),
            SchemaField(key="period", type="string", description="Business period or timeframe"),
            SchemaField(key="amount", type="number", description="Financial amount or value"),
            SchemaField(key="currency", type="string", description="Currency code or symbol"),
            SchemaField(key="category", type="string", description="Business category or classification"),
            SchemaField(key="date", type="date", description="Relevant business date")
        ]
    else:
        # Q&A-focused fallback schema (existing)
        fallback_fields = [
            SchemaField(key="question", type="string", description="Question about the document content"),
            SchemaField(key="answer", type="string", description="Answer based on the document"),
            SchemaField(key="context", type="string", description="Relevant context from the source document"),
            SchemaField(key="difficulty", type="string", description="Difficulty level of the question")
        ]
    
    return DatasetSchema(generated_schema=fallback_fields)